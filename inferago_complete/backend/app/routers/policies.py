"""
Policy CRUD router — Phase 3: Governance.
"""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import current_active_user
from app.models.policy import Policy
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.policy import PolicyCreate, PolicyUpdate, PolicyResponse

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    enabled: Optional[bool] = Query(None),
    limit:   int = Query(50, ge=1, le=200),
    offset:  int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """List all policies for the current user."""
    q = select(Policy).where(Policy.user_id == user.id)
    if enabled is not None:
        q = q.where(Policy.enabled == enabled)
    q = q.order_by(Policy.priority.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Get a single policy by ID."""
    result = await db.execute(
        select(Policy).where(Policy.id == policy_id, Policy.user_id == user.id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(
    payload: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Create a new policy."""
    policy = Policy(
        id                           = uuid.uuid4(),
        user_id                      = user.id,
        name                         = payload.name,
        description                  = payload.description,
        enabled                      = payload.enabled,
        applies_to_all_workflows     = payload.applies_to_all_workflows,
        workflow_ids                 = payload.workflow_ids,
        conditions                   = payload.conditions.model_dump(exclude_none=True),
        action                       = payload.action,
        priority                     = payload.priority,
        notify_on_trigger            = payload.notify_on_trigger,
        notification_channels        = payload.notification_channels,
    )
    db.add(policy)
    await db.flush()

    # Audit log
    db.add(AuditLog(
        id=uuid.uuid4(), user_id=user.id, entity_type="policy",
        entity_id=policy.id, action="policy.created", performed_by=user.id,
        snapshot={"name": policy.name, "action": policy.action},
    ))

    await db.commit()
    await db.refresh(policy)
    return policy


@router.patch("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: uuid.UUID,
    payload: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Update a policy."""
    result = await db.execute(
        select(Policy).where(Policy.id == policy_id, Policy.user_id == user.id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "conditions" in update_data and update_data["conditions"]:
        update_data["conditions"] = update_data["conditions"].model_dump(exclude_none=True)

    for key, value in update_data.items():
        setattr(policy, key, value)

    db.add(AuditLog(
        id=uuid.uuid4(), user_id=user.id, entity_type="policy",
        entity_id=policy.id, action="policy.updated", performed_by=user.id,
        snapshot={"updated_fields": list(update_data.keys())},
    ))

    await db.commit()
    await db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """Delete a policy."""
    result = await db.execute(
        select(Policy).where(Policy.id == policy_id, Policy.user_id == user.id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    db.add(AuditLog(
        id=uuid.uuid4(), user_id=user.id, entity_type="policy",
        entity_id=policy.id, action="policy.deleted", performed_by=user.id,
        snapshot={"name": policy.name},
    ))

    await db.delete(policy)
    await db.commit()
