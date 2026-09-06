from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    n8n_workflow_id: str

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class WorkflowResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    n8n_workflow_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
