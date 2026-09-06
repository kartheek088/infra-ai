from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.utils import to_uuid
from app.models.user import User
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate, WorkflowResponse

router = APIRouter(prefix="/api/workflows", tags=["Workflows"])


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workflow).where(Workflow.user_id == current_user.id).order_by(Workflow.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=WorkflowResponse, status_code=201)
async def create_workflow(data: WorkflowCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Workflow).where(Workflow.n8n_workflow_id == data.n8n_workflow_id))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "This n8n workflow ID is already registered")
    workflow = Workflow(name=data.name, description=data.description,
                        n8n_workflow_id=data.n8n_workflow_id, user_id=current_user.id)
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    wf_uuid = to_uuid(workflow_id)
    result = await db.execute(
        select(Workflow).where(Workflow.id == wf_uuid, Workflow.user_id == current_user.id)
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return wf


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: str, data: WorkflowUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    wf_uuid = to_uuid(workflow_id)
    result = await db.execute(
        select(Workflow).where(Workflow.id == wf_uuid, Workflow.user_id == current_user.id)
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(404, "Workflow not found")
    if data.name is not None:
        wf.name = data.name
    if data.description is not None:
        wf.description = data.description
    await db.commit()
    await db.refresh(wf)
    return wf


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    wf_uuid = to_uuid(workflow_id)
    result = await db.execute(
        select(Workflow).where(Workflow.id == wf_uuid, Workflow.user_id == current_user.id)
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(404, "Workflow not found")
    await db.delete(wf)
    await db.commit()
