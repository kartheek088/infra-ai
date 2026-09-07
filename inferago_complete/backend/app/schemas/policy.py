from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class PolicyCondition(BaseModel):
    """A single condition within a policy's condition tree."""
    field:    str = Field(..., description="Field to evaluate: severity, detector_id, risk_score, node_name, provider")
    operator: str = Field(..., description="Operator: equals | not_equals | in | not_in | gt | lt | gte | lte | contains")
    value:    Optional[object] = None  # flexible — str, int, list, etc.


class PolicyConditionTree(BaseModel):
    """
    JSON condition tree for a policy.
    Supports 'all' (AND) and 'any' (OR) combinations.
    """
    all: Optional[list[PolicyCondition]] = None
    any: Optional[list[PolicyCondition]] = None


class PolicyCreate(BaseModel):
    name:                    str
    description:             Optional[str] = None
    enabled:                 bool = True
    applies_to_all_workflows: bool = True
    workflow_ids:            Optional[list[str]] = None
    conditions:              PolicyConditionTree
    action:                  str = Field(..., pattern="^(ALLOW|ALERT|REQUIRE_REVIEW|BLOCK)$")
    priority:                int = 0
    notify_on_trigger:        bool = False
    notification_channels:   Optional[list[str]] = None


class PolicyUpdate(BaseModel):
    name:                    Optional[str] = None
    description:             Optional[str] = None
    enabled:                 Optional[bool] = None
    applies_to_all_workflows: Optional[bool] = None
    workflow_ids:            Optional[list[str]] = None
    conditions:              Optional[PolicyConditionTree] = None
    action:                  Optional[str] = Field(None, pattern="^(ALLOW|ALERT|REQUIRE_REVIEW|BLOCK)$")
    priority:                Optional[int] = None
    notify_on_trigger:        Optional[bool] = None
    notification_channels:    Optional[list[str]] = None


class PolicyResponse(BaseModel):
    id:                       uuid.UUID
    user_id:                  uuid.UUID
    name:                     str
    description:              Optional[str]
    enabled:                  bool
    applies_to_all_workflows:  bool
    workflow_ids:             Optional[list[str]]
    conditions:               PolicyConditionTree
    action:                   str
    priority:                 int
    notify_on_trigger:         bool
    notification_channels:    Optional[list[str]]
    created_at:                datetime
    updated_at:                datetime
    model_config = {"from_attributes": True}
