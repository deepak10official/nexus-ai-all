"""End-to-end evaluation pipeline: vote -> (maybe) revise -> re-vote.

Orchestration is done by a LangGraph state graph (see ``backend.graph``): the
``vote`` and ``revise`` nodes loop until the post passes or the revision budget
is spent. This class keeps the same public API as before and is the entry point
for the CLI and tests. (The Streamlit app uses the *manual* graph directly,
with human-in-the-loop interrupts and per-session memory.)
"""

from __future__ import annotations

from typing import Callable, List, Optional

from backend.mod02.agents.panel import VotingPanel
from backend.mod02.agents.reviser import ReviserAgent
from backend.mod02.graph import PanelState, build_auto_graph
from backend.mod02.utils.config import Settings, get_settings
from backend.mod02.utils.schemas import EvaluationResult, PanelResult, RevisionRound

# Callback signature: (round_number, panel_result, revised_post_or_None)
ProgressCallback = Callable[[int, PanelResult, Optional[str]], None]


class EvaluationPipeline:
    """Runs the auto vote/revise LangGraph until pass or budget exhausted."""

    def __init__(
        self,
        *,
        settings: Optional[Settings] = None,
        panel: Optional[VotingPanel] = None,
        reviser: Optional[ReviserAgent] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.panel = panel or VotingPanel(settings=self.settings)
        self.reviser = reviser or ReviserAgent(settings=self.settings)
        self._graph = build_auto_graph(self.panel, self.reviser)

    def run(
        self,
        post: str,
        *,
        max_rounds: Optional[int] = None,
        on_round: Optional[ProgressCallback] = None,
    ) -> EvaluationResult:
        """Evaluate ``post``, auto-revising on failure up to ``max_rounds``.

        ``max_rounds`` counts revision attempts; the initial vote always runs.
        So max_rounds=2 means: vote, revise, vote, revise, vote (at most).
        """

        if not post or not post.strip():
            raise ValueError("post must be a non-empty string")

        budget = (
            self.settings.max_revision_rounds if max_rounds is None else max_rounds
        )
        initial: PanelState = {
            "original_post": post.strip(),
            "current_post": post.strip(),
            "feedback": "",
            "previous_post": "",
            "max_rounds": budget,
        }
        config = {"recursion_limit": max(25, budget * 3 + 10)}

        rounds: List[RevisionRound] = []
        pending: Optional[PanelResult] = None
        round_number = 0

        # Stream node updates so each round is reported as it completes. A
        # failed round's RevisionRound is emitted together with its revision
        # (matching the previous behaviour of revise-then-report).
        for chunk in self._graph.stream(initial, config=config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "vote":
                    round_number += 1
                    pending = update["rounds"][0]
                elif node == "revise":
                    revised = update["current_post"]
                    rounds.append(
                        RevisionRound(
                            round_number=round_number,
                            panel_result=pending,
                            revised_post=revised,
                        )
                    )
                    if on_round is not None:
                        on_round(round_number, pending, revised)
                    pending = None

        if pending is not None:
            rounds.append(
                RevisionRound(
                    round_number=round_number,
                    panel_result=pending,
                    revised_post=None,
                )
            )
            if on_round is not None:
                on_round(round_number, pending, None)

        return EvaluationResult(
            original_post=post.strip(),
            final_post=rounds[-1].panel_result.post,
            passed=rounds[-1].panel_result.passed,
            rounds=rounds,
        )


def evaluate_post(post: str, **kwargs) -> EvaluationResult:
    """Convenience one-shot helper."""

    return EvaluationPipeline().run(post, **kwargs)
