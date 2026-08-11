"""Prompt registry.

All prompt wording lives in Markdown (``templates/*.md`` and ``personas/*.md``).
This module loads the persona definitions from those files, builds a
ready-to-use prompt per persona, and exposes lookups used by the agents and UI.
"""

from __future__ import annotations

from typing import Dict, List

from backend.mod02.prompts.base import (
    format_revision_context,
    persona_chat_prompt,
    prompt_values,
)
from backend.mod02.prompts.loader import load_persona_markdown
from backend.mod02.prompts.reviser import PROMPT as REVISER_PROMPT
from backend.mod02.utils.schemas import Persona

# Canonical panel ordering (also the order shown in the UI).
PERSONA_ORDER: List[str] = ["suresh", "meena", "arjun", "kavya", "ramesh"]


def _build_persona(persona_id: str) -> Persona:
    meta, body = load_persona_markdown(persona_id)
    return Persona(
        id=str(meta.get("id", persona_id)),
        name=str(meta.get("name", persona_id.title())),
        age=int(meta.get("age", 0)),
        location=str(meta.get("location", "")),
        occupation=str(meta.get("occupation", "")),
        archetype=str(meta.get("archetype", "")),
        tagline=str(meta.get("tagline", "")),
        emoji=str(meta.get("emoji", "")),
        profile=body,
    )


PERSONAS: List[Persona] = [_build_persona(pid) for pid in PERSONA_ORDER]

_PERSONA_INDEX: Dict[str, Persona] = {p.id: p for p in PERSONAS}
_PERSONA_PROMPTS = {p.id: persona_chat_prompt(p) for p in PERSONAS}


def get_persona(persona_id: str) -> Persona:
    """Look up a persona by id, raising a clear error if unknown."""

    try:
        return _PERSONA_INDEX[persona_id]
    except KeyError as exc:
        valid = ", ".join(_PERSONA_INDEX)
        raise KeyError(f"Unknown persona '{persona_id}'. Valid ids: {valid}") from exc


def get_persona_prompt(persona_id: str):
    """Return the ready-to-use ChatPromptTemplate for a persona."""

    if persona_id not in _PERSONA_PROMPTS:
        get_persona(persona_id)  # raises a helpful error
    return _PERSONA_PROMPTS[persona_id]


__all__ = [
    "PERSONAS",
    "PERSONA_ORDER",
    "get_persona",
    "get_persona_prompt",
    "persona_chat_prompt",
    "format_revision_context",
    "prompt_values",
    "REVISER_PROMPT",
]
