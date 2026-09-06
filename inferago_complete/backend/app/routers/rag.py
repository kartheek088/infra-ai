from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.utils import to_uuid
from app.models.user import User
from app.models.run import Run
from app.models.rag import RAGMetrics
from app.schemas.rag import RAGMetricsCreate, RAGMetricsResponse
from app.services.rag_analyzer import get_rag_summary, get_rag_efficiency_trend

router = APIRouter(prefix="/api/rag", tags=["RAG Analytics"])


@router.post("/{run_id}", response_model=RAGMetricsResponse, status_code=201)
async def store_rag_metrics(
    run_id: str,
    data: RAGMetricsCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Store RAG metrics for a run. Requires authentication and the caller must
    own the workflow that this run belongs to.
    """
    # Verify the run exists and belongs to the current user's workflow
    run_uuid = to_uuid(run_id)
    run_result = await db.execute(select(Run).where(Run.id == run_uuid))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Check the workflow ownership via the run's workflow_id
    from app.models.workflow import Workflow
    wf_result = await db.execute(
        select(Workflow).where(Workflow.id == run.workflow_id, Workflow.user_id == current_user.id)
    )
    workflow = wf_result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=403, detail="Not authorized for this run")

    # Ensure the workflow_id in the request body matches the run's workflow
    if data.workflow_id and str(data.workflow_id) != str(run.workflow_id):
        raise HTTPException(status_code=400, detail="workflow_id mismatch with run")

    rag = RAGMetrics(run_id=run_uuid, **data.model_dump())
    db.add(rag)
    await db.commit()
    await db.refresh(rag)
    return rag


@router.get("/{workflow_id}/summary")
async def rag_summary(workflow_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    summary = await get_rag_summary(workflow_id, db)
    if not summary:
        raise HTTPException(404, "No RAG data found for this workflow")
    return summary


@router.get("/{workflow_id}/efficiency")
async def rag_efficiency(workflow_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_rag_efficiency_trend(workflow_id, db)
