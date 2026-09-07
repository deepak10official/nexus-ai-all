"""Nexus — unified API.

One FastAPI application serving both modules:

    /api/radar/*   MOD03 National Trend Radar  — scores India X trends and
                   drafts a Bharat Connect post for human approval.
    /api/panel/*   MOD02 Persona Panel         — five synthetic consumers vote
                   APPROVE/REJECT on that draft.

The two are joined by the handoff endpoint ``POST /api/handoff``: a draft
approved in the Radar is sent straight into the Panel for validation, in-process
(no HTTP hop, no re-serialisation).

Run from the project root:

    uvicorn backend.api:app --reload --port 8000
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.core.logging import configure as configure_logging
from backend.core.logging import current_log_file, get_logger
from backend.mod02.router import router as panel_router
from backend.mod03.router import log_config as radar_log_config
from backend.mod03.router import router as radar_router
from backend.mod03.services.imagegen import OUTPUT_DIR

configure_logging()
log = get_logger("api")

app = FastAPI(title="Nexus — Trend Radar + Persona Panel", version="1.0.0")

# Single CORS policy for the whole app (each module no longer sets its own).
_origins = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(radar_router)
app.include_router(panel_router)

# Generated images are served from the app, not the router.
app.mount("/generated", StaticFiles(directory=OUTPUT_DIR), name="generated")


@app.on_event("startup")
def _startup() -> None:
    log.info("Nexus API starting — radar + panel mounted")
    try:
        radar_log_config()
    except Exception as exc:  # non-fatal: config logging only
        log.warning("radar config logging failed: %s", exc)


@app.get("/api/health")
def health():
    """Single health endpoint covering both modules."""

    radar_ok = panel_ok = False
    radar_model = panel_model = None
    image_ok = False
    image_model = None
    image_licence = None
    region = None
    fallback_ok = False
    ig_ok = fb_ok = gh_ok = False
    detail = {}

    try:
        from backend.mod03.utils.config import settings as radar_settings

        radar_model = radar_settings.openrouter_model
        radar_ok = bool(getattr(radar_settings, "openrouter_api_key", ""))
        image_model = getattr(radar_settings, "image_model", None)
        image_ok = bool(getattr(radar_settings, "hf_token", ""))
        image_licence = getattr(radar_settings, "image_licence", None)
        region = getattr(radar_settings, "trend_region", None)
        fallback_ok = bool(getattr(radar_settings, "scrapebadger_api_key", ""))
        from backend.mod03.services import facebook as _fb
        from backend.mod03.services import github_upload as _gh
        from backend.mod03.services import instagram as _ig

        ig_ok = _ig.is_configured()
        fb_ok = _fb.is_configured()
        gh_ok = _gh.is_configured()
    except Exception as exc:
        detail["radar"] = str(exc)

    try:
        from backend.mod02.utils.config import get_settings as panel_settings

        s = panel_settings()
        panel_model = {
            "groq": s.groq_model,
            "anthropic": s.anthropic_model,
        }.get(s.provider, s.ollama_model)
        panel_ok = s.provider != "groq" or bool(s.groq_api_key)
    except Exception as exc:
        detail["panel"] = str(exc)

    return {
        "ok": True,
        # Flat fields kept for the MOD03 UI, which was written against the
        # standalone Trend Radar health endpoint. Removing them silently
        # disabled the image button, so they stay.
        "llm_configured": radar_ok,
        "model": radar_model,
        "image_configured": image_ok,
        "image_model": image_model,
        "image_licence": image_licence,
        "region": region,
        "trend_fallback_configured": fallback_ok,
        "instagram_configured": ig_ok,
        "facebook_configured": fb_ok,
        "image_host_configured": gh_ok,
        # Grouped view for the merged app.
        "radar": {
            "llm_configured": radar_ok,
            "model": radar_model,
            "image_configured": image_ok,
            "image_model": image_model,
            "image_licence": image_licence,
        },
        "panel": {"llm_configured": panel_ok, "model": panel_model},
        "log_file": str(current_log_file() or ""),
        "detail": detail or None,
    }


# ----- MOD03 -> MOD02 handoff -------------------------------------------------

class HandoffRequest(BaseModel):
    draft_id: str
    thread_id: str


class HandoffResponse(BaseModel):
    draft_id: str
    thread_id: str
    post: str
    hashtags: list[str]


@app.post("/api/handoff", response_model=HandoffResponse)
def handoff(req: HandoffRequest):
    """Send a Radar-approved draft into the Persona Panel for validation.

    Looks the draft up in the Radar's in-memory store and returns the exact text
    the Panel should vote on. The client then calls ``POST /api/panel/run`` with
    this ``thread_id`` and ``post``. Keeping the vote as a separate call means
    the Panel's human-in-the-loop flow (rework / re-vote) is unchanged.
    """

    from backend.mod03 import router as radar

    draft = radar._drafts.get(req.draft_id)
    if draft is None:
        raise HTTPException(404, "Unknown draft_id.")

    post = getattr(draft, "post_text", None) or getattr(draft, "text", "")
    hashtags = list(getattr(draft, "hashtags", []) or [])
    if not post:
        raise HTTPException(409, "Draft has no post text to validate.")

    log.info(
        "HANDOFF | draft=%s -> panel thread=%s | %d chars",
        req.draft_id,
        req.thread_id[:8],
        len(post),
    )
    return HandoffResponse(
        draft_id=req.draft_id,
        thread_id=req.thread_id,
        post=post,
        hashtags=hashtags,
    )
