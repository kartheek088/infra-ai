"""
Application CRUD router — Phase 1: Core Multi-tenancy.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import current_active_user
from app.models.tenant import Tenant
from app.models.application import Application
from app.models.workflow import Workflow
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationUpdate, Application, ApplicationWithStats

router = APIRouter(prefix="/api/applications", tags=["applications"])


async def _verify_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Raise 404 if tenant does not exist or is inactive."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if not tenant.is_active:
        raise HTTPException(status_code=400, detail="Tenant is inactive")


@router.get("", response_model=list[ApplicationWithStats])
async def list_applications(
    tenant_id: uuid.UUID,
    is_active: bool = Query(None),
    limit:    int = Query(50, ge=1, le=200),
    offset:    int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(current_active_user),
):
    """List applications for a tenant."""
    wf_count_q = (
        select(func.count(Workflow.id))
        .where(Workflow.application_id == Application.id)
        .correlate(Application)
        .scalar_subquery()
    )

    q = (
        select(
            Application,
            wf_count_q.label("workflow_count"),
        )
        .where(Application.tenant_id == tenant_id)
    )
    if is_active is not None:
        q = q.where(Application.is_active == is_active)
    q = q.order_by(Application.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(q)
    rows = result.all()

    out = []
    for row in rows:
        app = ApplicationWithStats.model_validate(row[0])
        app.workflow_count = row.workflow_count or 0
        out.append(app)
    return out


@router.get("/{application_id}", response_model=ApplicationWithStats)
async def get_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(current_active_user),
):
    """Get a single application."""
    wf_count_q = (
        select(func.count(Workflow.id))
        .where(Workflow.application_id == application_id)
        .scalar_subquery()
    )

    result = await db.execute(
        select(
            Application,
            wf_count_q.label("workflow_count"),
        ).where(Application.id == application_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")

    app = ApplicationWithStats.model_validate(row[0])
    app.workflow_count = row.workflow_count or 0
    return app


@router.post("", response_model=Application, status_code=201)
async def create_application(
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(current_active_user),
):
    """Create a new application."""
    await _verify_tenant(db, payload.tenant_id)

    app = Application(
        id=uuid.uuid4(),
        tenant_id=payload.tenant_id,
        name=payload.name,
        description=payload.description,
        environment=payload.environment,
        is_active=True,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


@router.patch("/{application_id}", response_model=Application)
async def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(current_active_user),
):
    """Update an application."""
    result = await db.execute(select(Application).where(Application.id == application_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if payload.environment is not None:
        env = payload.environment.lower()
        if env not in ("production", "staging", "development", "testing"):
            raise HTTPException(
                status_code=400,
                detail="environment must be one of: production, staging, development, testing",
            )

    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update_data.items():
        setattr(app, key, value)

    await db.commit()
    await db.refresh(app)
    return app
