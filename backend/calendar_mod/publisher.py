"""Turning a scheduled calendar post into a real published post.

The calendar was built with a simulated publish — it flipped a status flag and
posted nothing. This module is what makes a schedule mean something: it takes a
stored post and pushes it to Meta through the same clients MOD03/MOD02 use, and
it runs the loop that fires posts when their time arrives.

Two ways a post goes live:

* **Automatically**, when the scheduled time passes. ``scheduler_loop`` wakes
  every ``CHECK_SECONDS`` and publishes anything due.
* **Manually**, via ``POST /api/calendar/publish/{id}`` — "publish it now
  rather than waiting".

Both funnel through :func:`publish_now`, so a manual publish and a scheduled
one behave identically.

Known limitation: the schedule lives in memory with the rest of the prototype,
so a backend restart loses it. That is consistent with drafts and panel state,
and deliberate — every demo starts clean — but it does mean this is not a
scheduler you would leave running overnight expecting posts in the morning.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from backend.core.logging import get_logger
from backend.mod03.services import facebook, github_upload, instagram

log = get_logger("calendar.publish")

# The calendar schedules in IST. Pinning the timezone here rather than relying
# on datetime.now() means a post scheduled for 17:00 fires at 17:00 IST whether
# the backend runs on a laptop in Hyderabad or a UTC server.
IST = timezone(timedelta(hours=5, minutes=30))


def ist_now() -> datetime:
    """Current wall-clock time in IST, as a naive datetime.

    Naive because stored schedules are naive calendar values ("2026-09-08",
    "17:00") with no offset, and comparing naive to aware raises.
    """

    return datetime.now(IST).replace(tzinfo=None)

# How often to check for due posts. 30s is fine for minute-granularity
# scheduling and costs nothing when the calendar is empty.
CHECK_SECONDS = 30

# Platforms this prototype can actually publish to. Anything else is stored and
# displayed but cannot go live — publishing it returns a clear error rather
# than silently doing nothing.
PUBLISHABLE = {"instagram", "facebook"}


class PublishError(RuntimeError):
    """Raised when a scheduled post cannot be published."""


def scheduled_at(post: Dict[str, Any]) -> Optional[datetime]:
    """Combine the stored date + time into a datetime, or None if unparseable.

    Treated as server-local time: a reviewer picking "17:00" means 5pm where
    they are, not UTC.
    """

    try:
        return datetime.fromisoformat(
            f"{post['scheduled_date']}T{post.get('scheduled_time') or '09:00'}"
        )
    except (KeyError, ValueError, TypeError):
        return None


def is_due(post: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    if post.get("status") != "scheduled":
        return False
    when = scheduled_at(post)
    if when is None:
        return False
    return when <= (now or ist_now())


def publish_now(post: Dict[str, Any]) -> Dict[str, Any]:
    """Publish one stored post. Mutates and returns it.

    Status moves scheduled -> publishing -> live | failed. The intermediate
    state is what stops the scheduler picking up a post the manual endpoint is
    already working on — publishing twice to Instagram cannot be undone.
    """

    platform = (post.get("platform") or "").lower()
    post_id = post.get("id")

    if platform not in PUBLISHABLE:
        raise PublishError(
            f"'{platform}' is not connected — this prototype can publish to "
            f"{' and '.join(sorted(PUBLISHABLE))} only. Change the platform on "
            "this post to publish it."
        )

    caption = (post.get("text") or "").strip()
    tags = " ".join(post.get("hashtags") or [])
    if tags and tags not in caption:
        caption = f"{caption}\n\n{tags}"
    if not caption and not post.get("image_url"):
        raise PublishError("Nothing to publish: the post has no text and no image.")

    post["status"] = "publishing"
    log.info("publishing scheduled post | id=%s | platform=%s", post_id, platform)

    try:
        # Meta fetches image_url from its own servers, so a local path has to
        # be made public first.
        public_url = None
        if post.get("image_url"):
            try:
                public_url = github_upload.ensure_public_url(post["image_url"])
            except Exception as exc:  # noqa: BLE001
                if platform == "instagram":
                    raise PublishError(f"Could not host the image: {exc}") from exc
                # Facebook can still post the text.
                log.warning("image upload failed, posting text only | %s", exc)

        if platform == "instagram":
            if not public_url:
                raise PublishError(
                    "Instagram requires an image. Attach one to this post, or "
                    "publish it to Facebook instead."
                )
            result = instagram.publish_image(public_url, caption)
        else:
            result = facebook.publish(caption, image_url=public_url)

    except PublishError as exc:
        post["status"] = "failed"
        post["error"] = str(exc)
        log.error("scheduled publish failed | id=%s | %s", post_id, exc)
        raise
    except Exception as exc:  # noqa: BLE001
        post["status"] = "failed"
        post["error"] = str(exc)
        log.error("scheduled publish failed | id=%s | %s", post_id, exc)
        raise PublishError(str(exc)) from exc

    post["status"] = "live"
    post["published_at"] = ist_now().isoformat()
    post["error"] = None
    post["post_id"] = result.get("post_id")
    post["permalink"] = result.get("permalink")
    log.info(
        "scheduled post is live | id=%s | platform=%s | permalink=%s",
        post_id, platform, post.get("permalink"),
    )
    return post


async def scheduler_loop(store: Dict[str, Dict[str, Any]]) -> None:
    """Publish posts as their scheduled time arrives.

    Runs for the life of the process. A failure on one post is recorded on that
    post and never stops the loop — one bad post must not silently freeze
    everything scheduled behind it.
    """

    log.info("calendar scheduler started | checking every %ss", CHECK_SECONDS)
    while True:
        try:
            await asyncio.sleep(CHECK_SECONDS)
            now = ist_now()
            due = [p for p in list(store.values()) if is_due(p, now)]
            if not due:
                continue

            log.info("scheduler: %d post(s) due", len(due))
            for post in due:
                if post.get("platform", "").lower() not in PUBLISHABLE:
                    # Mark it once rather than retrying every 30 seconds.
                    post["status"] = "failed"
                    post["error"] = (
                        f"'{post.get('platform')}' is not connected — cannot publish."
                    )
                    log.warning(
                        "scheduler: skipping unpublishable platform | id=%s | %s",
                        post.get("id"), post.get("platform"),
                    )
                    continue
                try:
                    # Blocking HTTP inside the loop: offloaded so the event
                    # loop keeps serving requests while Meta is slow.
                    await asyncio.to_thread(publish_now, post)
                except Exception as exc:  # noqa: BLE001
                    log.error(
                        "scheduler: post %s failed, continuing | %s",
                        post.get("id"), exc,
                    )
        except asyncio.CancelledError:
            log.info("calendar scheduler stopped")
            raise
        except Exception as exc:  # noqa: BLE001
            # Never let an unexpected error kill the loop.
            log.error("scheduler loop error (continuing) | %s", exc)
