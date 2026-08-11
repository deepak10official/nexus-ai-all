"""Suresh Yadav — the Cash Guardian voting agent."""

from __future__ import annotations

from typing import Optional

from backend.mod02.agents.base import PersonaAgent
from backend.mod02.prompts import get_persona, get_persona_prompt
from backend.mod02.utils.cache import VoteCache
from backend.mod02.utils.config import Settings

PERSONA_ID = "suresh"


def build_agent(
    *,
    settings: Optional[Settings] = None,
    cache: Optional[VoteCache] = None,
    llm=None,
) -> PersonaAgent:
    """Construct the Suresh persona agent."""

    return PersonaAgent(
        get_persona(PERSONA_ID),
        get_persona_prompt(PERSONA_ID),
        settings=settings,
        cache=cache,
        llm=llm,
    )
