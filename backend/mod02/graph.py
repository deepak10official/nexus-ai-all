"""LangGraph orchestration for the voting panel.

Two compiled graphs share the same nodes (``vote``, ``revise``):

- **Auto graph** (CLI / ``EvaluationPipeline``): vote -> fail? -> revise -> vote
  ... looping until the post passes or the revision budget is spent.

- **Manual graph** (Streamlit): vote -> fail? -> ``human`` node, which pauses the
  graph with ``interrupt()`` and waits for the user's decision (rework / re-vote
  / stop). It is compiled with an in-memory checkpointer, so one session
  (``thread_id``) keeps its full state - every round's votes, the feedback, and
  the evolving post - across all iterations.

Manual flow, step by step::

    START -> vote --passed--> END
                \\--failed--> human  (interrupt: waits for the user)
        resume {"action": "rework"}            -> revise -> human (interrupt again,
                                                  so the user can review the text)
        resume {"action": "revote", "post": p} -> vote  (re-vote, possibly edited)
        resume {"action": "stop"}              -> END
"""

from __future__ import annotations

import operator
from typing import Annotated, List, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.mod02.agents.panel import VotingPanel
from backend.mod02.agents.reviser import ReviserAgent
from backend.core.logging import get_logger
from backend.mod02.utils.schemas import PanelResult
from backend.mod02.utils.voting import format_full_feedback

log = get_logger("graph")


def _make_checkpointer() -> MemorySaver:
    """In-memory checkpointer that can (de)serialize our vote schemas."""

    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("backend.mod02.utils.schemas", "PanelResult"),
            ("backend.mod02.utils.schemas", "PersonaVote"),
            ("backend.mod02.utils.schemas", "VoteDecision"),
        ]
    )
    return MemorySaver(serde=serde)


class PanelState(TypedDict, total=False):
    """Shared state carried through the graph (checkpointed per session)."""

    original_post: str  # the user's very first post (anchor for reworks)
    current_post: str  # the post text being voted on right now
    rounds: Annotated[List[PanelResult], operator.add]  # session round history
    passed: bool
    feedback: str  # full previous-round feedback, shown to voters on re-vote
    previous_post: str  # the version of the post that feedback was given on
    revised_post: Optional[str]  # latest reviser output (for the UI)
    decision: str  # last human decision: rework | revote | stop
    max_rounds: int  # revision budget (auto mode only)


def _make_nodes(panel: VotingPanel, reviser: ReviserAgent):
    """Build the node functions bound to concrete panel/reviser agents."""

    def vote(state: PanelState) -> PanelState:
        round_no = len(state.get("rounds", [])) + 1
        log.info("Graph: vote node (round %d)", round_no)
        result = panel.evaluate(
            state["current_post"],
            previous_feedback=state.get("feedback") or None,
            previous_post=state.get("previous_post") or None,
        )
        return {"rounds": [result], "passed": result.passed}

    def revise(state: PanelState) -> PanelState:
        last = state["rounds"][-1]
        log.info("Graph: revise node (after round %d)", len(state["rounds"]))
        feedback = format_full_feedback(last)
        revised = reviser.revise(
            state["current_post"],
            feedback,
            original_post=state.get("original_post"),
        )
        # Remember the version that was reviewed and its full feedback, so the
        # next vote round sees the complete history (old post -> feedback ->
        # rework -> new post).
        return {
            "current_post": revised,
            "revised_post": revised,
            "feedback": feedback,
            "previous_post": last.post,
        }

    def human(state: PanelState) -> PanelState:
        """Pause the graph and wait for the user's decision (manual mode)."""

        last = state["rounds"][-1]
        decision = interrupt(
            {
                "round": len(state["rounds"]),
                "tally": last.tally,
                "passed": last.passed,
                "revised_post": state.get("revised_post"),
            }
        )
        action = str(decision.get("action", "revote"))
        log.info("Graph: human decision -> %s", action)
        update: PanelState = {"decision": action}
        post = (decision.get("post") or "").strip()
        if post:
            update["current_post"] = post
        if action == "revote":
            # Even if the user edited the text by hand, carry the previous
            # version + its full feedback into the next vote round.
            update["feedback"] = format_full_feedback(last)
            update["previous_post"] = last.post
        return update

    return vote, revise, human


def build_auto_graph(
    panel: Optional[VotingPanel] = None, reviser: Optional[ReviserAgent] = None
):
    """Vote/revise loop that runs unattended until pass or budget exhausted."""

    panel = panel or VotingPanel()
    reviser = reviser or ReviserAgent()
    vote, revise, _ = _make_nodes(panel, reviser)

    def route_after_vote(state: PanelState) -> str:
        if state.get("passed"):
            return END
        revisions_used = len(state.get("rounds", [])) - 1
        if revisions_used >= state.get("max_rounds", 2):
            return END
        return "revise"

    graph = StateGraph(PanelState)
    graph.add_node("vote", vote)
    graph.add_node("revise", revise)
    graph.add_edge(START, "vote")
    graph.add_conditional_edges(
        "vote", route_after_vote, {"revise": "revise", END: END}
    )
    graph.add_edge("revise", "vote")
    return graph.compile()


def build_manual_graph(
    panel: Optional[VotingPanel] = None,
    reviser: Optional[ReviserAgent] = None,
    checkpointer=None,
):
    """Human-in-the-loop graph with per-session (thread_id) state memory.

    Compiled with an in-memory checkpointer: every invoke/resume for the same
    ``{"configurable": {"thread_id": ...}}`` continues the same session state.
    """

    panel = panel or VotingPanel()
    reviser = reviser or ReviserAgent()
    vote, revise, human = _make_nodes(panel, reviser)

    def route_after_vote(state: PanelState) -> str:
        return END if state.get("passed") else "human"

    def route_after_human(state: PanelState) -> str:
        return {"rework": "revise", "stop": END}.get(
            state.get("decision", "revote"), "vote"
        )

    graph = StateGraph(PanelState)
    graph.add_node("vote", vote)
    graph.add_node("revise", revise)
    graph.add_node("human", human)
    graph.add_edge(START, "vote")
    graph.add_conditional_edges(
        "vote", route_after_vote, {"human": "human", END: END}
    )
    graph.add_conditional_edges(
        "human", route_after_human, {"revise": "revise", "vote": "vote", END: END}
    )
    # After a rework, go back to the human so the user reviews the text before
    # any re-vote. Nothing runs without an explicit user decision.
    graph.add_edge("revise", "human")
    return graph.compile(checkpointer=checkpointer or _make_checkpointer())
