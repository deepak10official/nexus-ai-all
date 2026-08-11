"""Reviser prompt, loaded from Markdown.

The wording lives in ``templates/reviser_system.md`` and
``templates/reviser_human.md`` so it can be edited without touching code.
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from backend.mod02.prompts.loader import load_template

SYSTEM_TEMPLATE = load_template("reviser_system.md")
HUMAN_TEMPLATE = load_template("reviser_human.md")


def build_reviser_prompt() -> ChatPromptTemplate:
    """Return the reusable chat prompt template for the reviser."""

    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_TEMPLATE),
            ("human", HUMAN_TEMPLATE),
        ]
    )


PROMPT = build_reviser_prompt()
