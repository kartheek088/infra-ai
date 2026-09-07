from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class RunCreate(BaseModel):
    workflow_id: str
    n8n_execution_id: Optional[str] = None
    status: str = "unknown"
    triggered_by: Optional[str] = None
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class RunResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    n8n_execution_id: Optional[str]
    status: str
    triggered_by: Optional[str]
    platform: str
    duration_ms: Optional[int]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}


class TokenUsageCreate(BaseModel):
    node_name: str
    model: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class TokenUsageResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    node_name: str
    model: Optional[str]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    recorded_at: datetime
    # Phase 1 extended fields
    node_type: Optional[str] = None
    event_type: Optional[str] = None
    provider: Optional[str] = None
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None
    node_metadata: Optional[dict] = None
    model_config = {"from_attributes": True}


class TokenSummaryResponse(BaseModel):
    run_id: str
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost_usd: float
    by_node: list[TokenUsageResponse]
