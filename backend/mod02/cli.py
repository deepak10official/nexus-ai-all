"""Command-line runner for quick, key-only demos and debugging.

Usage:
    python -m backend.cli "Your post text here"
    echo "Your post" | python -m backend.cli
"""

from __future__ import annotations

import sys

from backend.mod02.pipeline import EvaluationPipeline
from backend.mod02.prompts import get_persona
from backend.mod02.utils.config import get_settings
from backend.mod02.utils.schemas import VoteDecision

_DECISION_ICON = {
    VoteDecision.APPROVE: "[APPROVE]",
    VoteDecision.REJECT: "[REJECT] ",
}


def _read_post(argv: list[str]) -> str:
    if len(argv) > 1:
        return " ".join(argv[1:]).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return (
        "Get an instant personal loan in 5 minutes! No paperwork, no questions. "
        "Just share your OTP and money is yours. Limited time offer!"
    )


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    post = _read_post(argv)
    if not post:
        print("No post provided.", file=sys.stderr)
        return 2

    settings = get_settings()
    print(f"Provider: {settings.provider} | model configured")
    print(f"Threshold to pass: {settings.approval_threshold}/{settings.panel_size}\n")

    pipeline = EvaluationPipeline(settings=settings)

    def on_round(round_number, result, revised_post):
        print(f"===== Round {round_number} =====")
        print(f"Post:\n{result.post}\n")
        for vote in result.votes:
            persona = get_persona(vote.persona_id)
            icon = _DECISION_ICON.get(vote.decision, "")
            print(
                f"{icon} {persona.emoji} {vote.persona_name} "
                f"(conf {vote.confidence:.1f})"
            )
            print(f"      {vote.reasoning.strip()}")
            if vote.suggested_changes and vote.decision != VoteDecision.APPROVE:
                print(f"      -> {vote.suggested_changes.strip()}")
        print(f"\nTally: {result.tally} -> {'PASS' if result.passed else 'FAIL'}")
        if revised_post is not None:
            print("\nAuto-revising for next round...\n")

    result = pipeline.run(post, on_round=on_round)

    print("\n============================")
    print("FINAL:", "PASSED" if result.passed else "NOT PASSED")
    print(f"Rounds: {result.num_rounds}")
    if result.final_post != result.original_post:
        print(f"\nFinal post:\n{result.final_post}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
