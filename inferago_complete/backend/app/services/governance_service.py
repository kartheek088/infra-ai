"""
Governance aggregation service — Phase 10.

Responsibilities:
1. After security analysis, aggregate all findings for an execution into an
   execution-level governance decision.
2. Create a Review record (never fake — only when findings exist).
3. Update the Run record with governance fields so the ExecutionDetail page
   can display governance status without extra queries.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import Review
from app.models.run import Run
from app.models.security_finding import SecurityFinding
from app.models.audit_log import AuditLog


# Priority order: BLOCK > REQUIRE_REVIEW > ALERT > ALLOW
_GOVERNANCE_PRIORITY = {"BLOCK": 0, "REQUIRE_REVIEW": 1, "ALERT": 2, "ALLOW": 3}

# Which review status values correspond to requiring a human decision
_REQUIRES_REVIEW = {"REQUIRE_REVIEW", "BLOCK"}


async def _aggregate_findings(
    db: AsyncSession,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[Optional[str], int, int, Optional[str], Optional[uuid.UUID], Optional[str]]:
    """
    Aggregate all findings for a run into a single execution-level decision.

    Returns:
        (governance_decision, max_risk_score, finding_count,
         top_finding_severity, governing_policy_id, governing_policy_name)
    """
    result = await db.execute(
        select(SecurityFinding).where(
            SecurityFinding.run_id    == run_id,
            SecurityFinding.tenant_id == tenant_id,
        )
    )
    findings: list[SecurityFinding] = list(result.scalars().all())

    if not findings:
        return "ALLOW", 0, 0, None, None, None

    # Sort findings by risk_score desc to get the worst finding as governing
    findings.sort(key=lambda f: f.risk_score, reverse=True)
    worst = findings[0]

    # Determine execution-level governance decision
    # Priority: BLOCK > REQUIRE_REVIEW > ALERT > ALLOW
    seen_actions: dict[str, bool] = {a: False for a in _GOVERNANCE_PRIORITY}
    for f in findings:
        if f.governance_action in seen_actions:
            seen_actions[f.governance_action] = True

    # Pick highest-priority action seen
    decision = "ALLOW"
    for action in sorted(_GOVERNANCE_PRIORITY, key=lambda a: _GOVERNANCE_PRIORITY[a]):
        if seen_actions.get(action, False):
            decision = action
            break

    max_risk_score       = max(f.risk_score for f in findings)
    finding_count        = len(findings)
    top_severity         = worst.severity
    governing_policy_id  = worst.policy_id
    governing_policy_name = worst.policy_name

    return decision, max_risk_score, finding_count, top_severity, governing_policy_id, governing_policy_name


async def compute_and_persist_governance(
    db: AsyncSession,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Review | None:
    """
    Aggregate findings, persist governance to Run, and create a Review record.

    Called by run_security_analysis_background after security analysis completes.
    This function is idempotent — running it twice for the same run will
    update the existing review rather than creating a duplicate.

    Returns the created/updated Review record, or None if no review is needed.
    """
    (
        decision,
        max_risk_score,
        finding_count,
        top_severity,
        governing_policy_id,
        governing_policy_name,
    ) = await _aggregate_findings(db, run_id, tenant_id, user_id)

    # Only create a review if there's a meaningful governance signal
    if decision in _REQUIRES_REVIEW:
        # Check if a review already exists for this run
        existing = await db.execute(
            select(Review).where(Review.run_id == run_id)
        )
        review: Optional[Review] = existing.scalar_one_or_none()

        if review is None:
            review = Review(
                id                      = uuid.uuid4(),
                tenant_id               = tenant_id,
                run_id                  = run_id,
                workflow_id             = (
                    await db.execute(select(Run.workflow_id).where(Run.id == run_id))
                ).scalar_one_or_none() or uuid.UUID("00000000-0000-0000-0000-000000000000"),
                user_id                 = user_id,
                status                  = "pending",
                decision                = decision,
                max_risk_score          = max_risk_score,
                finding_count           = finding_count,
                top_finding_severity    = top_severity,
                governing_policy_id     = governing_policy_id,
                governing_policy_name   = governing_policy_name,
            )
            db.add(review)
        else:
            # Update existing review with latest governance data
            review.decision               = decision
            review.max_risk_score         = max_risk_score
            review.finding_count          = finding_count
            review.top_finding_severity   = top_severity
            review.governing_policy_id    = governing_policy_id
            review.governing_policy_name  = governing_policy_name

        # Update Run with execution-level governance fields
        run_result = await db.execute(select(Run).where(Run.id == run_id))
        run: Optional[Run] = run_result.scalar_one_or_none()
        if run:
            run.governance_decision  = decision
            run.max_risk_score      = max_risk_score
            run.review_required     = decision in _REQUIRES_REVIEW

        await db.flush()
        return review

    return None


async def make_review_decision(
    db: AsyncSession,
    review_id: uuid.UUID,
    user_id: uuid.UUID,
    new_status: str,
    decision_note: Optional[str] = None,
) -> Review:
    """
    Record a reviewer's decision on a review item.
    new_status: 'approved' | 'blocked' | 'escalated'
    """
    result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review: Review = result.scalar_one_or_none()
    if not review:
        raise ValueError(f"Review {review_id} not found")

    review.status       = new_status
    review.decision_by  = user_id
    review.decision_at = datetime.now(timezone.utc)
    if decision_note:
        review.decision_note = decision_note

    # Map status to execution-level governance decision
    status_to_decision = {
        "approved":  "ALLOWED",
        "blocked":   "BLOCKED",
        "escalated": "ESCALATED",
    }
    review.decision = status_to_decision.get(new_status, review.decision)

    # Also update the Run record
    run_result = await db.execute(select(Run).where(Run.id == review.run_id))
    run: Optional[Run] = run_result.scalar_one_or_none()
    if run:
        run.governance_decision  = review.decision
        run.review_required      = False
        run.review_status        = new_status

    # Write audit log
    db.add(AuditLog(
        id           = uuid.uuid4(),
        user_id      = review.user_id,
        tenant_id    = review.tenant_id,
        entity_type  = "review",
        entity_id    = review.id,
        action       = f"review.{new_status}",
        performed_by = user_id,
        snapshot     = {
            "run_id":           str(review.run_id),
            "workflow_id":      str(review.workflow_id),
            "previous_status":  review.status,
            "new_status":        new_status,
            "decision":         review.decision,
            "risk_score":       review.max_risk_score,
        },
        note         = decision_note,
    ))

    await db.commit()
    await db.refresh(review)
    return review
