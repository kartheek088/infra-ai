from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class RAGMetricsCreate(BaseModel):
    workflow_id: str
    chunks_retrieved: int = Field(ge=0)
    chunks_used: int = Field(ge=0)
    context_fill_pct: float = Field(ge=0.0, le=100.0)
    avg_relevance_score: float = Field(ge=0.0, le=1.0)
    embedding_tokens: int = 0
    has_duplicates: bool = False

class RAGMetricsResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    workflow_id: uuid.UUID
    chunks_retrieved: int
    chunks_used: int
    context_fill_pct: float
    avg_relevance_score: float
    embedding_tokens: int
    has_duplicates: bool
    recorded_at: datetime
    model_config = {"from_attributes": True}

class RAGSummaryResponse(BaseModel):
    workflow_id: str
    avg_chunks_retrieved: float
    avg_chunks_used: float
    avg_context_fill_pct: float
    avg_relevance_score: float
    efficiency_ratio: float
    duplicate_rate: float
    total_runs_analyzed: int
