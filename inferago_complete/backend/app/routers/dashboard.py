import asyncio
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.utils import to_uuid
from app.models.user import User
from app.models.workflow import Workflow
from app.models.run import Run, TokenUsage
from app.models.alert import Alert
from app.services.rag_analyzer import get_rag_summary
from app.services.suggestions import generate_suggestions
from app.services.health_score import calculate_health_score

logger = logging.getLogger("inferago")
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


async def _safe(coro, default):
    """Run a coroutine and return its result, or `default` if it raises.
    Prevents one failing component from killing the whole dashboard load."""
    try:
        return await coro
    except Exception as e:
        logger.warning("Dashboard component failed: %s: %s", type(e).__name__, e)
        return default


@router.get("/{workflow_id}")
async def get_dashboard(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Master dashboard endpoint — returns everything in one request.
    All queries run in parallel; each component is isolated so a single
    failure (e.g. missing RAG data) returns None instead of 500ing.
    """
    wf_uuid = to_uuid(workflow_id)
    workflow_result, runs_result, health, rag, suggestions_list, alerts_result = \
        await asyncio.gather(
            _safe(
                db.execute(select(Workflow).where(
                    Workflow.id == wf_uuid, Workflow.user_id == current_user.id
                )),
                None,
            ),
            _safe(
                db.execute(
                    select(Run).where(Run.workflow_id == wf_uuid)
                    .order_by(Run.created_at.desc()).limit(10)
                ),
                None,
            ),
            _safe(calculate_health_score(workflow_id, db), None),
            _safe(get_rag_summary(workflow_id, db), None),
            _safe(generate_suggestions(workflow_id, db), []),
            _safe(
                db.execute(select(Alert).where(
                    Alert.workflow_id == wf_uuid, Alert.is_active == True
                )),
                None,
            ),
        )

    workflow = workflow_result.scalar_one_or_none() if workflow_result is not None else None
    if not workflow:
        return {"error": "Workflow not found"}

    runs   = runs_result.scalars().all() if runs_result is not None else []
    alerts = alerts_result.scalars().all() if alerts_result is not None else []

    run_ids      = [r.id for r in runs]
    token_result = await db.execute(select(TokenUsage).where(TokenUsage.run_id.in_(run_ids)))
    tokens       = token_result.scalars().all()

    total_tokens = sum(t.total_tokens for t in tokens)
    total_cost   = round(sum(t.cost_usd for t in tokens), 6)

    cost_by_run = {}
    for t in tokens:
        rid = str(t.run_id)
        cost_by_run[rid] = cost_by_run.get(rid, 0) + t.cost_usd

    cost_trend = [
        {
            "run_id":   str(r.id),
            "cost":     round(cost_by_run.get(str(r.id), 0), 6),
            "status":   r.status,
            "platform": r.platform,
            "date":     r.created_at.isoformat() if r.created_at else None,
        }
        for r in reversed(runs)
    ]

    return {
        "workflow": {
            "id":              str(workflow.id),
            "name":            workflow.name,
            "description":     workflow.description,
            "n8n_workflow_id": workflow.n8n_workflow_id,
            "created_at":      workflow.created_at.isoformat() if workflow.created_at else None,
        },
        "health":        health,
        "token_summary": {
            "total_tokens":      total_tokens,
            "total_cost_usd":    total_cost,
            "total_runs":        len(runs),
            "last_run_at":       runs[0].created_at.isoformat() if runs else None,
            "last_run_status":   runs[0].status if runs else None,
            "last_run_platform": runs[0].platform if runs else None,
        },
        "cost_trend":  cost_trend,
        "rag_summary": rag,
        "suggestions": [
            {"type": s.type, "impact": s.impact, "title": s.title,
             "description": s.description, "estimated_saving": s.estimated_saving,
             "action": s.action}
            for s in (suggestions_list or [])[:3]
        ],
        "alerts": [
            {"id": str(a.id), "type": a.alert_type,
             "threshold": a.threshold_value,
             "last_triggered": a.last_triggered_at.isoformat() if a.last_triggered_at else None}
            for a in alerts
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }
