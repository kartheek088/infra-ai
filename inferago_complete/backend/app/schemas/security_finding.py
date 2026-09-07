from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class SecurityFindingCreate(BaseModel):
    run_id: str
    workflow_id: str
    detector_id: str
    detector_name: str
    severity: str
    confidence: float = 1.0
    title: str
    description: Optional[str] = None
    finding_data: Optional[dict] = None
    risk_score: int = 0
    risk_factors: Optional[list] = None
    governance_action: Optional[str] = None
    policy_id: Optional[str] = None
    policy_name: Optional[str] = None
    node_name: Optional[str] = None
    provider: Optional[str] = None


class SecurityFindingResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    workflow_id: uuid.UUID
    user_id: uuid.UUID
    detector_id: str
    detector_name: str
    severity: str
    confidence: float
    title: str
    description: Optional[str]
    finding_data: Optional[dict]
    risk_score: int
    risk_factors: Optional[list]
    governance_action: Optional[str]
    policy_id: Optional[uuid.UUID]
    policy_name: Optional[str]
    reviewed: str
    reviewed_by: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    review_note: Optional[str]
    node_name: Optional[str]
    provider: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class SecurityFindingUpdate(BaseModel):
    reviewed: Optional[str] = None
    review_note: Optional[str] = None


class FindingStats(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    avg_risk_score: float
    critical_count: int
