"""FastAPI bridge for the React (Vite) front-end.

This exposes the *same* human-in-the-loop manual graph the Streamlit app uses
(``backend/graph.py`` -> ``build_manual_graph``) over HTTP. The React client
holds a ``thread_id`` per browser session; LangGraph's in-memory checkpointer
keeps each session's state (rounds, feedback, evolving post) exactly like
Streamlit did — the only difference is the graph is reached over HTTP instead of
in-process.

Copy this file into your existing ``backend/`` package (next to ``graph.py``),
then run:

    uvicorn backend.api:app --reload --port 8000

Endpoints
---------
GET  /api/health                       -> {"ok": true}
GET  /api/personas                     -> the five persona profiles
GET  /api/settings                     -> provider / model / threshold / panel size
GET  /api/state?thread_id=...          -> current session state (rounds + flags)
POST /api/run     {thread_id, post}    -> run the panel (fresh vote or a re-vote)
POST /api/rework  {thread_id}          -> resume into the reviser, return new post
GET  /api/debug/state?thread_id=...    -> raw graph state (troubleshooting)
"""

from __future__ import annotations

import base64
import os
import uuid
from functools import lru_cache
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from langgraph.types import Command
from pydantic import BaseModel, Field

from backend.mod02.agents.panel import VotingPanel
from backend.mod02.graph import build_manual_graph
from backend.mod02.model.factory import LLMConfigError
from backend.mod02.prompts import PERSONAS, get_persona, get_persona_prompt
from backend.mod02.agents.base import PersonaAgent
from backend.mod02.utils.config import get_settings
from backend.core.logging import get_log_file, get_logger, start_run_log

log = get_logger("api")

router = APIRouter(prefix="/api/panel", tags=["persona-panel"])

# The Vite dev server runs on 5173 by default. Override with FRONTEND_ORIGIN
# (comma-separated) if you serve the front-end from somewhere else.
_origins = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")


# ----- graph singleton ---------------------------------------------------------

# One shared checkpointer for ALL graphs (default + custom-persona).  Every
# graph that is compiled with this checkpointer reads/writes the same state
# store, so /run (with custom personas) and /rework (with the default graph)
# both see the same thread state.
from backend.mod02.graph import _make_checkpointer as _mk_cp

_SHARED_CHECKPOINTER = _mk_cp()


@lru_cache(maxsize=1)
def _graph():
    """One compiled manual graph shared by all sessions.

    Session isolation comes from the per-session thread_id, not separate graphs
    — identical to the Streamlit app's ``@st.cache_resource`` behaviour.
    """

    return build_manual_graph(checkpointer=_SHARED_CHECKPOINTER)


def _build_agents_for(persona_ids: List[str]) -> List[PersonaAgent]:
    """Construct PersonaAgent instances for the given persona IDs."""

    agents = []
    for pid in persona_ids:
        persona = get_persona(pid)
        prompt = get_persona_prompt(pid)
        agents.append(PersonaAgent(persona, prompt))
    return agents


def _graph_with_personas(persona_ids: List[str]):
    """Build a manual graph using only the selected personas.

    Shares the module-level checkpointer so that state from a custom-persona
    /run is visible to subsequent /rework or /run calls.
    """

    agents = _build_agents_for(persona_ids)
    settings = get_settings()
    panel = VotingPanel(settings=settings, agents=agents)
    return build_manual_graph(panel=panel, checkpointer=_SHARED_CHECKPOINTER)


def _graph_or_503():
    try:
        return _graph()
    except LLMConfigError as exc:  # missing/invalid provider config
        raise HTTPException(status_code=503, detail=str(exc))


def _cfg(thread_id: str) -> dict:
    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required.")
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": 100}


# ----- serialization -----------------------------------------------------------

def _serialize_vote(v) -> dict:
    decision = getattr(v.decision, "value", v.decision)
    return {
        "persona_id": v.persona_id,
        "persona_name": v.persona_name,
        "decision": decision,
        "confidence": v.confidence,
        "reasoning": v.reasoning,
        "suggested_changes": v.suggested_changes,
        "is_approval": v.is_approval,
    }


def _serialize_round(r) -> dict:
    return {
        "post": r.post,
        "votes": [_serialize_vote(v) for v in r.votes],
        "approve_count": r.approve_count,
        "reject_count": r.reject_count,
        "threshold": r.threshold,
        "passed": r.passed,
        "total_votes": r.total_votes,
        "tally": r.tally,
        "image_url": getattr(r, "image_url", None),
    }



def _state_payload(cfg: dict, graph=None) -> dict:
    graph = graph or _graph_or_503()
    try:
        snap = graph.get_state(cfg)
        values = snap.values or {}
    except Exception:
        # Unknown / fresh thread: no checkpoint yet.
        values = {}
        snap = None

    rounds = values.get("rounds", []) or []
    waiting = bool(snap.next) if snap is not None else False
    last = rounds[-1] if rounds else None
    can_rework = waiting and last is not None and not last.passed
    return {
        "rounds": [_serialize_round(r) for r in rounds],
        "waiting": waiting,
        "can_rework": can_rework,
        "current_post": values.get("current_post", ""),
        "image_url": values.get("image_url") or None,
    }


# ----- request bodies ----------------------------------------------------------

class RunBody(BaseModel):
    thread_id: str
    post: str = ""
    persona_ids: Optional[List[str]] = Field(
        default=None,
        description="Subset of persona IDs to use. None = all.",
    )
    image_b64: Optional[str] = Field(
        default=None,
        description="Base64-encoded image to evaluate alongside the post.",
    )
    image_url: Optional[str] = Field(
        default=None,
        description="URL of the image (for UI display, not sent to the model).",
    )
    validate_text: bool = Field(
        default=True,
        description="Whether to validate post copy.",
    )
    validate_image: bool = Field(
        default=True,
        description="Whether to validate attached image.",
    )


class ThreadBody(BaseModel):
    thread_id: str


# ----- routes ------------------------------------------------------------------

@router.get("/personas")
def personas():
    return [
        {
            "id": p.id,
            "name": p.name,
            "age": p.age,
            "location": p.location,
            "occupation": p.occupation,
            "archetype": p.archetype,
            "category": p.category,
            "tagline": p.tagline,
            "emoji": p.emoji,
        }
        for p in PERSONAS
    ]


@router.get("/settings")
def settings():
    s = get_settings()
    label, model = {
        "groq": ("Groq", s.groq_model),
        "anthropic": ("Anthropic Claude", s.anthropic_model),
    }.get(s.provider, ("Ollama (local)", s.ollama_model))
    return {
        "provider": s.provider,
        "provider_label": label,
        "model": model,
        "approval_threshold": s.approval_threshold,
        "approval_threshold_label": f"≥{s.approval_threshold:.0f}%",
        "panel_size": s.panel_size,
    }


@router.get("/state")
def state(thread_id: str):
    return _state_payload(_cfg(thread_id))


def _round_count(cfg: dict, graph=None) -> int:
    try:
        g = graph or _graph_or_503()
        values = g.get_state(cfg).values or {}
        return len(values.get("rounds", []) or [])
    except Exception:
        return 0


def _fresh_invoke(
    graph, cfg: dict, post: str,
    image_b64: Optional[str] = None,
    image_url: Optional[str] = None,
    validate_text: bool = True,
    validate_image: bool = True,
) -> None:
    """Start a brand-new evaluation of ``post`` on this thread."""

    initial_state = {
        "original_post": post,
        "current_post": post,
        "feedback": "",
        "previous_post": "",
        "revised_post": None,
        "validate_text": validate_text,
        "validate_image": validate_image,
    }
    if image_b64:
        initial_state["image_b64"] = image_b64
    if image_url:
        initial_state["image_url"] = image_url
    graph.invoke(initial_state, config=cfg)


@router.post("/run")
def run(body: RunBody):
    # Validate evaluation mode
    if not body.validate_text and not body.validate_image:
        raise HTTPException(
            status_code=400,
            detail="Please select at least one evaluation target: Text or Image.",
        )

    post = body.post.strip()
    if body.validate_text and not post:
        raise HTTPException(status_code=400, detail="Please enter a post to evaluate text.")

    has_img = bool(body.image_b64 or body.image_url)
    if not body.validate_text and body.validate_image and not has_img:
        raise HTTPException(
            status_code=400,
            detail="Please attach an image to perform image validation.",
        )

    # Use a custom graph when persona_ids are specified, else the default.
    if body.persona_ids:
        # Validate all IDs exist.
        valid_ids = {p.id for p in PERSONAS}
        bad = set(body.persona_ids) - valid_ids
        if bad:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown persona IDs: {', '.join(sorted(bad))}",
            )
        try:
            graph = _graph_with_personas(body.persona_ids)
        except LLMConfigError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
    else:
        graph = _graph_or_503()

    cfg = _cfg(body.thread_id)

    try:
        snap = graph.get_state(cfg)
        waiting = bool(snap.next)
        before = len(snap.values.get("rounds", []) or [])
    except Exception:
        waiting = False
        before = 0

    mode_str = (
        "text+image" if (body.validate_text and body.validate_image and has_img)
        else "image-only" if (body.validate_image and has_img)
        else "text-only"
    )
    if before == 0:
        start_run_log(body.thread_id[:8])
    log.info(
        "RUN | thread=%s | round=%d | mode=%s | personas=%s | post=%s",
        body.thread_id[:8],
        before + 1,
        mode_str,
        body.persona_ids or "all",
        post[:120] if post else "(image only)",
    )

    if waiting:
        # Update image and validation flags on state if changing
        state_updates = {
            "validate_text": body.validate_text,
            "validate_image": body.validate_image,
        }
        if body.image_b64:
            state_updates["image_b64"] = body.image_b64
        if body.image_url:
            state_updates["image_url"] = body.image_url
        graph.update_state(cfg, state_updates)

        graph.invoke(
            Command(resume={"action": "revote", "post": post}),
            config=cfg,
        )
        if _round_count(cfg, graph=graph) == before:
            print("[api] resume added no round — falling back to a fresh vote.")
            _fresh_invoke(
                graph, cfg, post, body.image_b64, body.image_url,
                body.validate_text, body.validate_image,
            )
    else:
        _fresh_invoke(
            graph, cfg, post, body.image_b64, body.image_url,
            body.validate_text, body.validate_image,
        )

    return _state_payload(cfg, graph=graph)


@router.post("/rework")
def rework(body: ThreadBody):
    graph = _graph_or_503()
    cfg = _cfg(body.thread_id)
    snap = graph.get_state(cfg)
    if not bool(snap.next):
        raise HTTPException(
            status_code=409,
            detail="Nothing to rework — run the panel first.",
        )
    # Runs the reviser, then pauses again at the human node so the client can
    # review/edit the text before any re-vote.
    log.info("REWORK | thread=%s | revising from panel feedback", body.thread_id[:8])
    graph.invoke(Command(resume={"action": "rework"}), config=cfg)

    payload = _state_payload(cfg)
    if not payload.get("current_post"):
        # Some graphs park the reviser output on ``revised_post`` instead.
        try:
            values = graph.get_state(cfg).values or {}
            payload["current_post"] = values.get("revised_post") or ""
        except Exception:
            pass
    return payload


@router.get("/debug/logfile")
def debug_logfile():
    """Where the current run is being logged."""

    path = get_log_file()
    return {"log_file": str(path) if path else None}


@router.get("/debug/state")
def debug_state(thread_id: str):
    """Raw state dump — handy when the interrupt/resume contract misbehaves."""

    graph = _graph_or_503()
    snap = graph.get_state(_cfg(thread_id))
    values = snap.values or {}
    rounds = values.get("rounds", []) or []
    return {
        "next": list(snap.next or ()),
        "value_keys": sorted(values.keys()),
        "round_count": len(rounds),
        "current_post": values.get("current_post", ""),
        "revised_post": values.get("revised_post"),
        "posts_per_round": [r.post[:80] for r in rounds],
    }


# ----- image upload -----------------------------------------------------------

from backend.mod02.utils.vision import OUTPUT_DIR

_PANEL_IMAGE_DIR = os.path.join(str(OUTPUT_DIR), "panel")
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Accept an image upload and return its URL + base64 data.

    The client sends the base64 data back in the ``/run`` body so the graph
    can pass it to the vision model.
    """

    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}. Use JPEG, PNG, or WebP.",
        )

    data = await file.read()
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large ({len(data) / 1024 / 1024:.1f} MB). Max is 10 MB.",
        )

    os.makedirs(_PANEL_IMAGE_DIR, exist_ok=True)
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[
        file.content_type
    ]
    filename = f"{uuid.uuid4().hex[:12]}{ext}"
    filepath = os.path.join(_PANEL_IMAGE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(data)

    image_url = f"/generated/panel/{filename}"
    image_b64 = base64.b64encode(data).decode("ascii")

    log.info("Image uploaded: %s (%d KB)", filename, len(data) // 1024)
    return {
        "image_url": image_url,
        "image_b64": image_b64,
        "filename": filename,
        "size_kb": len(data) // 1024,
    }
