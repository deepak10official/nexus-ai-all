"""FastAPI router for the Social Calendar (MOD05).

In-memory store for scheduled posts and approval queue.  Follows the
same pattern as MOD03's ``_drafts`` dict — nothing is persisted to disk.

Endpoints
---------
GET   /api/calendar/posts            → scheduled posts (optionally filtered by week)
POST  /api/calendar/schedule         → schedule a post on a date/time
PATCH /api/calendar/posts/{post_id}  → update scheduling details
POST  /api/calendar/publish/{post_id}→ mark a post as "live"
DELETE/api/calendar/posts/{post_id}  → remove a post from the schedule
GET   /api/calendar/queue            → posts awaiting scheduling
POST  /api/calendar/queue            → add a post to the approval queue
POST  /api/calendar/queue/{item_id}/approve → approve a queued item
POST  /api/calendar/queue/{item_id}/reject  → reject a queued item
"""

from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/calendar", tags=["social-calendar"])

# ── In-memory stores ──────────────────────────────────────────────────────────

# Scheduled posts keyed by post_id.
_posts: dict[str, dict] = {}

# Approval queue — posts that arrived from MOD02 but have not been scheduled.
_queue: dict[str, dict] = {}


# ── Request / response models ─────────────────────────────────────────────────

class ScheduleBody(BaseModel):
    """Schedule a new post on the calendar."""
    text: str
    platform: str = Field(
        description="linkedin | twitter | instagram | reels",
    )
    scheduled_date: str = Field(description="ISO date YYYY-MM-DD")
    scheduled_time: str = Field(default="09:00", description="HH:MM (24-hour)")
    image_url: Optional[str] = None
    source_mod: Optional[str] = Field(
        default=None,
        description="Which module produced the post, e.g. MOD02, MOD03",
    )
    source_label: Optional[str] = Field(
        default=None,
        description="Human label, e.g. 'AMPLIFY', 'CO-CREATE', 'TRENDING'",
    )
    hashtags: Optional[List[str]] = None
    draft_id: Optional[str] = None


class UpdateBody(BaseModel):
    """Partial update to a scheduled post."""
    text: Optional[str] = None
    platform: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None


class QueueBody(BaseModel):
    """Add a post to the approval queue (typically from a MOD02 handoff)."""
    text: str
    platform: str = "linkedin"
    image_url: Optional[str] = None
    source_mod: Optional[str] = None
    source_label: Optional[str] = None
    hashtags: Optional[List[str]] = None
    draft_id: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _week_bounds(iso_date: str) -> tuple[date, date]:
    """Return (monday, sunday) for the ISO week containing *iso_date*."""
    d = date.fromisoformat(iso_date)
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


PLATFORM_LABELS = {
    "linkedin": "LinkedIn",
    "twitter": "Twitter/X",
    "instagram": "Instagram",
    "reels": "Instagram Reels",
}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/posts")
def list_posts(week: Optional[str] = None):
    """Return scheduled posts, optionally filtered to a single ISO week.

    ``week`` should be any ISO date (YYYY-MM-DD); the response will include
    every post whose ``scheduled_date`` falls in the Mon–Sun week containing
    that date.
    """
    posts = list(_posts.values())
    if week:
        try:
            mon, sun = _week_bounds(week)
        except ValueError:
            raise HTTPException(400, "Invalid week parameter — use YYYY-MM-DD.")
        posts = [
            p for p in posts
            if mon <= date.fromisoformat(p["scheduled_date"]) <= sun
        ]
    # Sort by date then time.
    posts.sort(key=lambda p: (p["scheduled_date"], p["scheduled_time"]))
    return {"posts": posts, "total": len(posts)}


@router.post("/schedule")
def schedule_post(body: ScheduleBody):
    """Place a new post on the calendar."""
    post_id = uuid.uuid4().hex[:12]
    now = datetime.utcnow().isoformat()
    post = {
        "id": post_id,
        "text": body.text,
        "platform": body.platform,
        "platform_label": PLATFORM_LABELS.get(body.platform, body.platform),
        "scheduled_date": body.scheduled_date,
        "scheduled_time": body.scheduled_time,
        "image_url": body.image_url,
        "source_mod": body.source_mod or "MOD02",
        "source_label": body.source_label or "APPROVED",
        "hashtags": body.hashtags or [],
        "draft_id": body.draft_id,
        "status": "scheduled",           # scheduled | live
        "created_at": now,
        "published_at": None,
    }
    _posts[post_id] = post
    return post


@router.patch("/posts/{post_id}")
def update_post(post_id: str, body: UpdateBody):
    """Update scheduling details for a post."""
    post = _posts.get(post_id)
    if not post:
        raise HTTPException(404, "Post not found.")
    for field, value in body.dict(exclude_unset=True).items():
        if value is not None:
            post[field] = value
    if body.platform and body.platform in PLATFORM_LABELS:
        post["platform_label"] = PLATFORM_LABELS[body.platform]
    return post


@router.post("/publish/{post_id}")
def publish_post(post_id: str):
    """Mark a scheduled post as 'live' (simulated)."""
    post = _posts.get(post_id)
    if not post:
        raise HTTPException(404, "Post not found.")
    if post["status"] == "live":
        raise HTTPException(409, "Post is already live.")
    post["status"] = "live"
    post["published_at"] = datetime.utcnow().isoformat()
    return post


@router.delete("/posts/{post_id}")
def delete_post(post_id: str):
    """Remove a post from the schedule."""
    if post_id not in _posts:
        raise HTTPException(404, "Post not found.")
    del _posts[post_id]
    return {"ok": True, "deleted": post_id}


# ── Approval Queue ────────────────────────────────────────────────────────────

@router.get("/queue")
def get_queue():
    """Return posts awaiting scheduling / approval."""
    items = sorted(
        _queue.values(),
        key=lambda q: q["created_at"],
        reverse=True,
    )
    return {"queue": items, "total": len(items)}


@router.post("/queue")
def add_to_queue(body: QueueBody):
    """Add a post to the approval queue (typically from MOD02 handoff)."""
    item_id = uuid.uuid4().hex[:12]
    now = datetime.utcnow().isoformat()
    item = {
        "id": item_id,
        "text": body.text,
        "platform": body.platform,
        "platform_label": PLATFORM_LABELS.get(body.platform, body.platform),
        "image_url": body.image_url,
        "source_mod": body.source_mod or "MOD02",
        "source_label": body.source_label or "PENDING APPROVAL",
        "hashtags": body.hashtags or [],
        "draft_id": body.draft_id,
        "status": "pending",             # pending | approved | rejected
        "created_at": now,
    }
    _queue[item_id] = item
    return item


@router.post("/queue/{item_id}/approve")
def approve_queue_item(item_id: str):
    """Approve a queued post so it can be scheduled."""
    item = _queue.get(item_id)
    if not item:
        raise HTTPException(404, "Queue item not found.")
    item["status"] = "approved"
    return item


@router.post("/queue/{item_id}/reject")
def reject_queue_item(item_id: str):
    """Reject a queued post."""
    item = _queue.get(item_id)
    if not item:
        raise HTTPException(404, "Queue item not found.")
    item["status"] = "rejected"
    # Remove from queue after rejecting.
    del _queue[item_id]
    return {"ok": True, "rejected": item_id}
