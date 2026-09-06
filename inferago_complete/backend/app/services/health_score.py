from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.run import Run
from app.services.rag_analyzer import get_rag_summary
from app.services.suggestions import get_token_stats
from app.core.utils import to_uuid


async def calculate_health_score(workflow_id: str, db: AsyncSession) -> dict:
    wf_uuid = to_uuid(workflow_id)
    rag   = await get_rag_summary(workflow_id, db)
    stats = await get_token_stats(workflow_id, db)

    result = await db.execute(
        select(Run).where(Run.workflow_id == wf_uuid)
        .order_by(Run.created_at.desc()).limit(30)
    )
    runs = result.scalars().all()

    if not runs:
        return {"score": 0, "grade": "N/A", "message": "No runs yet — score appears after first execution", "breakdown": {}}

    spike_penalty = 20 if stats.get("cost_spike_detected") else 0
    cost_score    = max(0, 100 - spike_penalty)

    if rag:
        rag_score = (rag.get("efficiency_ratio", 0.5) * 100 + rag.get("avg_relevance_score", 0.5) * 100) / 2
    else:
        rag_score = 50

    success_count = sum(1 for r in runs if r.status == "success")
    reliability   = (success_count / len(runs)) * 100

    durations  = [r.duration_ms for r in runs if r.duration_ms]
    perf_score = max(0, 100 - (sum(durations) / len(durations) / 300)) if durations else 70

    composite = round(min(100, max(0,
        cost_score * 0.30 + rag_score * 0.30 + reliability * 0.25 + perf_score * 0.15
    )))

    grade   = "A" if composite >= 85 else "B" if composite >= 70 else "C" if composite >= 50 else "D"
    message = {
        "A": "Excellent — this workflow is highly optimized",
        "B": "Good — a few optimizations could help",
        "C": "Fair — review suggestions below",
        "D": "Needs attention — significant issues detected",
    }[grade]

    return {
        "score": composite, "grade": grade, "message": message,
        "breakdown": {
            "cost_efficiency": round(cost_score),
            "rag_quality":     round(rag_score),
            "reliability":     round(reliability),
            "performance":     round(perf_score),
        },
    }
