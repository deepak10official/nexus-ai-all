"""The auto-reviser agent.

Given the original post and the panel's aggregated feedback, produces an improved
version that tries to win over the dissenting personas. Run slightly cooler than
the personas for more focused, deterministic edits.
"""

from __future__ import annotations

import time
from typing import Optional

from langchain_core.output_parsers import StrOutputParser

from backend.mod02.model.factory import build_chat_model
from backend.mod02.prompts.reviser import PROMPT
from backend.mod02.utils.config import Settings, get_settings
from backend.core.logging import get_logger

log = get_logger("reviser")


class ReviserAgent:
    """Rewrites a post to address panel feedback."""

    def __init__(
        self,
        *,
        settings: Optional[Settings] = None,
        llm=None,
        temperature: float = 0.4,
    ) -> None:
        self.settings = settings or get_settings()
        base_llm = llm or build_chat_model(self.settings, temperature=temperature)
        self._chain = PROMPT | base_llm | StrOutputParser()

    def revise(
        self, post: str, feedback: str, original_post: Optional[str] = None
    ) -> str:
        """Return a revised post addressing ``feedback``.

        ``original_post`` (the user's very first version) is passed as an anchor
        so that repeated reworks stay on the same subject/offer instead of
        drifting. Falls back to ``post`` if the LLM call fails.
        """

        anchor = ""
        if (
            original_post
            and original_post.strip()
            and original_post.strip() != post.strip()
        ):
            anchor = (
                "\n# ORIGINAL post (the true subject and offer to stay faithful to)\n"
                '"""\n' + original_post.strip() + '\n"""\n'
            )

        log.info("Reviser rewriting post from panel feedback...")
        started = time.perf_counter()
        try:
            revised = self._chain.invoke(
                {
                    "post": post.strip(),
                    "feedback": feedback.strip(),
                    "original_anchor": anchor,
                }
            )
        except Exception as exc:  # pragma: no cover - network/LLM dependent
            log.warning("Reviser errored (%s); keeping original post.", exc)
            return post
        revised = (revised or "").strip()
        elapsed = time.perf_counter() - started
        log.info("Reviser produced %d chars in %.1fs", len(revised), elapsed)
        return revised or post
