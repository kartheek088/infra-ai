"""
Security findings router — Phase 2 & 3.
"""
from typing import Optional
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import current_active_user
from app.models.security_finding import SecurityFinding
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.security_finding import (
    SecurityFindingUpdate,
    SecurityFindingResponse,
    FindingStats,
)

router = APIRouter(prefix="/api/security-findings", tags=["security-findings"])


@router.get("", response_model=list[SecurityFindingResponse])
async def list_findings(
    workflow_id:    Optional[uuid.UUID] = Query(None),
    run_id:         Optional[uuid.UUID] = Query(None),
    severity:       Optional[str]        = Query(None),
    reviewed:       Optional[str]        = Query(None),
    detector_id:    Optional[str]        = Query(None),
    min_risk_score: Optional[int]        = Query(None, ge=0, le=100),
    limit:          int = Query(50, ge=1, le=200),
    offset:         int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """List security findings for the current user."""
    q = select(SecurityFinding).where(SecurityFinding.user_id == user.id)

    if workflow_id:    q = q.where(SecurityFinding.workflow_id == workflow_id)
    if run_id:         q = q.where(SecurityFinding.run_id == run_id)
    if severity:       q = q.where(SecurityFinding.severity == severity)
    if reviewed:       q = q.where(SecurityFinding.reviewed == reviewed)
    if detector_id:    q = q.where(SecurityFinding.detector_id == detector_id)
    if min_risk_score: q = q.where(SecurityFinding.risk_score >= min_risk_score)

    q = q.order_by(SecurityFinding.risk_score.desc(), SecurityFinding.created_at.desc())
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats", response_model=FindingStats)
async def get_finding_stats(
    workflow_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Get aggregate statistics over security findings."""
    base_q = select(SecurityFinding).where(SecurityFinding.user_id == user.id)
    if workflow_id:
        base_q = base_q.where(SecurityFinding.workflow_id == workflow_id)

    result = await db.execute(base_q)
    rows = result.scalars().all()

    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    total_risk = 0
    critical_count = 0

    for r in rows:
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        by_status[r.reviewed]   = by_status.get(r.reviewed, 0) + 1
        total_risk += r.risk_score
        if r.severity == "critical":
            critical_count += 1

    total = len(rows)
    return FindingStats(
        total=total,
        by_severity=by_severity,
        by_status=by_status,
        avg_risk_score=round(total_risk / total, 1) if total else 0.0,
        critical_count=critical_count,
    )


@router.get("/{finding_id}", response_model=SecurityFindingResponse)
async def get_finding(
    finding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Get a single finding by ID."""
    result = await db.execute(
        select(SecurityFinding).where(
            SecurityFinding.id == finding_id,
            SecurityFinding.user_id == user.id,
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.patch("/{finding_id}", response_model=SecurityFindingResponse)
async def update_finding(
    finding_id: uuid.UUID,
    payload: SecurityFindingUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Update a finding's review status."""
    result = await db.execute(
        select(SecurityFinding).where(
            SecurityFinding.id == finding_id,
            SecurityFinding.user_id == user.id,
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "reviewed" in update_data:
        finding.reviewed    = update_data["reviewed"]
        finding.reviewed_by = user.id
        finding.reviewed_at = datetime.now(timezone.utc)

    if "review_note" in update_data:
        finding.review_note = update_data["review_note"]

    # Audit log
    db.add(AuditLog(
        id=uuid.uuid4(),
        user_id=user.id,
        entity_type="security_finding",
        entity_id=finding.id,
        action=f"security_finding.{update_data.get('reviewed', 'updated')}",
        performed_by=user.id,
        snapshot={
            "reviewed": finding.reviewed,
            "review_note": finding.review_note,
        },
        note=update_data.get("review_note"),
    ))

    await db.commit()
    await db.refresh(finding)
    return finding
