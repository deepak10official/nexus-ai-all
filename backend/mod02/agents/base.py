"""Base class for a single persona voting agent.

Wraps a LangChain chat model with a persona-specific prompt and constrains the
output to the ``PersonaVote`` schema via ``with_structured_output``. Individual
persona agents (``agents/suresh.py`` etc.) are thin wrappers around this.
"""

from __future__ import annotations

import re
import time
from typing import Optional, Tuple

from langchain_core.prompts import ChatPromptTemplate

from backend.mod02.model.factory import build_chat_model
from backend.mod02.prompts.base import prompt_values
from backend.mod02.utils.cache import VoteCache
from backend.mod02.utils.config import Settings, get_settings
from backend.core.logging import get_logger
from backend.mod02.utils.schemas import Persona, PersonaVote, VoteDecision


# Groq/OpenAI-style structured output occasionally comes back as plain prose
# instead of a tool call ("tool_use_failed"). The model's answer is still in the
# error payload under `failed_generation`, so we salvage it rather than throwing
# away a perfectly good opinion.
_FAILED_GEN_RE = re.compile(
    r"[\'\"]failed_generation[\'\"]\s*:\s*[\'\"](.+?)[\'\"]\s*\}",
    re.DOTALL,
)

_REJECT_MARKERS = (
    "cannot approve", "can not approve", "must be rejected", "should be rejected",
    "i reject", "vote reject", "should not be published", "do not approve",
    "must not be published", "reject this", "unacceptable", "dangerous advice",
)
_APPROVE_MARKERS = (
    "i approve", "vote approve", "acceptable to publish", "safe to publish",
    "i'm impressed", "i am impressed", "happy to approve", "this is fine",
    "acceptable, and", "accurate, secure, and acceptable",
)


def _extract_failed_generation(exc: Exception) -> str:
    """Pull the model's raw prose out of a tool_use_failed error, if present."""

    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        text = (body.get("error") or {}).get("failed_generation")
        if text:
            return str(text).strip()

    match = _FAILED_GEN_RE.search(str(exc))
    return match.group(1).strip() if match else ""


def _infer_decision(text: str) -> Tuple[VoteDecision, float]:
    """Best-effort read of a verdict from free prose.

    Returns the decision plus a modest confidence, since this is a heuristic
    rescue rather than a clean structured answer.
    """

    lowered = text.lower()
    rejects = sum(1 for m in _REJECT_MARKERS if m in lowered)
    approves = sum(1 for m in _APPROVE_MARKERS if m in lowered)

    if rejects > approves:
        return VoteDecision.REJECT, 0.6
    if approves > rejects:
        return VoteDecision.APPROVE, 0.6
    # Genuinely ambiguous: stay cautious, but flag low confidence.
    return VoteDecision.REJECT, 0.3


class PersonaAgent:
    """Casts one persona's vote on a post."""

    def __init__(
        self,
        persona: Persona,
        prompt: ChatPromptTemplate,
        *,
        settings: Optional[Settings] = None,
        cache: Optional[VoteCache] = None,
        llm=None,
    ) -> None:
        self.persona = persona
        self.settings = settings or get_settings()
        self.cache = cache
        self.log = get_logger(f"agent.{persona.id}")
        base_llm = llm or build_chat_model(self.settings)
        # Constrain output to the vote schema; the prompt already has the persona
        # profile baked in, so only post/revision_context vary at runtime.
        # ``function_calling`` (the provider default) makes some models answer in
        # prose instead of calling the tool — set STRUCTURED_OUTPUT_METHOD to
        # json_schema/json_mode to ask for raw JSON instead.
        method = getattr(self.settings, "structured_output_method", "function_calling")
        try:
            structured = (
                base_llm.with_structured_output(PersonaVote)
                if method == "function_calling"
                else base_llm.with_structured_output(PersonaVote, method=method)
            )
        except (TypeError, ValueError) as exc:
            # Provider/binding doesn't support this method — fall back safely.
            self.log.warning(
                "structured output method %r unavailable (%s); using the default.",
                method,
                exc,
            )
            structured = base_llm.with_structured_output(PersonaVote)
        self._chain = prompt | structured

    @property
    def model_name(self) -> str:
        if self.settings.provider == "groq":
            return self.settings.groq_model
        if self.settings.provider == "anthropic":
            return self.settings.anthropic_model
        return self.settings.ollama_model

    def vote(
        self,
        post: str,
        previous_feedback: Optional[str] = None,
        previous_post: Optional[str] = None,
    ) -> PersonaVote:
        """Return this persona's structured vote for ``post``.

        On a re-vote, ``previous_post`` + ``previous_feedback`` give the voter
        the full history: what the earlier version said, what the panel said
        about it, and that the current post is the rework.
        """

        cacheable = previous_feedback is None and self.cache is not None
        if cacheable:
            cached = self.cache.get(self.persona.id, post, self.model_name)
            if cached is not None:
                self.log.info(
                    "%s %s -> %s (cached)",
                    self.persona.emoji,
                    self.persona.name,
                    cached.decision.value,
                )
                return cached

        is_revote = previous_feedback is not None
        self.log.info(
            "%s %s thinking... (model=%s, pass=%s)",
            self.persona.emoji,
            self.persona.name,
            self.model_name,
            "re-vote" if is_revote else "first",
        )
        self.log.debug("post under review: %s", post.strip().replace("\n", " "))
        started = time.perf_counter()
        values = prompt_values(post, previous_feedback, previous_post)
        vote = self._invoke_with_retry(values)

        vote.persona_id = self.persona.id
        vote.persona_name = self.persona.name
        vote = self._sanitize(vote)

        elapsed = time.perf_counter() - started
        self.log.info(
            "%s %s -> %s (conf %.2f) in %.1fs",
            self.persona.emoji,
            self.persona.name,
            vote.decision.value,
            vote.confidence,
            elapsed,
        )
        # Full ballot detail, so the log file is a complete audit trail of every
        # iteration rather than just the verdicts.
        reasoning = (vote.reasoning or "").strip().replace("\n", " ")
        if reasoning:
            self.log.info("    reasoning: %s", reasoning)
        wants = (vote.suggested_changes or "").strip().replace("\n", " ")
        if wants and vote.decision != VoteDecision.APPROVE:
            self.log.info("    wants: %s", wants)

        if cacheable:
            self.cache.set(self.persona.id, post, self.model_name, vote)
        return vote

    def _invoke_with_retry(self, values) -> PersonaVote:
        """Call the model, retrying transient structured-output failures.

        ``tool_use_failed`` happens when the model answers in prose instead of
        calling the vote function. It is stochastic, so a retry usually works.
        If every attempt fails we salvage the model's prose from the error
        payload — that text *is* the persona's opinion, and discarding it in
        favour of a blind REJECT would corrupt the tally.
        """

        attempts = max(1, getattr(self.settings, "persona_max_attempts", 2))
        last_exc: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            try:
                return self._chain.invoke(values)
            except Exception as exc:  # pragma: no cover - network/LLM dependent
                last_exc = exc
                self.log.warning(
                    "%s attempt %d/%d failed: %s",
                    self.persona.name,
                    attempt,
                    attempts,
                    str(exc)[:200],
                )
                if attempt < attempts:
                    time.sleep(0.6 * attempt)  # brief backoff before retrying

        # Every attempt failed — try to rescue the model's own words.
        prose = _extract_failed_generation(last_exc) if last_exc else ""
        if prose:
            decision, confidence = _infer_decision(prose)
            self.log.warning(
                "%s: recovered an unstructured answer -> %s (heuristic)",
                self.persona.name,
                decision.value,
            )
            return PersonaVote(
                decision=decision,
                confidence=confidence,
                reasoning=prose,
                suggested_changes=None,
                persona_id=self.persona.id,
                persona_name=self.persona.name,
            )

        self.log.error("%s errored with no recoverable answer: %s", self.persona.name, last_exc)
        return self._fallback_vote(str(last_exc))

    def _sanitize(self, vote: PersonaVote) -> PersonaVote:
        """Enforce invariants the LLM might violate."""

        if vote.decision != VoteDecision.APPROVE and not (
            vote.suggested_changes and vote.suggested_changes.strip()
        ):
            vote.suggested_changes = (
                "Please clarify and simplify the messaging to address the "
                "concerns above."
            )
        if vote.decision == VoteDecision.APPROVE:
            vote.suggested_changes = vote.suggested_changes or None
        return vote

    def _fallback_vote(self, error: str) -> PersonaVote:
        """Safe, conservative vote used only if the LLM call fails outright."""

        return PersonaVote(
            decision=VoteDecision.REJECT,
            confidence=0.0,
            reasoning=(
                f"({self.persona.name} could not be reached this round; casting a "
                "cautious REJECT.)"
            ),
            suggested_changes="Retry the review; the voter agent errored.",
            persona_id=self.persona.id,
            persona_name=self.persona.name,
        )
