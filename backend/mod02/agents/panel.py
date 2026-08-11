"""The voting panel: runs all persona agents and tallies the result.

Votes run sequentially by default (one persona at a time) so providers with
tight tokens-per-minute limits are not flooded. Pass ``parallel=True`` to fan
them out on a thread pool instead. Tallying and feedback summarisation live in
``backend.utils.voting``.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from backend.mod02.agents.base import PersonaAgent
from backend.mod02.utils.cache import VoteCache
from backend.mod02.utils.config import Settings, get_settings
from backend.core.logging import get_logger
from backend.mod02.utils.schemas import PanelResult, PersonaVote
from backend.mod02.utils.voting import sort_votes_by, tally_votes

log = get_logger("panel")


def _default_agents(
    settings: Settings, cache: Optional[VoteCache]
) -> List[PersonaAgent]:
    """Build the standard five persona agents from their individual modules."""

    from backend.mod02.agents import arjun, kavya, meena, ramesh, suresh

    builders = [suresh, meena, arjun, kavya, ramesh]
    return [m.build_agent(settings=settings, cache=cache) for m in builders]


class VotingPanel:
    """Coordinates the persona agents and aggregates their ballots."""

    def __init__(
        self,
        *,
        settings: Optional[Settings] = None,
        cache: Optional[VoteCache] = None,
        agents: Optional[List[PersonaAgent]] = None,
        parallel: Optional[bool] = None,
    ) -> None:
        self.settings = settings or get_settings()
        # Explicit argument wins; otherwise fall back to PANEL_PARALLEL.
        self.parallel = (
            parallel
            if parallel is not None
            else getattr(self.settings, "panel_parallel", False)
        )
        self.cache = cache
        if self.cache is None and self.settings.caching_enabled:
            self.cache = VoteCache(self.settings)
        self.agents = agents or _default_agents(self.settings, self.cache)
        self.personas = [a.persona for a in self.agents]

    def evaluate(
        self,
        post: str,
        previous_feedback: Optional[str] = None,
        previous_post: Optional[str] = None,
    ) -> PanelResult:
        """Collect every persona's vote and tally the outcome.

        ``previous_post`` and ``previous_feedback`` are set on re-votes so each
        persona sees the earlier version, the feedback it received, and knows
        the current post is the rework.
        """

        mode = "parallel" if (self.parallel and len(self.agents) > 1) else "sequential"
        log.info(
            "Panel evaluating post with %d agents (%s)...", len(self.agents), mode
        )
        started = time.perf_counter()

        if self.parallel and len(self.agents) > 1:
            votes = self._vote_parallel(post, previous_feedback, previous_post)
        else:
            votes = [
                a.vote(post, previous_feedback, previous_post) for a in self.agents
            ]

        votes = sort_votes_by(votes, [p.id for p in self.personas])
        result = tally_votes(post, votes, self.settings.approval_threshold)
        elapsed = time.perf_counter() - started
        log.info(
            "Panel result: %s (A:%d R:%d) -> %s in %.1fs",
            result.tally,
            result.approve_count,
            result.reject_count,
            "PASS" if result.passed else "FAIL",
            elapsed,
        )
        return result

    def _vote_parallel(
        self,
        post: str,
        previous_feedback: Optional[str],
        previous_post: Optional[str] = None,
    ) -> List[PersonaVote]:
        with ThreadPoolExecutor(max_workers=len(self.agents)) as pool:
            futures = [
                pool.submit(agent.vote, post, previous_feedback, previous_post)
                for agent in self.agents
            ]
            return [f.result() for f in futures]
