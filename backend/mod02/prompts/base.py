"""Shared prompt scaffolding for persona voting, loaded from Markdown.

The wording lives in ``templates/persona_system.md``, ``templates/persona_human.md``
and ``templates/revision_context.md``. ``persona_chat_prompt`` bakes a specific
persona's profile into that structure and returns a ready-to-use
``ChatPromptTemplate`` whose only runtime variables are ``post`` and
``revision_context``.
"""

from __future__ import annotations

from typing import Optional

from langchain_core.prompts import ChatPromptTemplate

from backend.mod02.prompts.loader import load_template
from backend.mod02.utils.schemas import Persona

SYSTEM_TEMPLATE = load_template("persona_system.md")
HUMAN_TEMPLATE = load_template("persona_human.md")
REVISION_CONTEXT_TEMPLATE = load_template("revision_context.md")


def persona_chat_prompt(persona: Persona) -> ChatPromptTemplate:
    """Return a ChatPromptTemplate with ``persona`` baked in.

    The returned template only needs ``post`` and ``revision_context`` at invoke
    time; the persona profile and name are pre-filled.
    """

    template = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_TEMPLATE),
            ("human", HUMAN_TEMPLATE),
        ]
    )
    return template.partial(
        persona_profile=persona.profile_block(),
        persona_name=persona.name,
    )


def format_revision_context(
    previous_feedback: Optional[str], previous_post: Optional[str] = None
) -> str:
    """Build the optional revision-context block for the human message.

    On a re-vote this gives the voters the full history: the previous version
    of the post, the feedback the panel gave on it, and the note that the
    current post is the rework produced from that feedback.
    """

    if not previous_feedback:
        return ""
    return "\n" + REVISION_CONTEXT_TEMPLATE.format(
        previous_post=(previous_post or "(not available)").strip(),
        previous_feedback=previous_feedback.strip(),
    )


def prompt_values(
    post: str,
    previous_feedback: Optional[str] = None,
    previous_post: Optional[str] = None,
) -> dict:
    """Assemble the runtime values a persona prompt expects."""

    return {
        "post": post.strip(),
        "revision_context": format_revision_context(previous_feedback, previous_post),
    }
