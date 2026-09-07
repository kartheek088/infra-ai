from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid
from app.db.session import get_db, AsyncSessionLocal
from app.models.workflow import Workflow
from app.models.run import Run, TokenUsage
from app.models.api_key import ApiKey
from app.models.event import Event, EventType, Component
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


async def validate_api_key(api_key: str, db: AsyncSession) -> tuple[str, str] | None:
    """
    Validate API key and return (user_id, tenant_id).
    Updates last_used_at.

    Returns None if the key is missing or revoked. Callers should raise
    HTTP 401 on None.
    """
    result = await db.execute(
        select(ApiKey).where(ApiKey.key == api_key, ApiKey.is_active == True)
    )
    key_record = result.scalar_one_or_none()
    if not key_record:
        return None
    key_record.last_used_at = datetime.utcnow()
    await db.flush()
    return key_record.user_id, key_record.tenant_id


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
    tenant_id: str,
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
            tenant_uuid  = to_uuid(tenant_id)

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
                    finding, wf_uuid, tenant_uuid
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


async def run_ai_explanation_background(
    run_id: str,
    tenant_id: str,
) -> None:
    """
    Background task: generate and cache an AI explanation for one execution.

    Opens its own database session. Only runs when Run.ai_explanation is NULL
    (idempotent — multiple webhook redeliveries are safely skipped).

    Fetches:
      • Run metadata (status, platform, duration_ms)
      • TokenUsage rows (top nodes by cost for the prompt)
      • Anomalies (via detect_anomalies)
      • Security findings (via detect_anomalies -> security_findings)

    Writes Run.ai_explanation and Run.ai_explained_at on success.
    """
    from sqlalchemy import select
    from datetime import datetime, timezone as tz
    from app.models.run import Run, TokenUsage
    from app.models.security_finding import SecurityFinding
    from app.services.openrouter_client import explain_execution
    from app.services.anomaly_detector import detect_anomalies

    async with AsyncSessionLocal() as db:
        run_uuid    = to_uuid(run_id)
        tenant_uuid = to_uuid(tenant_id)

        # Guard: skip if already generated (idempotent)
        run_result = await db.execute(
            select(Run).where(Run.id == run_uuid, Run.tenant_id == tenant_uuid)
        )
        run = run_result.scalar_one_or_none()
        if not run or run.ai_explanation is not None:
            return

        # ── Gather data for the prompt ──────────────────────────────────
        # Token rows — top 5 by cost
        token_result = await db.execute(
            select(TokenUsage)
            .where(TokenUsage.run_id == run_uuid, TokenUsage.tenant_id == tenant_uuid)
            .order_by(TokenUsage.cost_usd.desc())
            .limit(5)
        )
        top_nodes = [
            {
                "node_name":    t.node_name,
                "model":        t.model,
                "cost_usd":     t.cost_usd,
                "total_tokens": t.total_tokens,
                "latency_ms":   t.latency_ms,
                "error_message": t.error_message,
            }
            for t in token_result.scalars().all()
        ]

        total_cost   = sum((n.cost_usd or 0.0) for n in top_nodes)
        total_tokens = sum(n.total_tokens or 0  for n in top_nodes)
        node_count   = len(top_nodes)

        # Anomalies
        try:
            anomalies = await detect_anomalies(
                run_id=str(run_uuid), tenant_id=str(tenant_uuid), db=db
            )
        except Exception:
            anomalies = []

        # Security findings
        sf_result = await db.execute(
            select(SecurityFinding)
            .where(SecurityFinding.run_id == run_uuid, SecurityFinding.tenant_id == tenant_uuid)
            .limit(10)
        )
        findings = [
            {
                "detector_id": f.detector_id,
                "severity":    f.severity,
                "risk_score":  f.risk_score,
                "node_name":   f.node_name,
            }
            for f in sf_result.scalars().all()
        ]

        # ── Call OpenRouter ──────────────────────────────────────────────
        text, ok = await explain_execution(
            run_status=run.status,
            platform=run.platform,
            duration_ms=run.duration_ms,
            total_cost=total_cost,
            total_tokens=total_tokens,
            node_count=node_count,
            failed_node_count=sum(1 for n in top_nodes if n.get("error_message")),
            anomalies=anomalies,
            findings=findings,
            top_nodes=top_nodes,
        )

        # ── Persist (only if we got a real response) ─────────────────────
        if ok and text:
            run.ai_explanation  = text
            run.ai_explained_at = datetime.now(tz.utc)
            try:
                await db.commit()
            except Exception:
                await db.rollback()


async def process_execution(
    execution: StandardExecution,
    user_id: str,
    tenant_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> dict:
    """
    Platform-agnostic core processing.
    1. Find matching registered workflow
    2. Create Run record
    3. Store token usage per node
    4. Queue alert checks as background task (own session)
    5. Queue security + governance analysis as background task (own session)
    """
    uid_uuid    = to_uuid(user_id)
    tenant_uuid = to_uuid(tenant_id)
    wf_uuid     = to_uuid(execution.workflow_id)

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
        tenant_id=tenant_uuid,
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

    # ── Emit structured Event rows ─────────────────────────────────────
    await _emit_execution_events(
        execution=execution,
        run_id=run.id,
        workflow_id=workflow.id,
        user_id=uid_uuid,
        tenant_id=tenant_uuid,
        db=db,
    )

    # ── Store token usage per node ────────────────────────────────────
    total_tokens = 0
    total_cost   = 0.0
    node_snapshots = []

    for node in execution.nodes:
        token = TokenUsage(
            tenant_id=tenant_uuid,
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
        str(tenant_uuid),
        events_jsonb,
        node_snapshots,
    )

    # ── Queue AI explanation — cached per run, runs after security analysis ─
    background_tasks.add_task(
        run_ai_explanation_background,
        str(run.id),
        str(tenant_uuid),
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


async def _emit_execution_events(
    execution: StandardExecution,
    run_id: uuid.UUID,
    workflow_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """
    Persist structured Event rows for one execution.

    For each raw ExecutionEvent we map platform event types to ARI EventType values,
    and synthesize EXECUTION_COMPLETED / EXECUTION_FAILED lifecycle events from
    the execution status. We never silently drop events — unknown event types
    still land as INFO so the audit trail is complete.
    """
    from datetime import datetime as _dt, timezone as _tz

    rows: list[Event] = []

    # Map of platform-level event_type → ARI EventType.value
    lifecycle_map = {
        "execution_triggered": EventType.EXECUTION_STARTED,
        "execution_started":   EventType.EXECUTION_STARTED,
        "execution_finished":  EventType.EXECUTION_COMPLETED,
        "execution_succeeded": EventType.EXECUTION_COMPLETED,
        "execution_failed":    EventType.EXECUTION_FAILED,
        "node_started":        EventType.NODE_STARTED,
        "node_finished":       EventType.NODE_COMPLETED,
        "node_completed":      EventType.NODE_COMPLETED,
        "node_failed":         EventType.NODE_FAILED,
    }

    def _coerce(ts):
        if not ts:
            return None
        if isinstance(ts, _dt):
            # naive datetimes are treated as UTC
            return ts if ts.tzinfo else ts.replace(tzinfo=_tz.utc)
        return None

    # 1) Raw lifecycle events from the adapter
    for ev in (execution.events or []):
        mapped = lifecycle_map.get(ev.event_type)
        ari_event_type = mapped.value if mapped else EventType.INFO.value
        rows.append(Event(
            tenant_id=tenant_id,
            user_id=user_id,
            workflow_id=workflow_id,
            run_id=run_id,
            event_type=ari_event_type,
            component=Component.PLATFORM_ADAPTER.value,
            operation=ev.event_type,  # original platform event name
            actor=execution.triggered_by or "system",
            session_id=execution.execution_id or str(run_id),
            occurred_at=_coerce(ev.timestamp) or _dt.now(_tz.utc),
            payload={
                "platform":      execution.platform,
                "node_name":     ev.node_name,
                "source":        ev.source,
                "message":       ev.message,
                "raw_metadata":  ev.metadata or {},
            },
            severity=None if mapped else "info",
        ))

    # 2) Synthesize terminal lifecycle event from status if not already present
    seen_types = {ev.event_type for ev in (execution.events or [])}
    if execution.status in ("success", "finished", "completed") and \
       not (seen_types & {"execution_finished", "execution_completed", "execution_succeeded"}):
        rows.append(Event(
            tenant_id=tenant_id,
            user_id=user_id,
            workflow_id=workflow_id,
            run_id=run_id,
            event_type=EventType.EXECUTION_COMPLETED.value,
            component=Component.PLATFORM_ADAPTER.value,
            operation="execution_completed_synthesized",
            actor=execution.triggered_by or "system",
            session_id=execution.execution_id or str(run_id),
            occurred_at=_coerce(execution.finished_at) or _dt.now(_tz.utc),
            payload={
                "platform": execution.platform,
                "status":   execution.status,
            },
        ))
    elif execution.status in ("error", "failed") and \
         not (seen_types & {"execution_failed"}):
        rows.append(Event(
            tenant_id=tenant_id,
            user_id=user_id,
            workflow_id=workflow_id,
            run_id=run_id,
            event_type=EventType.EXECUTION_FAILED.value,
            component=Component.PLATFORM_ADAPTER.value,
            operation="execution_failed_synthesized",
            actor=execution.triggered_by or "system",
            session_id=execution.execution_id or str(run_id),
            occurred_at=_coerce(execution.finished_at) or _dt.now(_tz.utc),
            payload={
                "platform": execution.platform,
                "status":   execution.status,
            },
            severity="error",
        ))

    # 3) One node-level completed/failed event per node (in case the adapter
    #    only sent node data without lifecycle events)
    for node in (execution.nodes or []):
        if node.event_type in ("node_started", "node_finished", "node_failed"):
            mapped = lifecycle_map.get(node.event_type, EventType.NODE_COMPLETED)
            rows.append(Event(
                tenant_id=tenant_id,
                user_id=user_id,
                workflow_id=workflow_id,
                run_id=run_id,
                event_type=mapped.value,
                component=Component.PLATFORM_ADAPTER.value,
                operation=node.event_type,
                actor=execution.triggered_by or "system",
                session_id=execution.execution_id or str(run_id),
                occurred_at=_dt.now(_tz.utc),
                payload={
                    "platform":     execution.platform,
                    "node_name":    node.node_name,
                    "node_type":    node.node_type,
                    "model":        node.model,
                    "provider":     node.provider,
                    "cost_usd":     node.cost_usd,
                    "total_tokens": node.total_tokens,
                    "latency_ms":   node.latency_ms,
                    "error_message": node.error_message,
                },
                severity="error" if node.error_message else None,
            ))

    if rows:
        db.add_all(rows)
        # Flush so the rows get IDs and any FK constraint errors surface here
        # (not later, after the commit). We let the caller's commit() finalize.
        await db.flush()


def make_endpoint(platform: str):
    """Factory that creates one webhook endpoint per platform."""
    adapter = ADAPTERS[platform]

    async def endpoint(
        payload: dict,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
        api_key: str = Header(..., description="Your ARI API key (X-API-Key header)"),
    ):
        auth = await validate_api_key(api_key, db)
        if not auth:
            raise HTTPException(401, "Invalid or revoked API key")
        user_id, tenant_id = auth
        execution = adapter.normalize(payload)
        return await process_execution(execution, user_id, tenant_id, background_tasks, db)

    endpoint.__name__ = f"webhook_{platform}"
    return endpoint


# One endpoint per platform — same core logic, different payload format
router.post("/n8n",    summary="n8n webhook — fires after every workflow execution")(make_endpoint("n8n"))
router.post("/make",   summary="Make/Integromat webhook")(make_endpoint("make"))
router.post("/zapier", summary="Zapier webhook")(make_endpoint("zapier"))
router.post("/custom", summary="Custom/Universal webhook for any platform")(make_endpoint("custom"))
