"""Facebook Page publishing.

Uses a Page access token against ``/{page-id}/photos`` (image post) or
``/{page-id}/feed`` (text post). Unlike Instagram, Facebook accepts a text-only
post and allows the message to be edited after publishing — which is why a
draft with no image can still go out here.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from backend.core.logging import get_logger
from backend.mod03.utils.config import settings

log = get_logger("facebook")


class FacebookError(RuntimeError):
    """Raised with a human-readable explanation of a Graph API failure."""


def _base() -> str:
    version = (settings.meta_api_version or "v23.0").strip()
    if not version.startswith("v"):
        version = f"v{version}"
    return f"https://graph.facebook.com/{version}"


def _token() -> str:
    # Page token first; a user token can work if it carries Page scopes.
    token = (settings.facebook_page_access_token or "").strip() or (
        settings.facebook_user_access_token or ""
    ).strip()
    if not token:
        raise FacebookError(
            "FACEBOOK_PAGE_ACCESS_TOKEN is not set — Facebook publishing is "
            "unavailable. Add it to .env and restart."
        )
    return token


def _page_id() -> str:
    page_id = (settings.facebook_page_id or "").strip()
    if not page_id:
        raise FacebookError(
            "FACEBOOK_PAGE_ID is not set — Facebook publishing is unavailable. "
            "Add it to .env and restart."
        )
    return page_id


def is_configured() -> bool:
    has_token = bool(
        (settings.facebook_page_access_token or "").strip()
        or (settings.facebook_user_access_token or "").strip()
    )
    return has_token and bool((settings.facebook_page_id or "").strip())


def _explain(payload: Any, status: int) -> str:
    err = (payload or {}).get("error") if isinstance(payload, dict) else None
    if not err:
        return f"HTTP {status} from Meta."

    msg = err.get("message", "Unknown error")
    code = err.get("code")

    if code == 190:
        return f"{msg} (the Page access token is invalid or expired)."
    if code in (10, 200):
        return (
            f"{msg} (missing permission — the Page token needs pages_manage_posts "
            "and pages_read_engagement)."
        )
    if code in (4, 17, 32):
        return f"{msg} (Meta rate limit reached — wait and retry)."
    if code == 324:
        return f"{msg} (Meta could not fetch the image — is the URL public?)."

    return f"{msg}" + (f" [code {code}]" if code else "")


def _post(path: str, body: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    url = f"{_base()}{path}"
    body = {**body, "access_token": _token()}
    try:
        r = requests.post(url, data=body, timeout=timeout)
    except requests.RequestException as exc:
        raise FacebookError(f"Could not reach Meta: {type(exc).__name__}") from exc
    payload = r.json() if r.content else {}
    if not r.ok or (isinstance(payload, dict) and payload.get("error")):
        raise FacebookError(_explain(payload, r.status_code))
    return payload


def publish(message: str, image_url: Optional[str] = None) -> Dict[str, Any]:
    """Publish to the Page. With an image it is a photo post, else text-only."""

    page_id = _page_id()
    message = (message or "").strip()

    if image_url:
        log.info("FB publish | photo post | url=%s", image_url)
        body: Dict[str, Any] = {"url": image_url}
        if message:
            body["caption"] = message
        data = _post(f"/{page_id}/photos", body)
        # /photos returns the photo id plus the feed post id used for edit/delete.
        post_id = data.get("post_id") or data.get("id")
        photo_id = data.get("id")
    else:
        if not message:
            raise FacebookError("Nothing to publish: no message and no image.")
        log.info("FB publish | text post")
        data = _post(f"/{page_id}/feed", {"message": message})
        post_id = data.get("id")
        photo_id = None

    log.info("FB published | post_id=%s", post_id)
    return {
        "platform": "facebook",
        "ok": True,
        "post_id": post_id,
        "photo_id": photo_id,
        "permalink": f"https://www.facebook.com/{post_id}" if post_id else None,
    }
