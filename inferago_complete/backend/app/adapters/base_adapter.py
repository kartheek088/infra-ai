from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


@dataclass
class NodeExecution:
    """Per-node execution record — tokens + rich timing/error metadata."""
    node_name: str
    node_type: str          # llm | http_request | trigger | transform | logic | data | other
    model: str              # openai/gpt-4o | anthropic/claude-3 | azure | google | custom
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    # Phase 1 extensions
    event_type: str = "node_finished"   # node_started | node_finished | execution_failed | ...
    provider: str = ""                  # openai | anthropic | azure | google | custom
    error_message: str = ""
    latency_ms: Optional[int] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ExecutionEvent:
    """Raw event from platform webhook — captures lifecycle events at execution level."""
    event_type: str                        # execution_triggered | execution_finished | execution_failed | ...
    timestamp: Optional[datetime] = None
    node_name: Optional[str] = None
    source: Optional[str] = None          # trigger | webhook | manual | schedule | ...
    message: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class StandardExecution:
    """Platform-agnostic execution representation."""
    platform: str
    execution_id: Optional[str]
    workflow_id: str
    status: str
    triggered_by: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_ms: Optional[int]
    nodes: list[NodeExecution] = field(default_factory=list)
    # Phase 1: raw event log
    events: list[ExecutionEvent] = field(default_factory=list)
