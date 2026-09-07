"""
Policy model — Phase 3: Governance.

Policies define rules that map security findings to governance actions.
"""
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class Policy(Base):
    __tablename__ = "policies"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id         = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Identity
    name              = Column(String(256), nullable=False)
    description       = Column(Text, nullable=True)
    enabled           = Column(Boolean, nullable=False, default=True)

    # Policy scope
    applies_to_all_workflows = Column(Boolean, nullable=False, default=True)
    # If not applies_to_all, restrict to specific workflow IDs
    workflow_ids      = Column(JSONB, nullable=True, default=None)  # list of UUID strings

    # Trigger conditions (JSON condition tree)
    conditions        = Column(JSONB, nullable=False, default=dict)
    # Example structure:
    # {
    #   "all": [
    #     {"field": "severity", "operator": "in", "value": ["critical", "high"]},
    #     {"field": "detector_id", "operator": "equals", "value": "api_secret_leak"},
    #   ]
    # }

    # Governance action when conditions match
    action            = Column(String(32), nullable=False)  # ALLOW | ALERT | REQUIRE_REVIEW | BLOCK

    # Priority (higher = evaluated first)
    priority          = Column(Integer, nullable=False, default=0)

    # Notification settings
    notify_on_trigger = Column(Boolean, nullable=False, default=False)
    notification_channels = Column(JSONB, nullable=True, default=None)  # ["email", "slack"]

    # Audit
    created_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at        = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_policies_user_enabled",  "user_id", "enabled"),
        Index("ix_policies_priority",      "priority"),
    )
