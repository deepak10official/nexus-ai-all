"""Voting helper functions: tallying ballots and summarising feedback.

Kept free of any LLM/agent state so they are trivial to unit-test.
"""

from __future__ import annotations

from typing import List

from backend.mod02.utils.schemas import PanelResult, PersonaVote, VoteDecision


def tally_votes(
    post: str,
    votes: List[PersonaVote],
    threshold: float,
    image_url: Optional[str] = None,
) -> PanelResult:
    """Count ballots and decide pass/fail against ``threshold`` percentage.

    ``threshold`` is a float 0-100 representing the minimum percentage of
    APPROVE votes required to pass.
    """

    approve = sum(v.decision == VoteDecision.APPROVE for v in votes)
    reject = sum(v.decision == VoteDecision.REJECT for v in votes)
    total = len(votes)
    approve_pct = (approve / total * 100) if total else 0
    return PanelResult(
        post=post,
        votes=votes,
        approve_count=approve,
        reject_count=reject,
        threshold=threshold,
        passed=approve_pct >= threshold,
        image_url=image_url,
    )



def summarize_feedback(result: PanelResult) -> str:
    """Condense REJECT feedback into a short block (persona context)."""

    lines: List[str] = []
    for vote in result.votes:
        if vote.decision == VoteDecision.APPROVE:
            continue
        change = (vote.suggested_changes or "").strip()
        lines.append(
            f"- {vote.persona_name} voted {vote.decision.value}: "
            f"{vote.reasoning.strip()}"
            + (f" Suggested change: {change}" if change else "")
        )
    if not lines:
        return "No specific objections were raised."
    return "\n".join(lines)


def _archetype_for(persona_id: str) -> str:
    """Best-effort archetype lookup (lazy import to avoid a circular import)."""

    try:
        from backend.mod02.prompts import get_persona

        return get_persona(persona_id).archetype
    except Exception:
        return ""


def format_full_feedback(result: PanelResult) -> str:
    """Full, verbatim feedback from EVERY persona for the reviser.

    Unlike ``summarize_feedback`` this keeps all five reviewers (including the
    approvers, so the reviser knows what already works and preserves it) and
    reproduces each reviewer's complete reasoning and requested changes.
    """

    blocks: List[str] = []
    for vote in result.votes:
        archetype = _archetype_for(vote.persona_id)
        who = vote.persona_name + (f" — {archetype}" if archetype else "")
        block = [
            f"### {who}",
            f"Vote: {vote.decision.value} (confidence {vote.confidence:.0%})",
            f"Reasoning: {vote.reasoning.strip()}",
        ]
        change = (vote.suggested_changes or "").strip()
        if vote.decision == VoteDecision.APPROVE:
            block.append(
                "Requested changes: none — this reviewer approved. Keep what "
                "they liked intact."
            )
        else:
            block.append(f"Requested changes: {change or 'not specified'}")
        blocks.append("\n".join(block))

    return "\n\n".join(blocks)


def sort_votes_by(votes: List[PersonaVote], persona_ids: List[str]) -> List[PersonaVote]:
    """Return ``votes`` reordered to match a canonical persona ordering."""

    order = {pid: i for i, pid in enumerate(persona_ids)}
    return sorted(votes, key=lambda v: order.get(v.persona_id, 999))
