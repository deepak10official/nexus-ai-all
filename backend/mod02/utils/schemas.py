"""Shared data models: LLM vote schemas plus the Persona definition.

``PersonaVote`` is the structured-output contract the LLM must satisfy; the rest
are plain aggregates used across the pipeline. ``Persona`` is a lightweight data
holder describing one synthetic reviewer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class VoteDecision(str, Enum):
    """The two possible ballots a persona can cast on a post."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"


class PersonaVote(BaseModel):
    """A single persona's structured verdict on a post.

    This is the schema the LLM is constrained to when voting. ``persona_id`` /
    ``persona_name`` are stamped on by the agent after the call so the model
    cannot get them wrong.
    """

    decision: VoteDecision = Field(
        description="The persona's ballot: APPROVE or REJECT."
    )
    confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="How strongly the persona holds this position, 0.0-1.0.",
    )
    reasoning: str = Field(
        description=(
            "A short first-person explanation, in the persona's own voice, of "
            "why they voted this way."
        )
    )
    suggested_changes: Optional[str] = Field(
        default=None,
        description=(
            "Concrete edits the persona wants. Required when the vote is "
            "REJECT; may be null for APPROVE."
        ),
    )

    persona_id: str = Field(default="", description="Stable persona identifier.")
    persona_name: str = Field(default="", description="Human-readable persona name.")

    @property
    def is_approval(self) -> bool:
        return self.decision == VoteDecision.APPROVE


class PanelResult(BaseModel):
    """Aggregated outcome of one round of voting by the full panel."""

    post: str = Field(description="The post text that was voted on this round.")
    votes: List[PersonaVote] = Field(description="Every persona's ballot.")
    approve_count: int = Field(description="Number of APPROVE ballots.")
    reject_count: int = Field(description="Number of REJECT ballots.")
    threshold: float = Field(description="Approval percentage required to pass (0-100).")
    passed: bool = Field(description="True when approve_count >= threshold.")
    image_url: Optional[str] = Field(default=None, description="Image URL attached to this round.")

    @property
    def total_votes(self) -> int:
        return len(self.votes)

    @property
    def tally(self) -> str:
        return f"{self.approve_count}/{self.total_votes} approvals"


class RevisionRound(BaseModel):
    """One iteration of the evaluate -> (maybe) revise loop."""

    round_number: int = Field(description="1-indexed round counter.")
    panel_result: PanelResult
    revised_post: Optional[str] = Field(
        default=None,
        description="The revised post produced after a failed round, if any.",
    )


class EvaluationResult(BaseModel):
    """The full trace returned by the pipeline for a single post."""

    original_post: str
    final_post: str
    passed: bool
    rounds: List[RevisionRound]

    @property
    def num_rounds(self) -> int:
        return len(self.rounds)

    @property
    def final_result(self) -> PanelResult:
        return self.rounds[-1].panel_result


@dataclass(frozen=True)
class Persona:
    """A synthetic Indian financial-content reviewer.

    Structured fields (name, archetype, emoji, ...) come from a persona markdown
    file's YAML frontmatter and are used by the UI and logs. ``profile`` is the
    markdown body — the prompt-ready description injected into the system prompt.
    """

    id: str
    name: str
    age: int
    location: str
    occupation: str
    archetype: str
    category: str = ""   # life-stage group (e.g. "Students & Early Career")
    tagline: str = ""  # short one-liner shown on the persona card
    emoji: str = ""
    profile: str = ""  # prompt-ready profile text (markdown body)

    def profile_block(self) -> str:
        """Return the prompt-ready persona description."""

        return self.profile.strip()
