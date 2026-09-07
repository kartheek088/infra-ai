from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
from typing import Optional
from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.utils import to_uuid
from app.models.user import User
from app.models.workflow import Workflow
from app.models.run import Run, TokenUsage
from app.schemas.execution import RunCreate, RunResponse, TokenUsageCreate, TokenUsageResponse, TokenSummaryResponse
from app.services.anomaly_detector import build_timeline, detect_anomalies

router = APIRouter(prefix="/api/executions", tags=["Executions & Tokens"])


@router.post("/", response_model=RunResponse, status_code=201)
async def create_execution(
    data: RunCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = Run(**data.model_dump())
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/{workflow_id}", response_model=list[RunResponse])
async def get_executions(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    # Filtering params
    status: Optional[str]  = Query(default=None, description="Filter by: success, failed, running"),
    platform: Optional[str] = Query(default=None, description="Filter by: n8n, make, zapier, custom"),
    date_from: Optional[str] = Query(default=None, description="ISO date e.g. 2026-03-01"),
    date_to: Optional[str]   = Query(default=None, description="ISO date e.g. 2026-03-31"),
    min_cost: Optional[float] = Query(default=None, description="Minimum cost in USD"),
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Get execution history with filtering support.
    Filter by status, platform, date range, and minimum cost.
    """
    wf_uuid = to_uuid(workflow_id)
    wf = await db.execute(
        select(Workflow).where(Workflow.id == wf_uuid, Workflow.user_id == current_user.id)
    )
    if not wf.scalar_one_or_none():
        raise HTTPException(404, "Workflow not found")

    # Build dynamic filters
    filters = [Run.workflow_id == wf_uuid]
    if status:
        filters.append(Run.status == status)
    if platform:
        filters.append(Run.platform == platform)
    if date_from:
        try:
            filters.append(Run.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            filters.append(Run.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    result = await db.execute(
        select(Run).where(*filters).order_by(Run.created_at.desc()).limit(limit)
    )
    runs = result.scalars().all()

    # Apply min_cost filter (needs token join — done in Python)
    if min_cost is not None and runs:
        run_ids = [r.id for r in runs]
        token_result = await db.execute(
            select(TokenUsage).where(TokenUsage.run_id.in_(run_ids))
        )
        tokens = token_result.scalars().all()
        cost_by_run: dict = {}
        for t in tokens:
            rid = str(t.run_id)
            cost_by_run[rid] = cost_by_run.get(rid, 0) + t.cost_usd
        runs = [r for r in runs if cost_by_run.get(str(r.id), 0) >= min_cost]

    return runs


@router.get("/{execution_id}/tokens", response_model=TokenSummaryResponse)
async def get_execution_tokens(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full token breakdown for an execution — prompt vs completion per node."""
    run_uuid = to_uuid(execution_id)
    result = await db.execute(
        select(TokenUsage).where(TokenUsage.run_id == run_uuid).order_by(TokenUsage.recorded_at)
    )
    tokens = result.scalars().all()
    return TokenSummaryResponse(
        run_id=execution_id,
        total_prompt_tokens=sum(t.prompt_tokens for t in tokens),
        total_completion_tokens=sum(t.completion_tokens for t in tokens),
        total_tokens=sum(t.total_tokens for t in tokens),
        total_cost_usd=round(sum(t.cost_usd for t in tokens), 8),
        by_node=tokens,
    )


@router.post("/{execution_id}/tokens", response_model=TokenUsageResponse, status_code=201)
async def store_tokens(
    execution_id: str,
    data: TokenUsageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Store token data for a specific execution node.
    Requires authentication and ownership of the workflow that this execution belongs to.
    """
    run_uuid = to_uuid(execution_id)
    run_result = await db.execute(select(Run).where(Run.id == run_uuid))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Execution not found")

    wf_result = await db.execute(
        select(Workflow).where(Workflow.id == run.workflow_id, Workflow.user_id == current_user.id)
    )
    if not wf_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized for this execution")

    token = TokenUsage(run_id=run_uuid, **data.model_dump())
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


@router.get("/{execution_id}/nodes", response_model=list[TokenUsageResponse])
async def get_execution_nodes(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-node token and cost breakdown, sorted by cost descending."""
    run_uuid = to_uuid(execution_id)
    result = await db.execute(
        select(TokenUsage)
        .where(TokenUsage.run_id == run_uuid)
        .order_by(TokenUsage.cost_usd.desc())
    )
    return result.scalars().all()


@router.get("/{execution_id}/trace")
async def get_execution_trace(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Node-level execution trace.
    Shows each AI node in execution order with tokens, cost, and model.
    """
    run_uuid = to_uuid(execution_id)
    run_result = await db.execute(select(Run).where(Run.id == run_uuid))
    run        = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Execution not found")

    token_result = await db.execute(
        select(TokenUsage)
        .where(TokenUsage.run_id == run_uuid)
        .order_by(TokenUsage.recorded_at)
    )
    nodes = token_result.scalars().all()

    total_cost   = sum(n.cost_usd for n in nodes)
    total_tokens = sum(n.total_tokens for n in nodes)

    return {
        "execution_id":    execution_id,
        "status":          run.status,
        "platform":        run.platform,
        "triggered_by":    run.triggered_by,
        "duration_ms":     run.duration_ms,
        "started_at":      run.started_at.isoformat() if run.started_at else None,
        "finished_at":     run.finished_at.isoformat() if run.finished_at else None,
        "total_tokens":    total_tokens,
        "total_cost_usd":  round(total_cost, 8),
        "node_trace": [
            {
                "step":               i + 1,
                "node_name":          n.node_name,
                "model":              n.model,
                "prompt_tokens":      n.prompt_tokens,
                "completion_tokens":  n.completion_tokens,
                "total_tokens":       n.total_tokens,
                "cost_usd":           round(n.cost_usd, 8),
                "cost_pct":           round(n.cost_usd / total_cost * 100, 1) if total_cost > 0 else 0,
                "recorded_at":         n.recorded_at.isoformat() if n.recorded_at else None,
                # Phase 1 extended fields
                "node_type":          n.node_type,
                "event_type":         n.event_type,
                "provider":           n.provider,
                "error_message":      n.error_message,
                "latency_ms":         n.latency_ms,
                "node_metadata":      n.node_metadata,
            }
            for i, n in enumerate(nodes)
        ],
        "events":          run.events_jsonb,
        "error_hint": (
            "Execution failed — check your n8n execution logs for the specific error. "
            "Common causes: API timeout, invalid input, rate limit exceeded."
            if run.status == "failed" else None
        ),
    }


# ── Phase 4: Timeline + Anomaly detection ────────────────────────────────────

@router.get("/{execution_id}/timeline")
async def get_execution_timeline(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execution timeline: ordered steps combining node executions (tokens, cost,
    latency) and structured events (lifecycle, errors, security findings).

    Multi-tenant safe — returns 404 if the user doesn't own the workflow.
    """
    run_uuid = to_uuid(execution_id)

    run = await db.execute(
        select(Run).where(Run.id == run_uuid)
    )
    run = run.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Execution not found")

    wf = await db.execute(
        select(Workflow).where(Workflow.id == run.workflow_id, Workflow.user_id == current_user.id)
    )
    if not wf.scalar_one_or_none():
        raise HTTPException(403, "Not authorized for this execution")

    timeline = await build_timeline(
        run_id=execution_id,
        tenant_id=str(run.tenant_id),
        db=db,
    )
    return timeline


@router.get("/{execution_id}/anomalies")
async def get_execution_anomalies(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Anomaly list for one execution.

    Detects: latency spikes, token spikes, node failures, idle gaps between
    steps, and cost spikes vs. the workflow's rolling average.

    Multi-tenant safe — returns 404 if the user doesn't own the workflow.
    """
    run_uuid = to_uuid(execution_id)

    run = await db.execute(
        select(Run).where(Run.id == run_uuid)
    )
    run = run.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Execution not found")

    wf = await db.execute(
        select(Workflow).where(Workflow.id == run.workflow_id, Workflow.user_id == current_user.id)
    )
    if not wf.scalar_one_or_none():
        raise HTTPException(403, "Not authorized for this execution")

    anomalies = await detect_anomalies(
        run_id=execution_id,
        tenant_id=str(run.tenant_id),
        db=db,
    )
    return {"execution_id": execution_id, "anomaly_count": len(anomalies), "anomalies": anomalies}


# ── Phase 8: AI explanation (cached) ─────────────────────────────────────────

@router.get("/{execution_id}/ai-explanation")
async def get_ai_explanation(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the cached AI explanation for this execution.

    The explanation is generated by the background task exactly once per
    execution completion (Run.ai_explanation is set then). Subsequent calls
    return the cached text — we never re-call the LLM per page load.

    If the explanation has not been generated yet, `text` is null and
    `status` is "pending". If the API key is not configured, `status` is
    "unavailable" (no LLM call is attempted).
    """
    from app.core.config import settings

    run_uuid = to_uuid(execution_id)
    run_result = await db.execute(select(Run).where(Run.id == run_uuid))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Execution not found")

    wf = await db.execute(
        select(Workflow).where(Workflow.id == run.workflow_id, Workflow.user_id == current_user.id)
    )
    if not wf.scalar_one_or_none():
        raise HTTPException(403, "Not authorized for this execution")

    if run.ai_explanation:
        return {
            "execution_id": execution_id,
            "status":       "ready",
            "text":         run.ai_explanation,
            "explained_at": run.ai_explained_at.isoformat() if run.ai_explained_at else None,
            "cached":       True,
        }

    if not settings.OPENROUTER_API_KEY:
        return {
            "execution_id": execution_id,
            "status":       "unavailable",
            "text":         None,
            "explained_at": None,
            "cached":       False,
            "reason":       "OPENROUTER_API_KEY not configured on server",
        }

    return {
        "execution_id": execution_id,
        "status":       "pending",
        "text":         None,
        "explained_at": None,
        "cached":       False,
    }
