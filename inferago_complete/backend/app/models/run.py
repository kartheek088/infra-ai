import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class Run(Base):
    __tablename__ = "runs"
    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id        = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    workflow_id      = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    n8n_execution_id = Column(String, index=True, nullable=True)
    status           = Column(String, nullable=False, default="unknown")
    triggered_by     = Column(String, nullable=True)
    platform         = Column(String, nullable=False, default="n8n")
    duration_ms      = Column(Integer, nullable=True)
    started_at       = Column(DateTime(timezone=True), nullable=True)
    finished_at      = Column(DateTime(timezone=True), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Phase 1: raw event log from platform webhooks
    events_jsonb     = Column(JSONB, nullable=True, default=None)


class TokenUsage(Base):
    __tablename__ = "token_usage"
    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id         = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    run_id            = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    node_name         = Column(String, nullable=False)
    model             = Column(String, nullable=True)
    prompt_tokens     = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens      = Column(Integer, default=0)
    cost_usd          = Column(Float, default=0.0)
    recorded_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Phase 1: richer per-node execution metadata
    node_type         = Column(String(64), nullable=True, default=None)   # llm | http_request | trigger | ...
    event_type        = Column(String(64), nullable=True, default=None)   # node_started | node_finished | ...
    provider          = Column(String(64), nullable=True, default=None)    # openai | anthropic | azure | ...
    error_message     = Column(Text, nullable=True, default=None)
    latency_ms        = Column(Integer, nullable=True, default=None)
    node_metadata     = Column('metadata', JSONB, nullable=True, default=None)
