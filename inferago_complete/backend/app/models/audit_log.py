"""
Audit Log model — Phase 3: Governance.

Every governance decision and review action is recorded here.
"""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id    = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # What type of entity was acted upon
    entity_type  = Column(String(32), nullable=False)   # security_finding | policy | run | workflow | execution
    entity_id    = Column(UUID(as_uuid=True), nullable=False, index=True)

    # The action taken
    action       = Column(String(64), nullable=False)
    # Examples:
    #   security_finding.created | security_finding.reviewed | security_finding.escalated
    #   policy.created | policy.updated | policy.deleted | policy.toggled
    #   execution.blocked | execution.flagged | execution.allowed

    # Actor
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Snapshot of relevant entity state at action time
    snapshot     = Column(JSONB, nullable=True, default=None)

    # Free-text note
    note         = Column(Text, nullable=True)

    # Metadata
    ip_address   = Column(String(45), nullable=True)  # supports IPv6
    user_agent   = Column(String(512), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_audit_logs_tenant_created",  "tenant_id", "created_at"),
        Index("ix_audit_logs_user_created",    "user_id", "created_at"),
        Index("ix_audit_logs_entity_type_id",  "entity_type", "entity_id"),
        Index("ix_audit_logs_action",          "action"),
    )
