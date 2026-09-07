from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid


# ── Request ────────────────────────────────────────────────────────────────────

class ReviewUpdate(BaseModel):
    """Payload for a reviewer making a decision on a review item."""
    status: str                            # approved | blocked | escalated
    decision_note: Optional[str] = None


# ── Response ──────────────────────────────────────────────────────────────────

class ReviewResponse(BaseModel):
    id                    : uuid.UUID
    tenant_id             : uuid.UUID
    run_id                : uuid.UUID
    workflow_id           : uuid.UUID
    user_id               : uuid.UUID
    status                : str
    decision              : Optional[str]
    max_risk_score        : int
    finding_count         : int
    top_finding_severity  : Optional[str]
    governing_policy_id   : Optional[uuid.UUID]
    governing_policy_name : Optional[str]
    decision_by           : Optional[uuid.UUID]
    decision_at           : Optional[datetime]
    decision_note         : Optional[str]
    created_at            : datetime
    updated_at            : datetime
    model_config = {"from_attributes": True}


class ReviewQueueStats(BaseModel):
    total          : int
    pending        : int
    in_review     : int
    approved       : int
    blocked        : int
    escalated      : int
    avg_risk_score : float
