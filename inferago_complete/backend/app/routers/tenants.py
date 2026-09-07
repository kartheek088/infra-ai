"""
Tenant CRUD router — Phase 1: Core Multi-tenancy.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import current_active_user
from app.models.tenant import Tenant
from app.models.user import User
from app.models.application import Application
from app.models.workflow import Workflow
from app.schemas.tenant import TenantCreate, TenantUpdate, Tenant, TenantWithStats

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantWithStats])
async def list_tenants(
    limit:  int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(current_active_user),
):
    """List all tenants with aggregate stats (admin use)."""
    # Subqueries for counts
    user_count_q = (
        select(func.count(User.id))
        .where(User.tenant_id == Tenant.id)
        .correlate(Tenant)
        .scalar_subquery()
    )
    app_count_q = (
        select(func.count(Application.id))
        .where(Application.tenant_id == Tenant.id)
        .correlate(Tenant)
        .scalar_subquery()
    )
    wf_count_q = (
        select(func.count(Workflow.id))
        .where(Workflow.tenant_id == Tenant.id)
        .correlate(Tenant)
        .scalar_subquery()
    )

    q = (
        select(
            Tenant,
            user_count_q.label("user_count"),
            app_count_q.label("application_count"),
            wf_count_q.label("workflow_count"),
        )
        .order_by(Tenant.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()

    out = []
    for row in rows:
        tenant = TenantWithStats.model_validate(row[0])
        tenant.user_count = row.user_count or 0
        tenant.application_count = row.application_count or 0
        tenant.workflow_count = row.workflow_count or 0
        out.append(tenant)
    return out


@router.get("/{tenant_id}", response_model=TenantWithStats)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(current_active_user),
):
    """Get a single tenant with stats."""
    user_count_q = (
        select(func.count(User.id))
        .where(User.tenant_id == tenant_id)
        .scalar_subquery()
    )
    app_count_q = (
        select(func.count(Application.id))
        .where(Application.tenant_id == tenant_id)
        .scalar_subquery()
    )
    wf_count_q = (
        select(func.count(Workflow.id))
        .where(Workflow.tenant_id == tenant_id)
        .scalar_subquery()
    )

    result = await db.execute(
        select(
            Tenant,
            user_count_q.label("user_count"),
            app_count_q.label("application_count"),
            wf_count_q.label("workflow_count"),
        ).where(Tenant.id == tenant_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = TenantWithStats.model_validate(row[0])
    tenant.user_count = row.user_count or 0
    tenant.application_count = row.application_count or 0
    tenant.workflow_count = row.workflow_count or 0
    return tenant


@router.post("", response_model=Tenant, status_code=201)
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(current_active_user),
):
    """Create a new tenant."""
    # Check slug uniqueness
    existing = await db.execute(select(Tenant).where(Tenant.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Tenant slug already exists")

    tenant = Tenant(
        id=uuid.uuid4(),
        name=payload.name,
        slug=payload.slug,
        plan=payload.plan,
        is_active=True,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}", response_model=Tenant)
async def update_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(current_active_user),
):
    """Update a tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if payload.slug is not None:
        existing = await db.execute(
            select(Tenant).where(Tenant.slug == payload.slug, Tenant.id != tenant_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Tenant slug already exists")

    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(tenant, key, value)

    await db.commit()
    await db.refresh(tenant)
    return tenant
