"""
Security detection engine — Phase 2.

Orchestrates all detectors, computes risk scores, and persists findings.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base_adapter import StandardExecution, NodeExecution
from app.core.security import (
    ALL_DETECTORS,
    SecurityFindingResult,
    _severity_to_score,
)
from app.models.security_finding import SecurityFinding
from app.models.run import Run
from app.models.workflow import Workflow
from app.schemas.security_finding import SecurityFindingCreate

logger = logging.getLogger(__name__)


class RiskScorer:
    """
    Computes risk scores from finding factors.
    Returns 0–100 integer score.
    """

    BASE_SCORES = {
        "critical": 100,
        "high":      75,
        "medium":    50,
        "low":       25,
        "info":      10,
    }

    @classmethod
    def compute(cls, finding: SecurityFindingResult) -> int:
        base = cls.BASE_SCORES.get(finding.severity, 0)

        # Sum weighted contributions from risk factors
        factor_score = 0.0
        for rf in (finding.risk_factors or []):
            weight    = rf.get("weight", 1.0)
            contrib   = rf.get("contribution", 0)
            factor_score += weight * contrib

        # Clamp total to 0–100
        total = min(100, max(0, int(base + factor_score)))
        return total


class SecurityEngine:
    """
    Entry point for running security detection on an execution.

    Usage:
        engine = SecurityEngine(db_session)
        findings = await engine.analyze_execution(standard_execution, nodes)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── public API ───────────────────────────────────────────────────────────────

    async def analyze_execution(
        self,
        execution: StandardExecution,
        nodes: list[NodeExecution],
        run_id: uuid.UUID,
        workflow_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[SecurityFinding]:
        """
        Run all detectors against the execution, compute risk scores,
        persist findings, and return the persisted SecurityFinding rows.
        """
        raw_findings = self._run_detectors(execution, nodes)

        if not raw_findings:
            return []

        persisted = []
        for raw in raw_findings:
            risk_score = RiskScorer.compute(raw)

            # Build persistence record
            create = SecurityFindingCreate(
                run_id=str(run_id),
                workflow_id=str(workflow_id),
                detector_id=raw.detector_id,
                detector_name=raw.detector_name,
                severity=raw.severity,
                confidence=raw.confidence,
                title=raw.title,
                description=raw.description,
                finding_data=raw.finding_data,
                risk_score=risk_score,
                risk_factors=raw.risk_factors,
                node_name=raw.node_name,
                provider=raw.provider,
            )

            db_finding = SecurityFinding(
                id=uuid.uuid4(),
                run_id=run_id,
                workflow_id=workflow_id,
                user_id=user_id,
                detector_id=create.detector_id,
                detector_name=create.detector_name,
                severity=create.severity,
                confidence=create.confidence,
                title=create.title,
                description=create.description,
                finding_data=create.finding_data,
                risk_score=create.risk_score,
                risk_factors=create.risk_factors,
                reviewed="pending",
                node_name=create.node_name,
                provider=create.provider,
            )

            self.db.add(db_finding)
            persisted.append(db_finding)

        await self.db.commit()
        logger.info(f"SecurityEngine: persisted {len(persisted)} findings for run {run_id}")

        return persisted

    # ── internal ────────────────────────────────────────────────────────────────

    def _run_detectors(
        self,
        execution: StandardExecution,
        nodes: list[NodeExecution],
    ) -> list[SecurityFindingResult]:
        all_results: list[SecurityFindingResult] = []
        for detector_cls in ALL_DETECTORS:
            try:
                findings = detector_cls.detect(execution, nodes)
                all_results.extend(findings)
            except Exception as exc:
                logger.warning(
                    f"Detector {detector_cls.__name__} raised {exc}; skipping"
                )
        return all_results


async def get_finding_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
    workflow_id: Optional[uuid.UUID] = None,
) -> dict:
    """
    Aggregate statistics over security_findings for a user (optionally filtered).
    """
    from app.schemas.security_finding import FindingStats

    base_q = select(SecurityFinding).where(SecurityFinding.user_id == user_id)
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
    avg_risk = total_risk / total if total else 0.0

    return FindingStats(
        total=total,
        by_severity=by_severity,
        by_status=by_status,
        avg_risk_score=round(avg_risk, 1),
        critical_count=critical_count,
    ).model_dump()
