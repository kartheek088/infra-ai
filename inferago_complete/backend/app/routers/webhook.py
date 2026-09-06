from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
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
    result   = await db.execute(
        select(Workflow).where(
            Workflow.n8n_workflow_id == execution.workflow_id,
            Workflow.user_id == uid_uuid,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        return {
            "status":   "skipped",
            "reason":   "Workflow not registered in Inferago",
            "hint":     f"Register workflow ID '{execution.workflow_id}' in your dashboard",
            "platform": execution.platform,
        }

    # ── Create run record ─────────────────────────────────────────────
    run = Run(
        workflow_id=workflow.id,
        n8n_execution_id=execution.execution_id,
        status=execution.status,
        triggered_by=execution.triggered_by,
        duration_ms=execution.duration_ms,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        platform=execution.platform,
    )
    db.add(run)
    await db.flush()

    # ── Store token usage per node ────────────────────────────────────
    total_tokens = 0
    total_cost   = 0.0

    for node in execution.nodes:
        token = TokenUsage(
            run_id=run.id,
            node_name=node.node_name,
            model=node.model,
            prompt_tokens=node.prompt_tokens,
            completion_tokens=node.completion_tokens,
            total_tokens=node.total_tokens,
            cost_usd=node.cost_usd,
        )
        db.add(token)
        total_tokens += node.total_tokens
        total_cost   += node.cost_usd

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

    return {
        "status":         "recorded",
        "run_id":         str(run.id),
        "workflow":       workflow.name,
        "platform":       execution.platform,
        "execution_id":   execution.execution_id,
        "nodes_tracked":  len(execution.nodes),
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
        api_key: str = Header(..., description="Your Inferago API key (X-API-Key header)"),
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
