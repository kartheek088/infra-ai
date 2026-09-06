from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class AlertCreate(BaseModel):
    workflow_id: str
    alert_type: str
    threshold_value: float
    slack_webhook_url: Optional[str] = None

class AlertUpdate(BaseModel):
    threshold_value: Optional[float] = None
    slack_webhook_url: Optional[str] = None
    is_active: Optional[bool] = None

class AlertResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    alert_type: str
    threshold_value: float
    is_active: bool
    slack_webhook_url: Optional[str]
    last_triggered_at: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}
