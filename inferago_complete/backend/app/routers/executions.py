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


@router.get("/recent")
async def get_recent_executions(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get real-time execution flow (recent executions across all workflows).
    Formatted with timeline steps, health status, duration, tokens, cost, anomalies, and AI explanation.
    """
    stmt = select(Run).order_by(Run.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    runs = result.scalars().all()

    output = []
    for r in runs:
        wf_res = await db.execute(select(Workflow).where(Workflow.id == r.workflow_id))
        wf = wf_res.scalar_one_or_none()
        wf_name = wf.name if wf else "Workflow Execution"

        timeline = await build_timeline(run_id=str(r.id), tenant_id=str(r.tenant_id), db=db)
        anomalies_data = await detect_anomalies(run_id=str(r.id), tenant_id=str(r.tenant_id), db=db)

        health = "SUCCESS"
        if r.status in ("failed", "error"):
            health = "FAILED"
        elif r.duration_ms and r.duration_ms > 3000:
            health = "DELAYED"
        if r.governance_decision in ("BLOCK", "BLOCKED"):
            health = "BLOCKED"
        elif r.governance_decision in ("REQUIRE_REVIEW", "REQUIRES_REVIEW"):
            health = "REQUIRE_REVIEW"

        output.append({
            "execution_id": r.n8n_execution_id or str(r.id),
            "run_id": str(r.id),
            "automation_name": wf_name,
            "workflow_id": str(r.workflow_id),
            "platform": r.platform,
            "health": health,
            "status": r.status,
            "total_duration": (r.duration_ms / 1000.0) if r.duration_ms else (timeline.get("duration_ms", 0) / 1000.0 if timeline.get("duration_ms") else 0.0),
            "total_tokens": timeline.get("total_tokens", 0),
            "total_cost": timeline.get("total_cost", 0.0),
            "timeline": timeline,
            "anomalies": [a.get("detail", a.get("kind", "")) for a in anomalies_data],
            "anomalies_full": anomalies_data,
            "explanation": r.ai_explanation,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return output


@router.post("/analyze")
async def analyze_execution_payload(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Instant execution analyzer — analyze any raw execution payload on the fly.
    Computes steps, latency, tokens, cost, anomalies, and returns instant trace.
    """
    from app.adapters.custom_adapter import CustomAdapter
    from app.services.openrouter_client import explain_execution

    adapter = CustomAdapter()
    std_exec = adapter.to_standard(payload)

    total_tokens = sum(n.total_tokens for n in std_exec.nodes)
    total_cost = sum(n.cost_usd for n in std_exec.nodes)
    total_duration_s = (std_exec.duration_ms / 1000.0) if std_exec.duration_ms else sum((n.latency_ms or 0) / 1000.0 for n in std_exec.nodes)

    steps = []
    anomalies = []
    for i, n in enumerate(std_exec.nodes):
        dur_s = (n.latency_ms / 1000.0) if n.latency_ms else 0.0
        steps.append({
            "step": n.node_name or f"Step {i+1}",
            "kind": "node",
            "status": "failed" if n.error_message else "SUCCESS",
            "duration": dur_s,
            "duration_ms": n.latency_ms,
            "tokens": n.total_tokens,
            "cost": n.cost_usd,
            "model": n.model,
            "provider": n.provider,
            "node_type": n.node_type,
            "error_message": n.error_message,
        })
        if dur_s > 3.0:
            anomalies.append(f"{n.node_name} latency spike ({dur_s:.2f}s)")
        if n.total_tokens > 500:
            anomalies.append(f"{n.node_name} token spike ({n.total_tokens:,} tokens)")
        if n.error_message:
            anomalies.append(f"{n.node_name} failed: {n.error_message}")

    health = "SUCCESS"
    if any(n.error_message for n in std_exec.nodes) or std_exec.status in ("failed", "error"):
        health = "FAILED"
    elif total_duration_s > 3.0:
        health = "DELAYED"

    timeline = {
        "execution_id": std_exec.execution_id or "live_test",
        "total_duration": total_duration_s,
        "steps": steps,
    }

    explanation, _ = await explain_execution(
        run_status=std_exec.status,
        platform=std_exec.platform,
        duration_ms=std_exec.duration_ms,
        total_cost=total_cost,
        total_tokens=total_tokens,
        node_count=len(std_exec.nodes),
        failed_node_count=sum(1 for n in std_exec.nodes if n.error_message),
        anomalies=[{"kind": "anomaly", "step": a, "detail": a, "severity": "medium"} for a in anomalies],
        findings=[],
        top_nodes=[{"node_name": n.node_name, "model": n.model, "cost_usd": n.cost_usd, "total_tokens": n.total_tokens, "latency_ms": n.latency_ms} for n in std_exec.nodes],
    )

    return {
        "execution_id": std_exec.execution_id or "live_test",
        "automation_name": std_exec.workflow_id or "Live Analyzed Execution",
        "health": health,
        "total_duration": total_duration_s,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "timeline": timeline,
        "anomalies": anomalies,
        "explanation": explanation or "Execution analyzed successfully.",
    }


@router.get("/summary/{execution_id}")
@router.get("/{execution_id}/summary")
async def get_execution_summary(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get full execution summary (trace, steps, anomalies, security findings, AI intelligence).
    """
    run_uuid = to_uuid(execution_id)
    run_res = await db.execute(
        select(Run).where((Run.id == run_uuid) | (Run.n8n_execution_id == execution_id))
    )
    run = run_res.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Execution not found")

    wf_res = await db.execute(select(Workflow).where(Workflow.id == run.workflow_id))
    wf = wf_res.scalar_one_or_none()
    wf_name = wf.name if wf else "Workflow Execution"

    timeline = await build_timeline(run_id=str(run.id), tenant_id=str(run.tenant_id), db=db)
    anomalies_data = await detect_anomalies(run_id=str(run.id), tenant_id=str(run.tenant_id), db=db)

    from app.models.security_finding import SecurityFinding
    sf_res = await db.execute(
        select(SecurityFinding).where(SecurityFinding.run_id == run.id)
    )
    findings = sf_res.scalars().all()

    health = "SUCCESS"
    if run.status in ("failed", "error"):
        health = "FAILED"
    elif run.duration_ms and run.duration_ms > 3000:
        health = "DELAYED"
    if run.governance_decision in ("BLOCK", "BLOCKED"):
        health = "BLOCKED"
    elif run.governance_decision in ("REQUIRE_REVIEW", "REQUIRES_REVIEW"):
        health = "REQUIRE_REVIEW"

    return {
        "execution_id": run.n8n_execution_id or str(run.id),
        "run_id": str(run.id),
        "automation_name": wf_name,
        "workflow_id": str(run.workflow_id),
        "platform": run.platform,
        "health": health,
        "status": run.status,
        "total_duration": (run.duration_ms / 1000.0) if run.duration_ms else (timeline.get("duration_ms", 0) / 1000.0 if timeline.get("duration_ms") else 0.0),
        "total_tokens": timeline.get("total_tokens", 0),
        "total_cost": timeline.get("total_cost", 0.0),
        "timeline": timeline,
        "anomalies": [a.get("detail", a.get("kind", "")) for a in anomalies_data],
        "anomalies_full": anomalies_data,
        "explanation": run.ai_explanation,
        "security_findings": [
            {
                "id": str(f.id),
                "detector_id": f.detector_id,
                "detector_name": f.detector_name,
                "severity": f.severity,
                "confidence": f.confidence,
                "title": f.title,
                "description": f.description,
                "risk_score": f.risk_score,
                "node_name": f.node_name,
                "governance_action": f.governance_action,
                "reviewed": f.reviewed,
            }
            for f in findings
        ],
        "governance_decision": run.governance_decision,
        "max_risk_score": run.max_risk_score,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
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
