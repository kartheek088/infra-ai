"""
Review queue router — Phase 10.

Provides:
- GET  /api/reviews              — paginated review queue list
- GET  /api/reviews/stats        — aggregate counts by status
- GET  /api/reviews/{id}         — single review
- PATCH /api/reviews/{id}        — reviewer makes a decision (approve/block/escalate)
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import current_active_user
from app.models.review import Review
from app.models.user import User
from app.schemas.review import (
    ReviewUpdate,
    ReviewResponse,
    ReviewQueueStats,
)

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewResponse])
async def list_reviews(
    status:       Optional[str]  = Query(None, description="pending|in_review|approved|blocked|escalated|completed"),
    workflow_id:  Optional[uuid.UUID] = Query(None),
    min_risk:     Optional[int] = Query(None, ge=0, le=100),
    limit:        int  = Query(50,  ge=1, le=200),
    offset:       int  = Query(0,   ge=0),
    db: AsyncSession = Depends(get_db),
    user: User       = Depends(current_active_user),
):
    """List reviews the current user can act on.

    By default returns all statuses. Filter by status to narrow the queue.
    """
    q = select(Review).where(Review.user_id == user.id)

    if status:
        q = q.where(Review.status == status)
    if workflow_id:
        q = q.where(Review.workflow_id == workflow_id)
    if min_risk is not None:
        q = q.where(Review.max_risk_score >= min_risk)

    q = q.order_by(
        # Worst risk first, then oldest pending first
        Review.max_risk_score.desc(),
        Review.created_at.asc(),
    )
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats", response_model=ReviewQueueStats)
async def review_queue_stats(
    db: AsyncSession = Depends(get_db),
    user: User       = Depends(current_active_user),
):
    """Aggregate counts for the review queue dashboard."""
    result = await db.execute(
        select(Review).where(Review.user_id == user.id)
    )
    rows: list[Review] = list(result.scalars().all())

    by_status: dict[str, int] = {}
    total_risk = 0
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        total_risk += r.max_risk_score

    total = len(rows)
    return ReviewQueueStats(
        total          = total,
        pending        = by_status.get("pending",      0),
        in_review      = by_status.get("in_review",    0),
        approved       = by_status.get("approved",      0),
        blocked        = by_status.get("blocked",       0),
        escalated      = by_status.get("escalated",    0),
        avg_risk_score = round(total_risk / total, 1) if total else 0.0,
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User       = Depends(current_active_user),
):
    """Fetch a single review record."""
    result = await db.execute(
        select(Review).where(
            Review.id      == review_id,
            Review.user_id == user.id,
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.patch("/{review_id}", response_model=ReviewResponse)
async def decide_review(
    review_id:  uuid.UUID,
    payload:    ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    user: User       = Depends(current_active_user),
):
    """
    Record a reviewer's decision on a review item.

    Valid transitions:
    - pending / in_review → approved  (allow the execution)
    - pending / in_review → blocked   (halt or quarantine)
    - pending / in_review → escalated (pass to a senior reviewer)
    """
    VALID_TRANSITIONS = {
        "approved":  {"pending", "in_review"},
        "blocked":   {"pending", "in_review"},
        "escalated": {"pending", "in_review"},
    }
    if payload.status not in VALID_TRANSITIONS:
        raise HTTPException(status_code=400, detail=f"Invalid status: {payload.status}")

    result = await db.execute(
        select(Review).where(
            Review.id      == review_id,
            Review.user_id == user.id,
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.status not in VALID_TRANSITIONS.get(payload.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition from '{review.status}' to '{payload.status}'",
        )

    from app.services.governance_service import make_review_decision
    return await make_review_decision(
        db             = db,
        review_id      = review.id,
        user_id        = user.id,
        new_status     = payload.status,
        decision_note  = payload.decision_note,
    )
