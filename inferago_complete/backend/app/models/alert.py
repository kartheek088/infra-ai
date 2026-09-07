import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Alert(Base):
    """
    Alert types supported:
      cost_threshold  → fires when a single run cost exceeds threshold_value (USD)
      token_spike     → fires when tokens are threshold_value times above average (e.g. 2.5)
      error_rate      → fires when error % exceeds threshold_value (0.0-1.0)
      inactivity      → fires when workflow silent for threshold_value hours
      daily_budget    → fires when total daily spend exceeds threshold_value (USD)
      monthly_budget  → fires when total monthly spend exceeds threshold_value (USD)
      latency_spike   → fires when run duration exceeds threshold_value milliseconds
    """
    __tablename__ = "alerts"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id         = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    workflow_id       = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_type        = Column(String, nullable=False)  # see docstring above
    threshold_value   = Column(Float, nullable=False)
    is_active         = Column(Boolean, default=True)
    slack_webhook_url = Column(String, nullable=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
