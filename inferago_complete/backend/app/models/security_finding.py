"""
Security Finding model — Phase 2: Security Detection.
Each finding represents one deterministic security signal detected in an execution.
"""
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class SecurityFinding(Base):
    __tablename__ = "security_findings"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id         = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    run_id            = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id       = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Detection
    detector_id       = Column(String(64), nullable=False)   # e.g. "pii_exposure", "api_key_leak"
    detector_name     = Column(String(128), nullable=False)  # human-readable name
    severity          = Column(String(16), nullable=False)   # critical | high | medium | low | info
    confidence        = Column(Float, nullable=False, default=1.0)  # 0.0–1.0

    # Evidence
    title             = Column(String(256), nullable=False)
    description       = Column(Text, nullable=True)
    finding_data      = Column(JSONB, nullable=True, default=None)  # detector-specific evidence

    # Risk scoring (computed at detection time)
    risk_score        = Column(Integer, nullable=False, default=0)   # 0–100
    risk_factors      = Column(JSONB, nullable=True, default=None)  # [{factor, weight, contribution}]

    # Policy evaluation result
    governance_action = Column(String(32), nullable=True)   # ALLOW | ALERT | REQUIRE_REVIEW | BLOCK
    policy_id         = Column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="SET NULL"), nullable=True)
    policy_name       = Column(String(256), nullable=True)

    # Review state
    reviewed          = Column(String(16), nullable=False, default="pending")  # pending | approved | false_positive | escalated
    reviewed_by       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at       = Column(DateTime(timezone=True), nullable=True)
    review_note       = Column(Text, nullable=True)

    # Metadata
    node_name         = Column(String(256), nullable=True)
    provider          = Column(String(64), nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_security_findings_severity",      "severity"),
        Index("ix_security_findings_risk_score",   "risk_score"),
        Index("ix_security_findings_reviewed",      "reviewed"),
        Index("ix_security_findings_detector_id",   "detector_id"),
        # Composite for dashboard queries
        Index("ix_security_findings_user_created",  "user_id", "created_at"),
    )
