"""
Audit log router — Phase 3: Governance.
"""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import current_active_user
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


class AuditLogResponse:
    """Pydantic-compatible response via model_validate."""
    pass


from pydantic import BaseModel, Field
from datetime import datetime


class AuditLogSchema(BaseModel):
    id:           uuid.UUID
    user_id:      uuid.UUID
    entity_type:  str
    entity_id:    uuid.UUID
    action:       str
    performed_by: Optional[uuid.UUID]
    snapshot:     Optional[dict]
    note:         Optional[str]
    ip_address:   Optional[str]
    user_agent:   Optional[str]
    created_at:   datetime
    model_config = {"from_attributes": True}


router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


@router.get("", response_model=list[AuditLogSchema])
async def list_audit_logs(
    entity_type: Optional[str] = Query(None),
    entity_id:   Optional[uuid.UUID] = Query(None),
    action:      Optional[str]        = Query(None),
    limit:       int = Query(100, ge=1, le=500),
    offset:      int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    """List audit log entries for the current user."""
    q = select(AuditLog).where(AuditLog.user_id == user.id)
    if entity_type: q = q.where(AuditLog.entity_type == entity_type)
    if entity_id:   q = q.where(AuditLog.entity_id == entity_id)
    if action:      q = q.where(AuditLog.action == action)
    q = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
