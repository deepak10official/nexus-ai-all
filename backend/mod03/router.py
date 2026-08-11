"""
MOD03 National Trend Radar — API.

Routes:
    GET  /api/health          config + model readiness
    GET  /api/trends          scored trend feed
    POST /api/generate        run the agent on one hashtag
    POST /api/decision        record approve/reject (simulated publish)
    GET  /api/log             decision audit trail
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.staticfiles import StaticFiles

from backend.mod03.services import trend_service
from backend.mod03.agents.agent import AgentError, generate_post
from backend.mod03.services.imagegen import OUTPUT_DIR, ImageError, generate_image
from backend.mod03.utils.config import settings
from backend.core.logging import configure as configure_logging
from backend.core.logging import current_log_file, get_logger, start_run
from backend.mod03.services.scoring import evaluate
from backend.mod03.utils.schemas import (
    ScoredTrend,
    ImageRequest,
    ImageResult,
    DecisionRequest,
    DecisionResponse,
    Draft,
    DraftEdit,
    GenerateRequest,
    TrendFeed,
)

router = APIRouter(prefix="/api/radar", tags=["trend-radar"])


log = get_logger("api")


def log_config() -> None:
    """Configuration goes to the log and console, never to the browser."""
    configure_logging()
    log.info("text model: %s", settings.openrouter_model)
    log.info("image model: %s (provider=%s, licence=%s)",
             settings.image_model, settings.hf_provider, settings.image_licence)
    log.info("region: %s | text configured=%s | image configured=%s",
             settings.trend_region, settings.configured, settings.image_configured)


# Generated images are written to disk and served from here, so the
# frontend can just point an <img> at the URL and the reviewer can
# download the asset.
# In-memory stores. A real deployment would use Postgres; for a prototype
# the ephemerality is a feature — every demo starts clean.
_drafts: dict[str, Draft] = {}
_decisions: list[DecisionResponse] = []
_images: dict[str, ImageResult] = {}


@router.get("/trends", response_model=TrendFeed)
def trends(refresh: bool = False):
    # A scan is the run boundary: this closes the previous log file and
    # opens a new one, so everything that follows this scan reads as one
    # trace.
    path = start_run("manual scan" if refresh else "initial scan")
    log.info("GET /api/trends | refresh=%s | log=%s",
             refresh, path.name if path else "console only")
    try:
        return trend_service.get_feed(force=refresh)
    except Exception as e:  # noqa: BLE001
        log.exception("trend feed request failed")
        raise HTTPException(
            status_code=502,
            detail=(
                f"Trend fetch failed: {type(e).__name__}: {e}. "
                "The trends24 page structure may have changed — check the "
                "selector in trends_html.parse_latest()."
            ),
        )


@router.get("/evaluate", response_model=ScoredTrend)
def evaluate_one(name: str):
    """Score an arbitrary hashtag without it being in the live feed.
    Powers the manual test input — useful for demos and for tuning the
    scoring weights against hashtags you expect to see."""
    name = name.strip()
    if not name:
        raise HTTPException(422, "Enter a hashtag to score.")
    if not name.startswith("#"):
        name = "#" + name.lstrip("#")
    return evaluate(name)


@router.post("/generate", response_model=Draft)
def generate(req: GenerateRequest):
    log.info("POST /api/generate | hashtag=%s | force=%s",
             req.hashtag, req.force)
    trend = trend_service.find(req.hashtag)
    if trend is None:
        if not req.force:
            log.warning("hashtag not in current feed: %s", req.hashtag)
            raise HTTPException(404, f"'{req.hashtag}' is not in the current feed.")
        # Manual test: score it on the fly.
        log.info("manual test bench | scoring %s on the fly", req.hashtag)
        trend = evaluate(req.hashtag)

    if trend["band"] == "blocked":
        log.warning("BLOCKED at gate | %s | reason=%s — model never called",
                    req.hashtag, trend["blocked_reason"])
        raise HTTPException(
            403,
            f"'{req.hashtag}' is off-limits ({trend['blocked_reason']}). "
            "Blocked trends never reach the model.",
        )
    if trend["band"] == "ignore" and not req.force:
        log.info("below threshold | %s | score=%d — no draft",
                 req.hashtag, trend["score"])
        raise HTTPException(
            422,
            f"'{req.hashtag}' scored {trend['score']}/100, below the 40-point "
            "floor. Drafting it would waste reviewer time.",
        )

    try:
        post, model, latency = generate_post(
            hashtag=trend["name"],
            score=trend["score"],
            band=trend["band"],
            rationale=trend["rationale"],
            neighbours=trend_service.neighbours_of(trend["name"]),
            region=settings.trend_region,
            language_label=trend["language_label"],
            category=trend["category"],
        )
    except AgentError as e:
        log.error("draft generation failed for %s", trend["name"])
        raise HTTPException(502, str(e))

    draft = Draft(
        draft_id=uuid.uuid4().hex[:12],
        hashtag=trend["name"],
        language=trend["language"],
        language_label=trend["language_label"],
        category=trend["category"],
        score=trend["score"],
        band=trend["band"],
        action=trend["action"],
        post=post,
        generated_at=datetime.now(timezone.utc),
        latency_ms=latency,
    )
    _drafts[draft.draft_id] = draft
    log.info("draft stored | id=%s | hashtag=%s | score=%d | band=%s",
             draft.draft_id, draft.hashtag, draft.score, draft.band)
    return draft


@router.post("/image", response_model=ImageResult)
def make_image(req: ImageRequest):
    log.info("POST /api/image | draft=%s | override=%s",
             req.draft_id, bool(req.prompt_override))
    """
    Generate the visual for an existing draft.

    Deliberately a separate call from /api/generate: image generation is
    slow and costs credits, so the reviewer decides whether the copy is
    worth illustrating before spending either.
    """
    draft = _drafts.get(req.draft_id)
    if draft is None:
        raise HTTPException(404, "Unknown draft_id. Generate the post first.")

    prompt = (req.prompt_override or draft.post.image_prompt or "").strip()
    if not prompt:
        raise HTTPException(
            422,
            "This draft has no image brief. Regenerate the post, or type a "
            "brief of your own.",
        )

    try:
        out = generate_image(prompt, draft.hashtag, draft.post.post_text)
    except ImageError as e:
        log.error("image request failed for draft %s", req.draft_id)
        raise HTTPException(502, str(e))


    result = ImageResult(
        draft_id=req.draft_id,
        filename=out["filename"],
        url=out["url"],
        prompt_used=prompt,
        width=out.get("width"),
        height=out.get("height"),
        latency_ms=out["latency_ms"],
        removed_from_brief=out.get("removed_from_brief", []),
        warning=out["warning"],
        created_at=datetime.now(timezone.utc),
    )
    _images[req.draft_id] = result
    return result


@router.patch("/draft/{draft_id}", response_model=Draft)
def edit_draft(draft_id: str, edit: DraftEdit):
    """
    Save a reviewer's manual edit. This is what makes "Review or Edit"
    genuinely an edit rather than a reroll — a reviewer who wants one word
    changed should not have to spend a model call and lose everything else
    the draft got right.

    Fields left null are untouched, so post and image are independent.
    """
    draft = _drafts.get(draft_id)
    if draft is None:
        raise HTTPException(404, "Unknown draft_id.")

    log.info("PATCH /api/draft/%s | fields=%s", draft_id,
             ", ".join(k for k, v in edit.model_dump().items() if v is not None)
             or "none")
    if edit.post_text is not None:
        text = edit.post_text.strip()
        if not text:
            raise HTTPException(422, "Post text cannot be empty.")
        draft.post.post_text = text
    if edit.hashtags is not None:
        draft.post.hashtags = [
            h if h.startswith("#") else f"#{h}"
            for h in (t.strip() for t in edit.hashtags)
            if h
        ]
    if edit.image_prompt is not None:
        draft.post.image_prompt = edit.image_prompt.strip()

    draft.edited = True
    _drafts[draft_id] = draft
    log.info("draft %s edited by reviewer", draft_id)
    return draft


@router.post("/decision", response_model=DecisionResponse)
def decision(req: DecisionRequest):
    draft = _drafts.get(req.draft_id)
    if draft is None:
        raise HTTPException(404, "Unknown draft_id.")

    # Each target gets its own wording. A reviewer approving only the image
    # should not see language implying the whole post is cleared to publish.
    if req.action == "approve":
        status = "approved"
        message = {
            "post": "Post copy approved. The image is still judged separately.",
            "image": "Image approved. The post copy is still judged separately.",
            "final": (
                "Full post approved. In production this hands off to MOD02 "
                "(Persona Council) for sign-off. Nothing was published."
            ),
        }[req.target]
        if req.target == "final":
            status = "queued_simulated"
    else:
        status = "rejected"
        message = {
            "post": "Post copy rejected. Regenerate or edit it — the image is kept.",
            "image": "Image rejected. Regenerate or edit the brief — the copy is kept.",
            "final": "Draft rejected. Pick another trend, or regenerate.",
        }[req.target]

    result = DecisionResponse(
        draft_id=req.draft_id,
        action=req.action,
        target=req.target,
        status=status,
        message=message,
        decided_at=datetime.now(timezone.utc),
    )
    _decisions.append(result)
    log.info("DECISION | draft=%s | target=%s | action=%s | status=%s",
             req.draft_id, req.target, req.action, status)
    if req.target == "final" and req.action == "approve":
        log.info("run complete — full post approved (simulated, nothing published)")
    return result


@router.get("/log")
def decision_log():
    return {"decisions": [d.model_dump() for d in reversed(_decisions)]}
