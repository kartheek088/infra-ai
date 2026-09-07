"""
Universal event model — stores raw structured events from any platform.
Platform adapters emit these; the security engine consumes them.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EventType(str, Enum):
    # Lifecycle
    EXECUTION_STARTED   = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED    = "execution.failed"
    EXECUTION_BLOCKED   = "execution.blocked"

    # Node-level
    NODE_STARTED        = "node.started"
    NODE_COMPLETED      = "node.completed"
    NODE_FAILED         = "node.failed"

    # AI / LLM
    LLM_PROMPT          = "llm.prompt"
    LLM_COMPLETION      = "llm.completion"
    LLM_ERROR           = "llm.error"

    # RAG
    RAG_RETRIEVE        = "rag.retrieve"
    RAG_QUERY           = "rag.query"

    # Tool
    TOOL_CALL           = "tool.call"
    TOOL_RESULT         = "tool.result"

    # Security
    SECURITY_FINDING    = "security.finding"

    # Governance
    POLICY_EVALUATED    = "policy.evaluated"
    BLOCK_APPLIED       = "block.applied"

    # Generic
    INFO                = "info"
    WARNING             = "warning"
    ERROR               = "error"


class Component(str, Enum):
    PLATFORM_ADAPTER  = "platform_adapter"  # n8n, make, zapier, custom
    SECURITY_ENGINE   = "security_engine"
    POLICY_ENGINE     = "policy_engine"
    TELEMETRY         = "telemetry"
    API               = "api"
    WEBHOOK           = "webhook"


class Event(Base):
    """
    Universal event log — one row per structured event emitted during a workflow execution.

    event_type: dot-notation string from EventType enum
    component:  which ARI subsystem emitted this
    operation:  what happened (create, update, delete, call, receive, etc.)
    actor:      human user id or "system"
    session_id: groups events from one execution or user session
    payload:    flexible JSON blob — schema varies by event_type
    """
    __tablename__ = "events"

    id          = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id   = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id     = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    workflow_id = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=True, index=True)
    run_id      = mapped_column(PG_UUID(as_uuid=True), ForeignKey("runs.id"), nullable=True, index=True)

    event_type  = mapped_column(String, nullable=False, index=True)
    component   = mapped_column(String, nullable=False)  # EventType / Component enum values as strings
    operation   = mapped_column(String, nullable=False)

    # Who / what
    actor       = mapped_column(String, nullable=True)  # user id, "system", or service name
    session_id  = mapped_column(String, nullable=True, index=True)  # execution id or login session

    # Temporal
    occurred_at = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Structured payload — schema varies per event_type
    payload = mapped_column(JSON, nullable=True)

    # Severity for filtering (used for security/warning/error events)
    severity   = mapped_column(String, nullable=True)  # critical | high | medium | low | info

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
