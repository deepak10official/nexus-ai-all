"""Pydantic models. The LLM is forced into SocialPost; everything else
is API contract shared with the frontend."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ─────────────────────── structured LLM output ───────────────────────


class SocialPost(BaseModel):
    """The shape the LLM must return. This is the schema handed to the
    output parser, so the field descriptions are effectively prompt text —
    edit them carefully."""

    post_text: str = Field(
        description=(
            "The ready-to-publish post for X. Under 260 characters including "
            "hashtags. No emoji spam, no more than one emoji. Must read as a "
            "brand voice, not a press release."
        )
    )
    hashtags: list[str] = Field(
        description=(
            "2 to 4 hashtags, each starting with '#'. Must include the "
            "trending hashtag being reacted to and #BharatConnect."
        )
    )
    angle: str = Field(
        description=(
            "One sentence explaining the creative link between the trend and "
            "Bharat Connect. This is shown to the human reviewer, not published."
        )
    )
    tone: Literal["celebratory", "informative", "conversational", "civic"] = Field(
        description="The register used for this post."
    )
    risk_notes: str = Field(
        description=(
            "Any reason a reviewer might reject this — ambiguity in the trend, "
            "possible misreading, tenuous link. Write 'none' if genuinely clean."
        )
    )
    image_prompt: str = Field(
        description=(
            "A visual brief for an image to accompany this post, 15-40 words. "
            "Describe a concrete scene, not an abstract concept: real Indian "
            "settings, everyday people, objects, light. Do NOT describe any "
            "text, words, letters, logos or signage — branding is added "
            "separately. Leave the lower-right of the frame visually quiet. "
            "Avoid depicting identifiable public figures, religious imagery, "
            "political symbols, currency notes, or competitor branding."
        )
    )

    @field_validator("hashtags")
    @classmethod
    def _normalise_tags(cls, v: list[str]) -> list[str]:
        out = []
        for tag in v:
            tag = tag.strip()
            if tag and not tag.startswith("#"):
                tag = "#" + tag
            if tag and tag not in out:
                out.append(tag)
        return out


# ─────────────────────────── API contracts ───────────────────────────


class ScoredTrend(BaseModel):
    """One trend, fully evaluated. Every field here is rendered in the UI."""

    name: str
    is_hashtag: bool

    # Multilingual
    language: str = Field(description="BCP-47-ish code: en, hi, hi-Latn, ta …")
    language_label: str = Field(description="Human-readable, e.g. 'Hindi (Devanagari)'")
    script: str = Field(description="Detected Unicode script, e.g. 'Devanagari'")
    language_confidence: Literal["high", "low"] = "high"

    # Classification
    category: str = Field(description="Sports, Business & Finance, Technology …")
    category_key: str = Field(description="Short key the UI maps to an accent colour")

    # Relevance
    score: int = Field(ge=0, le=100, description="BBPS Relevance Score")
    band: Literal["auto_draft", "review", "monitor", "ignore", "blocked"]
    action: Literal["AUTO_DRAFT", "HUMAN_REVIEW", "MONITOR", "IGNORE", "BLOCKED"]
    band_range: str = Field(description="The score window this band covers")
    rationale: str
    blocked_reason: str | None = None


class TrendFeed(BaseModel):
    region: str
    fetched_at: datetime
    tier: Literal["live", "api", "cache"]
    tier_note: str
    trends: list[ScoredTrend]


class GenerateRequest(BaseModel):
    hashtag: str
    # Manual test mode: score a hashtag that is not in the live feed and
    # draft against it even if it falls below the band threshold. Never
    # bypasses the off-limits blocklist.
    force: bool = False


class Draft(BaseModel):
    draft_id: str
    hashtag: str
    language: str
    language_label: str
    category: str
    score: int
    band: str
    action: str
    post: SocialPost
    generated_at: datetime
    latency_ms: int
    # True once a reviewer has manually edited the copy or the brief. Shown
    # in the UI so an edited draft is never mistaken for raw model output.
    edited: bool = False


class ImageRequest(BaseModel):
    draft_id: str
    # Lets the reviewer tune the visual brief without regenerating the post.
    prompt_override: str | None = None


class ImageResult(BaseModel):
    """Sent to the browser. Model, provider and licence are deliberately
    absent — they are operator concerns, and shipping them would expose
    them in DevTools even if the UI never rendered them. They are logged
    server-side instead."""

    draft_id: str
    filename: str
    url: str
    prompt_used: str
    width: int | None = None
    height: int | None = None
    latency_ms: int
    removed_from_brief: list[str] = []
    warning: str | None = None
    created_at: datetime


class DraftEdit(BaseModel):
    """A reviewer's manual edit. Any field left None is untouched, so the
    post and the image brief can be edited independently."""

    post_text: str | None = None
    hashtags: list[str] | None = None
    image_prompt: str | None = None


class DecisionRequest(BaseModel):
    draft_id: str
    action: Literal["approve", "reject"]
    # Which half of the draft this decision applies to. The post and the
    # image are judged separately — a good post with a poor image should
    # not force both to be regenerated.
    target: Literal["post", "image", "final"] = "final"
    note: str | None = None


class DecisionResponse(BaseModel):
    draft_id: str
    action: str
    target: str
    status: str
    message: str
    decided_at: datetime
