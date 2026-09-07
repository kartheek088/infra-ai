"""
Review model — Phase 10: Review Queue.

Execution-level governance review record. Created automatically when
run_security_analysis_background produces a REQUIRE_REVIEW or BLOCK
finding (or when max risk_score ≥ policy threshold).

Never created with fake/placeholder data — only when the system actually
generates a governance review signal.
"""
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"

    # Identity
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id    = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    run_id       = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id  = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Execution context
    status       = Column(String(16), nullable=False, default="pending")   # pending | in_review | approved | blocked | escalated | completed
    decision     = Column(String(16), nullable=True)                       # ALLOW | ALERT | REQUIRE_REVIEW | BLOCK | APPROVED | BLOCKED

    # Governance snapshot (captured at time of review creation)
    max_risk_score   = Column(Integer, nullable=False, default=0)
    finding_count    = Column(Integer, nullable=False, default=0)
    top_finding_severity = Column(String(16), nullable=True)             # critical | high | medium | low | info
    governing_policy_id   = Column(UUID(as_uuid=True), nullable=True)
    governing_policy_name = Column(String(256), nullable=True)

    # Review decision
    decision_by      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision_at      = Column(DateTime(timezone=True), nullable=True)
    decision_note    = Column(Text, nullable=True)

    # Timestamps
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_reviews_status",         "status"),
        Index("ix_reviews_user_created",   "user_id", "created_at"),
        Index("ix_reviews_workflow_created", "workflow_id", "created_at"),
        Index("ix_reviews_tenant_created", "tenant_id", "created_at"),
    )
