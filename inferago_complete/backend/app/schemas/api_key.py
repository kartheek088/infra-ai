from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class ApiKeyCreate(BaseModel):
    name: str

class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key: str
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}

class ApiKeyListResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_preview: str
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}
