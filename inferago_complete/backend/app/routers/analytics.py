from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.utils import to_uuid
from app.models.user import User
from app.models.run import Run, TokenUsage
from app.models.workflow import Workflow
from app.services.health_score import calculate_health_score

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# ── Health score ──────────────────────────────────────────────────────────────
@router.get("/{workflow_id}/health")
async def health_score(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Composite health score 0-100 with grade and breakdown."""
    return await calculate_health_score(workflow_id, db)


# ── Token trend (7d / 30d / 90d) ─────────────────────────────────────────────
@router.get("/{workflow_id}/token-trend")
async def token_trend(
    workflow_id: str,
    days: int = Query(default=30, ge=7, le=90, description="7, 30, or 90"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Token usage trend over time — daily aggregated.
    Supports 7d, 30d, 90d windows.
    Returns: date, prompt_tokens, completion_tokens, total_tokens, cost_usd
    """
    wf_uuid = to_uuid(workflow_id)
    since   = datetime.utcnow() - timedelta(days=days)

    runs_result = await db.execute(
        select(Run)
        .where(Run.workflow_id == wf_uuid, Run.created_at >= since)
        .order_by(Run.created_at.asc())
    )
    runs = runs_result.scalars().all()
    if not runs:
        return {"days": days, "data": [], "summary": {}}

    run_ids      = [r.id for r in runs]
    token_result = await db.execute(
        select(TokenUsage).where(TokenUsage.run_id.in_(run_ids))
    )
    tokens = token_result.scalars().all()

    # Group by day
    daily: dict = {}
    token_by_run: dict = {}
    for t in tokens:
        rid = str(t.run_id)
        if rid not in token_by_run:
            token_by_run[rid] = {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0}
        token_by_run[rid]["prompt"]     += t.prompt_tokens
        token_by_run[rid]["completion"] += t.completion_tokens
        token_by_run[rid]["total"]      += t.total_tokens
        token_by_run[rid]["cost"]       += t.cost_usd

    for run in runs:
        day = run.created_at.strftime("%Y-%m-%d") if run.created_at else "unknown"
        if day not in daily:
            daily[day] = {"date": day, "runs": 0, "prompt_tokens": 0,
                          "completion_tokens": 0, "total_tokens": 0, "cost_usd": 0.0}
        rid  = str(run.id)
        d    = token_by_run.get(rid, {})
        daily[day]["runs"]              += 1
        daily[day]["prompt_tokens"]     += d.get("prompt", 0)
        daily[day]["completion_tokens"] += d.get("completion", 0)
        daily[day]["total_tokens"]      += d.get("total", 0)
        daily[day]["cost_usd"]          += d.get("cost", 0.0)

    data = list(daily.values())
    all_totals = [d["total_tokens"] for d in data]
    all_costs  = [d["cost_usd"]     for d in data]

    summary = {
        "total_tokens":       sum(all_totals),
        "total_cost_usd":     round(sum(all_costs), 6),
        "avg_tokens_per_day": round(sum(all_totals) / len(all_totals)) if all_totals else 0,
        "peak_tokens_day":    max(all_totals) if all_totals else 0,
        "avg_cost_per_day":   round(sum(all_costs) / len(all_costs), 6) if all_costs else 0,
        "peak_cost_day":      round(max(all_costs), 6) if all_costs else 0,
    }

    return {"days": days, "data": data, "summary": summary}


# ── Cost breakdown (per run / per day / per week / per month) ─────────────────
@router.get("/{workflow_id}/cost-breakdown")
async def cost_breakdown(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cost breakdown with projections.
    Returns: per_run, per_day, per_week, per_month, projected_monthly
    """
    wf_uuid = to_uuid(workflow_id)
    runs_result = await db.execute(
        select(Run)
        .where(Run.workflow_id == wf_uuid)
        .order_by(Run.created_at.desc())
        .limit(100)
    )
    runs = runs_result.scalars().all()
    if not runs:
        return {}

    run_ids      = [r.id for r in runs]
    token_result = await db.execute(
        select(TokenUsage).where(TokenUsage.run_id.in_(run_ids))
    )
    tokens = token_result.scalars().all()

    cost_by_run: dict = {}
    for t in tokens:
        rid = str(t.run_id)
        cost_by_run[rid] = cost_by_run.get(rid, 0) + t.cost_usd

    costs    = list(cost_by_run.values())
    avg_cost = sum(costs) / len(costs) if costs else 0

    # Estimate runs per day from date range
    if len(runs) > 1 and runs[-1].created_at and runs[0].created_at:
        days_span = max(1, (runs[0].created_at - runs[-1].created_at).days)
        runs_per_day = len(runs) / days_span
    else:
        runs_per_day = 1

    per_day   = avg_cost * runs_per_day
    per_week  = per_day * 7
    per_month = per_day * 30

    return {
        "avg_cost_per_run":     round(avg_cost, 6),
        "per_day":              round(per_day, 4),
        "per_week":             round(per_week, 4),
        "per_month":            round(per_month, 4),
        "projected_monthly":    round(per_month, 4),
        "runs_per_day_estimate": round(runs_per_day, 2),
        "total_runs_analyzed":  len(runs),
        "cost_breakdown_note":  "Based on last 100 runs",
    }


# ── Peak vs average token usage ───────────────────────────────────────────────
@router.get("/{workflow_id}/peak-vs-average")
async def peak_vs_average(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Peak vs average comparison for tokens and cost.
    Useful for detecting outlier runs.
    """
    wf_uuid = to_uuid(workflow_id)
    runs_result = await db.execute(
        select(Run)
        .where(Run.workflow_id == wf_uuid)
        .order_by(Run.created_at.desc())
        .limit(50)
    )
    runs = runs_result.scalars().all()
    if not runs:
        return {}

    run_ids      = [r.id for r in runs]
    token_result = await db.execute(
        select(TokenUsage).where(TokenUsage.run_id.in_(run_ids))
    )
    tokens = token_result.scalars().all()

    totals_by_run: dict = {}
    costs_by_run:  dict = {}
    for t in tokens:
        rid = str(t.run_id)
        totals_by_run[rid] = totals_by_run.get(rid, 0) + t.total_tokens
        costs_by_run[rid]  = costs_by_run.get(rid, 0)  + t.cost_usd

    token_vals = list(totals_by_run.values())
    cost_vals  = list(costs_by_run.values())

    return {
        "tokens": {
            "average": round(sum(token_vals) / len(token_vals)) if token_vals else 0,
            "peak":    max(token_vals) if token_vals else 0,
            "min":     min(token_vals) if token_vals else 0,
            "spike_ratio": round(max(token_vals) / (sum(token_vals) / len(token_vals)), 2) if token_vals else 0,
        },
        "cost": {
            "average": round(sum(cost_vals) / len(cost_vals), 6) if cost_vals else 0,
            "peak":    round(max(cost_vals), 6) if cost_vals else 0,
            "min":     round(min(cost_vals), 6) if cost_vals else 0,
            "spike_ratio": round(max(cost_vals) / (sum(cost_vals) / len(cost_vals)), 2) if cost_vals else 0,
        },
        "runs_analyzed": len(runs),
    }


# ── Inefficiency score ────────────────────────────────────────────────────────
@router.get("/{workflow_id}/inefficiency-score")
async def inefficiency_score(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Inefficiency score 0-100.
    0 = fully optimized, 100 = highly inefficient.
    Factors: prompt bloat, RAG waste, model overuse, error waste.
    """
    from app.services.suggestions import get_token_stats
    from app.services.rag_analyzer import get_rag_summary

    stats = await get_token_stats(workflow_id, db)
    rag   = await get_rag_summary(workflow_id, db)

    score = 0
    flags = []

    # Prompt bloat (0-25 points)
    avg_sys = stats.get("avg_system_prompt_tokens", 0)
    if avg_sys > 800:
        score += 25; flags.append("Severe prompt bloat (>800 tokens system prompt)")
    elif avg_sys > 400:
        score += 15; flags.append("Moderate prompt bloat (>400 tokens system prompt)")

    # RAG waste (0-25 points)
    if rag:
        efficiency = rag.get("efficiency_ratio", 1)
        if efficiency < 0.2:
            score += 25; flags.append("Severe RAG waste (<20% chunks used)")
        elif efficiency < 0.4:
            score += 15; flags.append("Moderate RAG waste (<40% chunks used)")
        elif efficiency < 0.6:
            score += 8;  flags.append("Some RAG waste (<60% chunks used)")

    # Cost spikes (0-25 points)
    if stats.get("cost_spike_detected"):
        score += 20; flags.append("Cost spikes detected (2.5x above average)")
    if stats.get("token_spike_detected"):
        score += 15; flags.append("Token spikes detected (3x above average)")

    # Error waste (0-25 points)
    error_rate = stats.get("error_rate", 0)
    if error_rate > 0.3:
        score += 25; flags.append(f"High error rate ({error_rate*100:.0f}% of runs fail)")
    elif error_rate > 0.15:
        score += 15; flags.append(f"Moderate error rate ({error_rate*100:.0f}% of runs fail)")

    score = min(100, score)
    grade = "Efficient" if score < 20 else "Moderate" if score < 50 else "Inefficient" if score < 75 else "Critical"

    return {
        "inefficiency_score": score,
        "grade":              grade,
        "flags":              flags,
        "interpretation":     f"Score of {score}/100 — {grade}. Lower is better.",
    }


# ── Platform summary ─────────────────────────────────────────────────────────
@router.get("/platforms/summary")
async def platform_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Spend and run count broken down by platform (n8n, make, zapier, custom)."""
    wf_result = await db.execute(select(Workflow.id).where(Workflow.user_id == current_user.id))
    wf_ids    = [row[0] for row in wf_result.fetchall()]
    if not wf_ids:
        return {"platforms": [], "total_cost_usd": 0}

    run_result = await db.execute(
        select(Run).where(Run.workflow_id.in_(wf_ids)).order_by(Run.created_at.desc()).limit(500)
    )
    runs = run_result.scalars().all()
    if not runs:
        return {"platforms": [], "total_cost_usd": 0}

    run_ids      = [r.id for r in runs]
    token_result = await db.execute(select(TokenUsage).where(TokenUsage.run_id.in_(run_ids)))
    tokens       = token_result.scalars().all()

    cost_by_run: dict = {}
    for t in tokens:
        rid = str(t.run_id)
        cost_by_run[rid] = cost_by_run.get(rid, 0) + t.cost_usd

    platform_data: dict = {}
    for run in runs:
        p = run.platform or "n8n"
        if p not in platform_data:
            platform_data[p] = {"name": p, "runs": 0, "cost_usd": 0.0}
        platform_data[p]["runs"]     += 1
        platform_data[p]["cost_usd"] += cost_by_run.get(str(run.id), 0)

    total     = sum(p["cost_usd"] for p in platform_data.values())
    platforms = []
    for p in platform_data.values():
        p["cost_usd"] = round(p["cost_usd"], 4)
        p["pct"]      = round((p["cost_usd"] / total * 100) if total > 0 else 0, 1)
        platforms.append(p)

    platforms.sort(key=lambda x: x["cost_usd"], reverse=True)
    return {"platforms": platforms, "total_cost_usd": round(total, 4)}
