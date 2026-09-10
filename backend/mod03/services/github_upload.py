"""Publish a generated image to a public GitHub repo and return its raw URL.

Instagram will not accept a local file: Meta fetches ``image_url`` from its own
servers, so anything on localhost silently fails. The cheapest public host that
needs no new infrastructure is a public GitHub repo — commit the file via the
contents API, then hand Meta the ``raw.githubusercontent.com`` URL.

The repo **must be public**. Raw URLs for private repos require a token that
Meta will not have, and the fetch fails with an opaque error.

Anything pushed here is permanently public and in git history.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import requests

from backend.core.logging import get_logger
from backend.mod03.utils.config import settings

log = get_logger("github-upload")

API = "https://api.github.com"


class GitHubUploadError(RuntimeError):
    """Raised when the image could not be made publicly reachable."""


def is_configured() -> bool:
    return bool(
        (settings.github_token or "").strip()
        and (settings.github_repo or "").strip()
    )


def _headers() -> dict:
    token = (settings.github_token or "").strip()
    if not token:
        raise GitHubUploadError(
            "GITHUB_TOKEN is not set. Instagram needs a publicly reachable "
            "image URL, and the image is uploaded to GitHub to get one. Add a "
            "PAT with 'contents: write' to .env and restart."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo() -> str:
    repo = (settings.github_repo or "").strip().strip("/")
    if not repo or "/" not in repo:
        raise GitHubUploadError(
            "GITHUB_REPO must look like 'owner/repo' (e.g. "
            "'Karthik-p28/ig-test-images'). Set it in .env and restart."
        )
    return repo


def upload_image(local_path: str, filename: Optional[str] = None) -> str:
    """Commit ``local_path`` to the configured repo and return its raw URL.

    The filename is made unique so re-publishing never collides with an
    existing file — the contents API rejects a create without the current blob
    SHA, and silently overwriting a previously published image would change a
    live post's picture.
    """

    if not os.path.isfile(local_path):
        raise GitHubUploadError(f"No such image on disk: {local_path}")

    repo = _repo()
    branch = (settings.github_branch or "main").strip() or "main"
    folder = (settings.github_path or "images").strip().strip("/")

    ext = os.path.splitext(local_path)[1] or ".png"
    if not filename:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"{stamp}-{uuid.uuid4().hex[:8]}{ext}"
    path_in_repo = f"{folder}/{filename}" if folder else filename

    with open(local_path, "rb") as fh:
        content_b64 = base64.b64encode(fh.read()).decode("ascii")

    url = f"{API}/repos/{repo}/contents/{path_in_repo}"
    body = {
        "message": f"Add generated image {filename}",
        "content": content_b64,
        "branch": branch,
    }

    log.info("uploading image to GitHub | repo=%s | path=%s", repo, path_in_repo)
    try:
        r = requests.put(url, headers=_headers(), json=body, timeout=60)
    except requests.RequestException as exc:
        raise GitHubUploadError(
            f"Could not reach GitHub: {type(exc).__name__}"
        ) from exc

    if r.status_code == 401:
        raise GitHubUploadError(
            "GitHub rejected the token (401). Check GITHUB_TOKEN is valid and "
            "has 'contents: write' on the repo."
        )
    if r.status_code == 404:
        raise GitHubUploadError(
            f"GitHub returned 404 for '{repo}'. Check GITHUB_REPO is correct "
            "and the token can write to it."
        )
    if r.status_code == 422:
        raise GitHubUploadError(
            f"GitHub rejected the upload (422): {r.json().get('message', '')}. "
            f"Does branch '{branch}' exist?"
        )
    if not r.ok:
        raise GitHubUploadError(
            f"GitHub upload failed (HTTP {r.status_code}): "
            f"{r.json().get('message', r.text[:200])}"
        )

    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path_in_repo}"
    log.info("image public at %s", raw_url)
    return raw_url


def local_path_for(image_url: str) -> Optional[str]:
    """Map a served ``/generated/...`` URL back to the file on disk."""

    if not image_url:
        return None
    marker = "/generated/"
    if marker not in image_url:
        # Already an absolute public URL — nothing to upload.
        return None

    from backend.mod03.services.imagegen import OUTPUT_DIR

    relative = image_url.split(marker, 1)[1].lstrip("/")
    candidate = os.path.join(str(OUTPUT_DIR), relative)
    return candidate if os.path.isfile(candidate) else None


def ensure_public_url(image_url: Optional[str]) -> Optional[str]:
    """Return a URL Meta can fetch, uploading to GitHub if needed.

    Absolute non-local URLs pass straight through, so a reviewer can paste a
    public image and skip GitHub entirely.
    """

    if not image_url:
        return None

    local = local_path_for(image_url)
    if local is None:
        if image_url.startswith("http://") or image_url.startswith("https://"):
            if "localhost" in image_url or "127.0.0.1" in image_url:
                raise GitHubUploadError(
                    "That image URL points at localhost, which Meta cannot "
                    "reach. Generate the image in MOD03 so it can be uploaded, "
                    "or supply a public URL."
                )
            return image_url  # already public
        raise GitHubUploadError(f"Unusable image URL: {image_url}")

    return upload_image(local)
