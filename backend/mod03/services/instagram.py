"""Instagram Graph API — hashtag reference media and publishing.

Two jobs, both via Facebook Login for Instagram (``graph.facebook.com``):

1. **Reference media.** Resolve a trending hashtag to its IG node, then pull
   ``top_media`` and ``recent_media``. Their captions ground the draft in what
   people are actually posting under that tag, instead of the model inventing
   an angle from the tag name alone.

2. **Publishing.** The two-step container flow: create a media container from a
   *publicly reachable* image URL, poll until Meta has fetched and processed
   it, then publish.

Hard limits worth knowing before changing anything here:

* **30 unique hashtags per rolling 7 days**, per IG account. A hashtag counts
  against the budget the moment it is queried and stays counted for 7 days,
  used or not. So lookups happen only when a reviewer selects a trend — never
  across the whole scanned feed — and results are cached.
* ``image_url`` must be publicly reachable. Meta fetches it server-side, so
  localhost paths silently fail. See ``github_upload.py``.
* 25 published posts per 24 hours.
* Captions cannot be edited after publishing. Only deletion is possible.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from backend.core.logging import get_logger
from backend.mod03.utils.config import settings
from backend.mod03.utils.language import is_english_caption

log = get_logger("instagram")

MEDIA_FIELDS = (
    "id,caption,media_type,media_url,permalink,like_count,comments_count,timestamp"
)

# Hashtag id lookups are stable and global, so they are cached for the whole
# process — re-resolving the same tag would burn nothing extra against the
# budget, but it is a wasted round trip.
_hashtag_id_cache: Dict[str, str] = {}

# Media results per hashtag, with a short TTL. The 30-per-week budget makes
# repeat lookups expensive in a way normal caching does not capture: the cost
# is not latency, it is a slot you cannot get back for 7 days.
_media_cache: Dict[str, Dict[str, Any]] = {}


class InstagramError(RuntimeError):
    """Raised with a human-readable explanation of a Meta API failure."""


def _base() -> str:
    version = (settings.meta_api_version or "v23.0").strip()
    if not version.startswith("v"):
        version = f"v{version}"
    return f"https://graph.facebook.com/{version}"


def _token() -> str:
    token = (settings.facebook_user_access_token or "").strip()
    if not token:
        raise InstagramError(
            "FACEBOOK_USER_ACCESS_TOKEN is not set — Instagram features are "
            "unavailable. Add it to .env and restart."
        )
    return token


def _business_id() -> str:
    ig_id = (settings.instagram_business_account_id or "").strip()
    if not ig_id:
        raise InstagramError(
            "INSTAGRAM_BUSINESS_ACCOUNT_ID is not set — Instagram features are "
            "unavailable. Add it to .env and restart."
        )
    return ig_id


def is_configured() -> bool:
    return bool(
        (settings.facebook_user_access_token or "").strip()
        and (settings.instagram_business_account_id or "").strip()
    )


def _explain(payload: Any, status: int) -> str:
    """Turn a Meta error body into something a reviewer can act on."""

    err = (payload or {}).get("error") if isinstance(payload, dict) else None
    if not err:
        return f"HTTP {status} from Meta."

    msg = err.get("message", "Unknown error")
    code = err.get("code")
    sub = err.get("error_subcode")

    # The handful of codes that actually come up, translated.
    if code == 190:
        return f"{msg} (the access token is invalid or expired — regenerate it)."
    if code == 4 or code == 17:
        return f"{msg} (Meta rate limit reached — wait and retry)."
    if code == 9:
        return f"{msg} (publishing limit reached — 25 posts per 24 hours)."
    if code == 10 or code == 200:
        return (
            f"{msg} (missing permission — the app may need App Review for this "
            "call, or the token lacks the required scope)."
        )
    if code == 24:
        return f"{msg} (Meta could not fetch the image — is the URL public?)."

    detail = f" [code {code}" + (f", subcode {sub}" if sub else "") + "]" if code else ""
    return f"{msg}{detail}"


def _get(path: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    url = f"{_base()}{path}"
    params = {**params, "access_token": _token()}
    try:
        r = requests.get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise InstagramError(f"Could not reach Meta: {type(exc).__name__}") from exc
    payload = r.json() if r.content else {}
    if not r.ok or (isinstance(payload, dict) and payload.get("error")):
        raise InstagramError(_explain(payload, r.status_code))
    return payload


def _post(path: str, body: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    url = f"{_base()}{path}"
    body = {**body, "access_token": _token()}
    try:
        r = requests.post(url, data=body, timeout=timeout)
    except requests.RequestException as exc:
        raise InstagramError(f"Could not reach Meta: {type(exc).__name__}") from exc
    payload = r.json() if r.content else {}
    if not r.ok or (isinstance(payload, dict) and payload.get("error")):
        raise InstagramError(_explain(payload, r.status_code))
    return payload


# ----- hashtag reference media ------------------------------------------------

def _normalise(hashtag: str) -> str:
    """Meta wants the bare word: no '#', no spaces, no emoji."""

    return (hashtag or "").strip().lstrip("#").strip()


def hashtag_id(hashtag: str) -> str:
    """Resolve a hashtag to its IG node id. Counts against the weekly budget."""

    tag = _normalise(hashtag)
    if not tag:
        raise InstagramError("Empty hashtag.")
    if tag.lower() in _hashtag_id_cache:
        return _hashtag_id_cache[tag.lower()]

    log.info("resolving hashtag id | tag=%s (counts against the 30/7d budget)", tag)
    data = _get("/ig_hashtag_search", {"user_id": _business_id(), "q": tag})
    items = data.get("data") or []
    if not items:
        raise InstagramError(
            f"Instagram has no hashtag matching '{tag}'. X trends often have no "
            "Instagram presence — the draft will be written without reference posts."
        )
    hid = items[0]["id"]
    _hashtag_id_cache[tag.lower()] = hid
    return hid


def reference_media(hashtag: str, limit: int = 8, ttl_minutes: int = 60) -> Dict[str, Any]:
    """Top + recent media for a hashtag, for display and as drafting context.

    Cached: the weekly budget makes a repeat lookup genuinely costly, not just
    slow. Top and recent are fetched independently so one failing does not lose
    the other.
    """

    tag = _normalise(hashtag)
    key = tag.lower()
    now = datetime.now(timezone.utc)

    cached = _media_cache.get(key)
    if cached and now - cached["fetched_at"] < timedelta(minutes=ttl_minutes):
        age = int((now - cached["fetched_at"]).total_seconds())
        log.info("serving cached IG media | tag=%s | age=%ss", tag, age)
        return {**cached["payload"], "cached": True}

    hid = hashtag_id(tag)
    limit = max(1, min(limit, 25))
    common = {"user_id": _business_id(), "fields": MEDIA_FIELDS, "limit": limit}

    top: List[dict] = []
    recent: List[dict] = []
    errors: Dict[str, str] = {}

    try:
        top = (_get(f"/{hid}/top_media", common).get("data") or [])
    except InstagramError as exc:
        errors["top"] = str(exc)
        log.warning("top_media failed | tag=%s | %s", tag, exc)

    try:
        recent = (_get(f"/{hid}/recent_media", common).get("data") or [])
    except InstagramError as exc:
        errors["recent"] = str(exc)
        log.warning("recent_media failed | tag=%s | %s", tag, exc)

    if not top and not recent:
        raise InstagramError(
            errors.get("top")
            or errors.get("recent")
            or f"No media found for #{tag}."
        )

    # Only English captions are kept. A hashtag like #upi carries Hindi,
    # Gujarati and Telugu posts alongside English ones; feeding that mix to
    # the drafting model produces muddled copy, and showing it as "reference"
    # implies it informed the draft when it did not.
    raw_total = len(top) + len(recent)
    top, top_dropped = _keep_english(top)
    recent, recent_dropped = _keep_english(recent)
    dropped = top_dropped + recent_dropped
    if dropped:
        log.info(
            "language filter | tag=%s | kept %d of %d captions (%d not English)",
            tag, raw_total - dropped, raw_total, dropped,
        )

    payload = {
        "hashtag": tag,
        "hashtag_id": hid,
        "top": top,
        "recent": recent,
        "errors": errors or None,
        "fetched_at": now.isoformat(),
        "filtered_out": dropped,
        "total_fetched": raw_total,
    }
    _media_cache[key] = {"payload": payload, "fetched_at": now}
    log.info("IG media ok | tag=%s | top=%d recent=%d", tag, len(top), len(recent))
    return {**payload, "cached": False}


def _keep_english(items: List[dict]) -> Tuple[List[dict], int]:
    """Split media on caption language. Returns (kept, dropped_count).

    Each kept item is annotated with the caption that was actually judged, so
    the UI and the prompt agree on what "English" meant here.
    """

    kept: List[dict] = []
    dropped = 0
    for item in items or []:
        ok, reason = is_english_caption(item.get("caption") or "")
        if ok:
            kept.append(item)
        else:
            dropped += 1
            log.debug("dropped non-English media %s: %s", item.get("id"), reason)
    return kept, dropped


def captions_for_prompt(media: Dict[str, Any], max_items: int = 6) -> List[str]:
    """Pick the caption lines worth showing the drafting model.

    Top media first — those are the posts that actually landed under this tag.
    Captions are truncated because the model needs the gist and the angle, not
    someone's full 2,000-character story.
    """

    seen: set[str] = set()
    out: List[str] = []
    for item in list(media.get("top") or []) + list(media.get("recent") or []):
        caption = (item.get("caption") or "").strip().replace("\n", " ")
        if not caption:
            continue
        key = caption[:60].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(caption[:280])
        if len(out) >= max_items:
            break
    return out


def budget_used() -> Optional[int]:
    """How many of the 30 weekly hashtag slots are already spent.

    Returns None if the call fails — this is a nicety, never a blocker.
    """

    try:
        data = _get(
            f"/{_business_id()}/recently_searched_hashtags", {"limit": 30}
        )
        return len(data.get("data") or [])
    except Exception as exc:  # noqa: BLE001
        log.debug("could not read hashtag budget: %s", exc)
        return None


# ----- publishing -------------------------------------------------------------

def publish_image(
    image_url: str,
    caption: str,
    poll_attempts: int = 12,
    poll_delay: float = 2.0,
) -> Dict[str, Any]:
    """Publish a single image post. ``image_url`` must be publicly reachable.

    Container -> poll until FINISHED -> publish. The poll matters: publishing a
    container Meta has not finished fetching fails with an opaque error.
    """

    ig_id = _business_id()
    caption = (caption or "").strip()

    log.info("IG publish | creating container | url=%s", image_url)
    container = _post(f"/{ig_id}/media", {"image_url": image_url, "caption": caption})
    creation_id = container.get("id")
    if not creation_id:
        raise InstagramError("Meta did not return a container id.")

    # Images are usually instant, but Meta still has to fetch the URL.
    status = "UNKNOWN"
    for attempt in range(1, poll_attempts + 1):
        try:
            info = _get(f"/{creation_id}", {"fields": "status_code,status"})
        except InstagramError as exc:
            log.warning("status poll %d failed: %s", attempt, exc)
            time.sleep(poll_delay)
            continue

        status = info.get("status_code", "UNKNOWN")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise InstagramError(
                "Meta could not process the image. Most often the URL is not "
                f"publicly reachable, or the format is unsupported. ({info.get('status', '')})"
            )
        time.sleep(poll_delay)
    else:
        raise InstagramError(
            f"Container was still '{status}' after "
            f"{poll_attempts * poll_delay:.0f}s. Try publishing again shortly."
        )

    log.info("IG publish | publishing container %s", creation_id)
    published = _post(f"/{ig_id}/media_publish", {"creation_id": creation_id})
    post_id = published.get("id")

    permalink = None
    try:
        permalink = _get(f"/{post_id}", {"fields": "permalink"}).get("permalink")
    except InstagramError:
        pass  # cosmetic only — the post is already live

    log.info("IG published | post_id=%s", post_id)
    return {
        "platform": "instagram",
        "ok": True,
        "post_id": post_id,
        "creation_id": creation_id,
        "permalink": permalink,
    }
