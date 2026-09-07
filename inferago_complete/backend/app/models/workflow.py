import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Workflow(Base):
    __tablename__ = "workflows"
    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id        = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id   = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=True, index=True)
    name             = Column(String, nullable=False)
    description      = Column(String, nullable=True)
    n8n_workflow_id  = Column(String, unique=True, index=True, nullable=False)
    config           = Column(JSON, default={})
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    # Risk classification
    risk_level       = Column(String(32), nullable=True, default=None, index=True)   # low | medium | high | critical
