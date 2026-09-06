from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class NodeExecution:
    node_name: str
    node_type: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float

@dataclass
class StandardExecution:
    platform: str
    execution_id: Optional[str]
    workflow_id: str
    status: str
    triggered_by: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_ms: Optional[int]
    nodes: list[NodeExecution] = field(default_factory=list)
