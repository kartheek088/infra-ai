from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rag import RAGMetrics
from app.core.utils import to_uuid


async def get_rag_summary(workflow_id: str, db: AsyncSession) -> dict:
    wf_uuid = to_uuid(workflow_id)
    result = await db.execute(
        select(RAGMetrics)
        .where(RAGMetrics.workflow_id == wf_uuid)
        .order_by(RAGMetrics.recorded_at.desc())
        .limit(30)
    )
    metrics = result.scalars().all()
    if not metrics:
        return {}

    count        = len(metrics)
    avg_ret      = sum(m.chunks_retrieved for m in metrics) / count
    avg_used     = sum(m.chunks_used for m in metrics) / count
    efficiency   = avg_used / avg_ret if avg_ret > 0 else 0

    return {
        "workflow_id":          workflow_id,
        "avg_chunks_retrieved": round(avg_ret, 2),
        "avg_chunks_used":      round(avg_used, 2),
        "avg_context_fill_pct": round(sum(m.context_fill_pct for m in metrics) / count, 2),
        "avg_relevance_score":  round(sum(m.avg_relevance_score for m in metrics) / count, 3),
        "efficiency_ratio":     round(efficiency, 3),
        "duplicate_rate":       round(sum(1 for m in metrics if m.has_duplicates) / count, 3),
        "total_runs_analyzed":  count,
    }


async def get_rag_efficiency_trend(workflow_id: str, db: AsyncSession) -> list:
    wf_uuid = to_uuid(workflow_id)
    result = await db.execute(
        select(RAGMetrics)
        .where(RAGMetrics.workflow_id == wf_uuid)
        .order_by(RAGMetrics.recorded_at.desc())
        .limit(20)
    )
    metrics = result.scalars().all()
    return [
        {
            "run_id":         str(m.run_id),
            "retrieved":      m.chunks_retrieved,
            "used":           m.chunks_used,
            "efficiency_pct": round((m.chunks_used / m.chunks_retrieved * 100) if m.chunks_retrieved > 0 else 0, 1),
            "relevance":      m.avg_relevance_score,
            "date":           m.recorded_at.isoformat(),
        }
        for m in reversed(metrics)
    ]
