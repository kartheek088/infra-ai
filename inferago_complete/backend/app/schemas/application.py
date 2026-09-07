from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ApplicationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    environment: str = Field(default="production", max_length=50)


class ApplicationCreate(ApplicationBase):
    tenant_id: UUID


class ApplicationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    environment: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class Application(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ApplicationWithStats(Application):
    workflow_count: int = 0
