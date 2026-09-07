from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid
from app.db.session import get_db, AsyncSessionLocal
from app.models.workflow import Workflow
from app.models.run import Run, TokenUsage
from app.models.api_key import ApiKey
from app.adapters.base_adapter import StandardExecution
from app.adapters.n8n_adapter import N8NAdapter
from app.adapters.make_adapter import MakeAdapter
from app.adapters.zapier_adapter import ZapierAdapter
from app.adapters.custom_adapter import CustomAdapter
from app.core.utils import to_uuid

router   = APIRouter(prefix="/api/webhook", tags=["Webhooks"])
ADAPTERS = {
    "n8n":    N8NAdapter,
    "make":   MakeAdapter,
    "zapier": ZapierAdapter,
    "custom": CustomAdapter,
}


async def validate_api_key(api_key: str, db: AsyncSession) -> str | None:
    """Validate API key and return user_id. Updates last_used_at."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.key == api_key, ApiKey.is_active == True)
    )
    key_record = result.scalar_one_or_none()
    if not key_record:
        return None
    key_record.last_used_at = datetime.utcnow()
    await db.flush()
    return key_record.user_id


async def get_workflow_averages(workflow_id: str, db: AsyncSession) -> dict:
    """Calculate rolling averages for spike detection (last 30 runs)."""
    wf_uuid = to_uuid(workflow_id)
    result = await db.execute(
        select(Run)
        .where(Run.workflow_id == wf_uuid)
        .order_by(Run.created_at.desc())
        .limit(30)
    )
    runs = result.scalars().all()
    if not runs:
        return {"avg_cost": 0.0, "avg_tokens": 0.0, "error_rate": 0.0}

    run_ids      = [r.id for r in runs]
    token_result = await db.execute(
        select(TokenUsage).where(TokenUsage.run_id.in_(run_ids))
    )
    tokens = token_result.scalars().all()

    costs_per_run: dict  = {}
    tokens_per_run: dict = {}
    for t in tokens:
        rid = str(t.run_id)
        costs_per_run[rid]  = costs_per_run.get(rid, 0)  + t.cost_usd
        tokens_per_run[rid] = tokens_per_run.get(rid, 0) + t.total_tokens

    avg_cost   = sum(costs_per_run.values())  / len(costs_per_run)  if costs_per_run  else 0.0
    avg_tokens = sum(tokens_per_run.values()) / len(tokens_per_run) if tokens_per_run else 0.0
    error_rate = sum(1 for r in runs if r.status == "failed") / len(runs)

    return {"avg_cost": avg_cost, "avg_tokens": avg_tokens, "error_rate": error_rate}


async def run_alert_checks_background(
    workflow_id: str,
    workflow_name: str,
    user_id: str,
    run_cost: float,
    total_tokens: int,
    platform: str,
) -> None:
    """
    Background task that opens its OWN database session.
    This is critical — the request session is closed by the time
    BackgroundTasks runs, so we cannot reuse it.
    """
    from app.services.notifications import check_and_fire_alerts, check_inactivity_alerts

    # Open a fresh session — request session is already closed
    async with AsyncSessionLocal() as db:
        try:
            averages = await get_workflow_averages(workflow_id, db)

            await check_and_fire_alerts(
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                user_id=user_id,
                run_cost=run_cost,
                total_tokens=total_tokens,
                avg_cost=averages["avg_cost"],
                avg_tokens=averages["avg_tokens"],
                error_rate=averages["error_rate"],
                platform=platform,
                db=db,
            )

            await check_inactivity_alerts(workflow_id, workflow_name, db)
            await db.commit()
        except Exception:
            await db.rollback()


async def run_security_analysis_background(
    run_id: str,
    workflow_id: str,
    user_id: str,
    execution_events: list,
    execution_nodes: list,
) -> None:
    """
    Background task: run security detectors, evaluate policies, and write audit logs.
    Opens its own database session so it runs after the request session is closed.
    """
    from app.core.security.engine import SecurityEngine
    from app.core.policy_engine import PolicyEvaluator
    from app.core.utils import to_uuid
    from app.models.security_finding import SecurityFinding
    from app.models.audit_log import AuditLog

    async with AsyncSessionLocal() as db:
        try:
            # Reconstruct lightweight execution objects from stored data
            from app.adapters.base_adapter import StandardExecution, NodeExecution, ExecutionEvent

            events = [
                ExecutionEvent(
                    event_type=e.get("event_type", ""),
                    timestamp=datetime.fromisoformat(e["timestamp"]) if e.get("timestamp") else None,
                    node_name=e.get("node_name"),
                    source=e.get("source"),
                    message=e.get("message"),
                    metadata=e.get("metadata") or {},
                )
                for e in (execution_events or [])
            ]

            nodes = [
                NodeExecution(
                    node_name=n.get("node_name", ""),
                    node_type=n.get("node_type") or "other",
                    model=n.get("model") or "",
                    prompt_tokens=n.get("prompt_tokens", 0),
                    completion_tokens=n.get("completion_tokens", 0),
                    total_tokens=n.get("total_tokens", 0),
                    cost_usd=n.get("cost_usd", 0.0),
                    event_type=n.get("event_type") or "node_finished",
                    provider=n.get("provider") or "",
                    error_message=n.get("error_message") or "",
                    latency_ms=n.get("latency_ms"),
                    metadata=n.get("metadata") or {},
                )
                for n in (execution_nodes or [])
            ]

            std_exec = StandardExecution(
                execution_id=run_id,
                workflow_id=workflow_id,
                platform="unknown",
                status="completed",
                triggered_by="",
                started_at=None,
                finished_at=None,
                duration_ms=None,
                events=events,
                nodes=nodes,
            )

            run_uuid     = to_uuid(run_id)
            wf_uuid      = to_uuid(workflow_id)
            user_uuid    = to_uuid(user_id)

            # Run security detectors
            engine = SecurityEngine(db)
            findings = await engine.analyze_execution(
                std_exec, nodes, run_uuid, wf_uuid, user_uuid
            )

            if not findings:
                return

            # Evaluate policies for each finding
            evaluator = PolicyEvaluator(db)
            for finding in findings:
                action, policy_id, policy_name = await evaluator.evaluate(
                    finding, wf_uuid
                )

                if action:
                    finding.governance_action = action
                    finding.policy_id         = policy_id
                    finding.policy_name       = policy_name

                    # Audit log entry for the governance decision
                    db.add(AuditLog(
                        id=uuid.uuid4(),
                        user_id=user_uuid,
                        entity_type="security_finding",
                        entity_id=finding.id,
                        action=f"governance.{action.lower()}",
                        performed_by=user_uuid,
                        snapshot={
                            "severity":     finding.severity,
                            "risk_score":   finding.risk_score,
                            "detector_id":  finding.detector_id,
                            "policy_id":    str(policy_id) if policy_id else None,
                            "policy_name":  policy_name,
                        },
                        note=f"Auto-assigned by policy '{policy_name}'" if policy_name else None,
                    ))

            await db.commit()

        except Exception:
            await db.rollback()


async def process_execution(
    execution: StandardExecution,
    user_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> dict:
    """
    Platform-agnostic core processing.
    1. Find matching registered workflow
    2. Create Run record
    3. Store token usage per node
    4. Queue alert checks as background task (own session)
    """
    uid_uuid = to_uuid(user_id)
    wf_uuid  = to_uuid(execution.workflow_id)

    # Match by workflow UUID (workflows.id) — the n8n payload sends
    # workflowId which is the workflow's internal UUID stored in workflows.id.
    # Fall back to n8n_workflow_id for adapters that send the external ID.
    result = await db.execute(
        select(Workflow).where(
            Workflow.id == wf_uuid,
            Workflow.user_id == uid_uuid,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        # Try matching by n8n_workflow_id (external adapter ID)
        result = await db.execute(
            select(Workflow).where(
                Workflow.n8n_workflow_id == execution.workflow_id,
                Workflow.user_id == uid_uuid,
            )
        )
        workflow = result.scalar_one_or_none()

    if not workflow:
        return {
            "status":   "skipped",
            "reason":   "Workflow not registered in ARI",
            "hint":     f"Register workflow ID '{execution.workflow_id}' in your dashboard",
            "platform": execution.platform,
        }

    # ── Create run record ─────────────────────────────────────────────
    # Serialize execution lifecycle events to JSONB
    events_jsonb = [
        {
            "event_type": ev.event_type,
            "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
            "node_name": ev.node_name,
            "source": ev.source,
            "message": ev.message,
            "metadata": ev.metadata,
        }
        for ev in (execution.events or [])
    ]

    run = Run(
        workflow_id=workflow.id,
        n8n_execution_id=execution.execution_id,
        status=execution.status,
        triggered_by=execution.triggered_by,
        duration_ms=execution.duration_ms,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        platform=execution.platform,
        events_jsonb=events_jsonb or None,
    )
    db.add(run)
    await db.flush()

    # ── Store token usage per node ────────────────────────────────────
    total_tokens = 0
    total_cost   = 0.0
    node_snapshots = []

    for node in execution.nodes:
        token = TokenUsage(
            run_id=run.id,
            node_name=node.node_name,
            model=node.model,
            prompt_tokens=node.prompt_tokens,
            completion_tokens=node.completion_tokens,
            total_tokens=node.total_tokens,
            cost_usd=node.cost_usd,
            # Phase 1 extended fields
            node_type=node.node_type or "other",
            event_type=node.event_type or "node_finished",
            provider=node.provider or "",
            error_message=node.error_message or "",
            latency_ms=node.latency_ms,
            node_metadata=node.metadata or {},
        )
        db.add(token)
        total_tokens += node.total_tokens
        total_cost   += node.cost_usd

        # Capture node data for security analysis (background task)
        node_snapshots.append({
            "node_name":         node.node_name,
            "model":             node.model,
            "prompt_tokens":     node.prompt_tokens,
            "completion_tokens": node.completion_tokens,
            "total_tokens":      node.total_tokens,
            "cost_usd":          node.cost_usd,
            "node_type":         node.node_type,
            "event_type":        node.event_type,
            "provider":          node.provider,
            "error_message":     node.error_message,
            "latency_ms":        node.latency_ms,
            "metadata":          node.metadata,
        })

    await db.commit()

    # ── Queue alert checks — uses its own session ─────────────────────
    background_tasks.add_task(
        run_alert_checks_background,
        str(workflow.id),
        workflow.name,
        user_id,
        total_cost,
        total_tokens,
        execution.platform,
    )

    # ── Queue security + governance analysis — uses its own session ───
    background_tasks.add_task(
        run_security_analysis_background,
        str(run.id),
        str(workflow.id),
        user_id,
        events_jsonb,
        node_snapshots,
    )

    return {
        "status":         "recorded",
        "run_id":         str(run.id),
        "workflow":       workflow.name,
        "platform":       execution.platform,
        "execution_id":   execution.execution_id,
        "nodes_tracked":  len(execution.nodes),
        "events_tracked": len(execution.events),
        "total_tokens":   total_tokens,
        "total_cost_usd": round(total_cost, 6),
    }


def make_endpoint(platform: str):
    """Factory that creates one webhook endpoint per platform."""
    adapter = ADAPTERS[platform]

    async def endpoint(
        payload: dict,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
        api_key: str = Header(..., description="Your ARI API key (X-API-Key header)"),
    ):
        user_id = await validate_api_key(api_key, db)
        if not user_id:
            raise HTTPException(401, "Invalid or revoked API key")
        execution = adapter.normalize(payload)
        return await process_execution(execution, user_id, background_tasks, db)

    endpoint.__name__ = f"webhook_{platform}"
    return endpoint


# One endpoint per platform — same core logic, different payload format
router.post("/n8n",    summary="n8n webhook — fires after every workflow execution")(make_endpoint("n8n"))
router.post("/make",   summary="Make/Integromat webhook")(make_endpoint("make"))
router.post("/zapier", summary="Zapier webhook")(make_endpoint("zapier"))
router.post("/custom", summary="Custom/Universal webhook for any platform")(make_endpoint("custom"))
