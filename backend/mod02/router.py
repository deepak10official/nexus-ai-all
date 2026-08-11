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

import os
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from langgraph.types import Command
from pydantic import BaseModel

from backend.mod02.graph import build_manual_graph
from backend.mod02.model.factory import LLMConfigError
from backend.mod02.prompts import PERSONAS
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

@lru_cache(maxsize=1)
def _graph():
    """One compiled manual graph (with MemorySaver) shared by all sessions.

    Session isolation comes from the per-session thread_id, not separate graphs
    — identical to the Streamlit app's ``@st.cache_resource`` behaviour.
    """

    return build_manual_graph()


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
    }


def _state_payload(cfg: dict) -> dict:
    graph = _graph_or_503()
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
    }


# ----- request bodies ----------------------------------------------------------

class RunBody(BaseModel):
    thread_id: str
    post: str


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
        "panel_size": s.panel_size,
    }


@router.get("/state")
def state(thread_id: str):
    return _state_payload(_cfg(thread_id))


def _round_count(cfg: dict) -> int:
    try:
        values = _graph_or_503().get_state(cfg).values or {}
        return len(values.get("rounds", []) or [])
    except Exception:
        return 0


def _fresh_invoke(graph, cfg: dict, post: str) -> None:
    """Start a brand-new evaluation of ``post`` on this thread."""

    graph.invoke(
        {
            "original_post": post,
            "current_post": post,
            "feedback": "",
            "previous_post": "",
            "revised_post": None,
        },
        config=cfg,
    )


@router.post("/run")
def run(body: RunBody):
    graph = _graph_or_503()
    cfg = _cfg(body.thread_id)
    post = body.post.strip()
    if not post:
        raise HTTPException(status_code=400, detail="Please enter a post.")

    snap = graph.get_state(cfg)
    waiting = bool(snap.next)
    before = len(snap.values.get("rounds", []) or [])

    if before == 0:
        # A brand-new draft on this thread: give the run its own log file so the
        # filename reflects when the run happened, not when the server booted.
        start_run_log(body.thread_id[:8])
    log.info("RUN | thread=%s | round=%d | post=%s", body.thread_id[:8], before + 1, post[:120])

    if waiting:
        # The manual graph's `human` node applies the resumed post itself
        # (`if post: update["current_post"] = post`), so the payload is enough —
        # no extra state write needed here.
        graph.invoke(
            Command(resume={"action": "revote", "post": post}),
            config=cfg,
        )

        # Self-heal: if resuming produced no new round, the interrupt contract
        # didn't route us into the vote node. Run the post fresh on this same
        # thread so the user still gets a result instead of a silent no-op.
        if _round_count(cfg) == before:
            print("[api] resume added no round — falling back to a fresh vote.")
            _fresh_invoke(graph, cfg, post)
    else:
        _fresh_invoke(graph, cfg, post)

    return _state_payload(cfg)


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
