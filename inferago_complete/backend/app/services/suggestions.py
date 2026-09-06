from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dataclasses import dataclass
from enum import Enum
from app.models.run import Run, TokenUsage
from app.services.rag_analyzer import get_rag_summary
from app.core.utils import to_uuid


class Impact(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


@dataclass
class Suggestion:
    type: str
    impact: Impact
    title: str
    description: str
    estimated_saving: str
    action: str


async def get_token_stats(workflow_id: str, db: AsyncSession) -> dict:
    """Compute token + cost statistics for a workflow (last 30 runs)."""
    wf_uuid = to_uuid(workflow_id)
    result = await db.execute(
        select(Run).where(Run.workflow_id == wf_uuid)
        .order_by(Run.created_at.desc()).limit(30)
    )
    runs = result.scalars().all()
    if not runs:
        return {}

    run_ids      = [r.id for r in runs]
    token_result = await db.execute(select(TokenUsage).where(TokenUsage.run_id.in_(run_ids)))
    tokens       = token_result.scalars().all()
    if not tokens:
        return {}

    costs_per_run  = {}
    tokens_per_run = {}
    for t in tokens:
        rid = str(t.run_id)
        costs_per_run[rid]  = costs_per_run.get(rid, 0)  + t.cost_usd
        tokens_per_run[rid] = tokens_per_run.get(rid, 0) + t.total_tokens

    cost_values    = list(costs_per_run.values())
    token_values   = list(tokens_per_run.values())
    avg_run_cost   = sum(cost_values)  / len(cost_values)
    avg_run_tokens = sum(token_values) / len(token_values)
    max_run_cost   = max(cost_values)
    max_run_tokens = max(token_values)

    spike_detected = max_run_cost   > avg_run_cost   * 2.5
    token_spike    = max_run_tokens > avg_run_tokens  * 3.0

    # Loop detection — unusually long duration spikes
    durations        = [r.duration_ms for r in runs if r.duration_ms]
    avg_duration     = sum(durations) / len(durations) if durations else 0
    max_duration     = max(durations) if durations else 0
    loop_suspected   = max_duration > avg_duration * 5 and max_duration > 30_000  # 30s+

    # Error rate
    failed_runs = sum(1 for r in runs if r.status == "failed")
    error_rate  = failed_runs / len(runs)

    return {
        "avg_cost_per_run":         round(avg_run_cost, 6),
        "daily_cost_estimate":      round(avg_run_cost * len(runs) / 30, 4),
        "cost_spike_detected":      spike_detected,
        "token_spike_detected":     token_spike,
        "loop_suspected":           loop_suspected,
        "avg_duration_ms":          round(avg_duration),
        "max_duration_ms":          max_duration,
        "error_rate":               round(error_rate, 3),
        "failed_runs":              failed_runs,
        "avg_prompt_tokens":        round(sum(t.prompt_tokens for t in tokens) / len(tokens)),
        "avg_completion_tokens":    round(sum(t.completion_tokens for t in tokens) / len(tokens)),
        "avg_system_prompt_tokens": round(sum(t.prompt_tokens for t in tokens) / len(tokens) * 0.6),
    }


async def generate_suggestions(workflow_id: str, db: AsyncSession) -> list[Suggestion]:
    """
    Rules-based optimization engine.
    Analyzes token usage, RAG metrics, run history and generates
    ranked, actionable suggestions with estimated savings.
    """
    suggestions = []
    rag         = await get_rag_summary(workflow_id, db)
    stats       = await get_token_stats(workflow_id, db)
    daily       = stats.get("daily_cost_estimate", 0)

    # ── Rule 1: RAG top_k too high ────────────────────────────────────
    if rag and rag.get("efficiency_ratio", 1) < 0.4:
        r = rag["avg_chunks_retrieved"]
        u = rag["avg_chunks_used"]
        suggestions.append(Suggestion(
            type="rag_top_k", impact=Impact.HIGH,
            title=f"Reduce top_k from {int(r)} → {max(1, int(u)+1)}",
            description=(
                f"You retrieve {int(r)} chunks on average but only use {int(u)}. "
                f"Cutting top_k saves ~{int((1-u/r)*100)}% of RAG tokens."
            ),
            estimated_saving=f"~${round(daily*0.35, 2)}/day",
            action=f"Set top_k = {max(1, int(u)+1)} in your retrieval node",
        ))

    # ── Rule 2: System prompt too large ──────────────────────────────
    if stats.get("avg_system_prompt_tokens", 0) > 400:
        suggestions.append(Suggestion(
            type="prompt_cache", impact=Impact.HIGH,
            title="Cache your system prompt",
            description=(
                "Your system prompt is large and resent on every run. "
                "Prompt caching eliminates this repeated cost instantly."
            ),
            estimated_saving=f"~${round(daily*0.25, 2)}/day",
            action="Enable prompt caching in your LLM node settings",
        ))

    # ── Rule 3: Low context fill ──────────────────────────────────────
    if rag and rag.get("avg_context_fill_pct", 100) < 40:
        suggestions.append(Suggestion(
            type="chunk_size", impact=Impact.MEDIUM,
            title="Increase chunk size — context window underused",
            description=(
                f"Only {rag['avg_context_fill_pct']:.0f}% of your context window is used. "
                "Larger chunks give the model richer context at the same token cost."
            ),
            estimated_saving="Better quality, same cost",
            action="Increase chunk size from 256 → 512 tokens in your vector store",
        ))

    # ── Rule 4: Cost spike ────────────────────────────────────────────
    if stats.get("cost_spike_detected"):
        suggestions.append(Suggestion(
            type="cost_spike", impact=Impact.HIGH,
            title="Unusual cost spike detected",
            description=(
                "A recent run cost 2.5x your average. This often indicates "
                "unexpectedly large input, a misconfigured node, or a runaway loop."
            ),
            estimated_saving="Prevent budget overrun",
            action="Review recent run history — check input size and node outputs",
        ))

    # ── Rule 5: Token spike ───────────────────────────────────────────
    if stats.get("token_spike_detected"):
        suggestions.append(Suggestion(
            type="token_spike", impact=Impact.HIGH,
            title="Token spike detected — 3x above average",
            description=(
                "One or more runs consumed 3x the average token count. "
                "This could be caused by an unexpectedly large document, "
                "recursive calls, or a loop in your workflow."
            ),
            estimated_saving="Prevent runaway costs",
            action="Add a max_tokens limit or input size validation to your workflow",
        ))

    # ── Rule 6: Loop detection ────────────────────────────────────────
    if stats.get("loop_suspected"):
        avg_s = stats["avg_duration_ms"] / 1000
        max_s = stats["max_duration_ms"] / 1000
        suggestions.append(Suggestion(
            type="loop_detection", impact=Impact.HIGH,
            title="Possible infinite loop detected",
            description=(
                f"One run took {max_s:.0f}s — that's 5x your average of {avg_s:.0f}s. "
                "This pattern typically indicates a recursive loop, retry storm, "
                "or a workflow waiting indefinitely for a response."
            ),
            estimated_saving="Prevent runaway executions",
            action=(
                "Add a loop counter or timeout to your workflow. "
                "Check for recursive agent calls or unbounded retry logic."
            ),
        ))

    # ── Rule 7: High error rate ───────────────────────────────────────
    if stats.get("error_rate", 0) > 0.15:
        rate = stats["error_rate"] * 100
        suggestions.append(Suggestion(
            type="error_rate", impact=Impact.HIGH,
            title=f"High failure rate — {rate:.0f}% of runs failing",
            description=(
                f"{rate:.0f}% of your recent runs have failed. "
                "Every failed run still consumes tokens up to the point of failure. "
                "Fixing the root cause will save both cost and reliability."
            ),
            estimated_saving=f"~${round(daily * stats['error_rate'], 2)}/day wasted on failed runs",
            action="Check your error logs — look for API timeouts, invalid inputs, or rate limits",
        ))

    # ── Rule 8: Cheaper model opportunity ────────────────────────────
    if stats.get("avg_completion_tokens", 500) < 150 and daily > 0.05:
        suggestions.append(Suggestion(
            type="model_downgrade", impact=Impact.MEDIUM,
            title="Switch to a lighter model",
            description=(
                f"Your average completion is only {int(stats['avg_completion_tokens'])} tokens. "
                "For short outputs, GPT-4o-mini or Claude Haiku delivers similar quality "
                "at 10x lower cost."
            ),
            estimated_saving=f"~${round(daily*0.6, 2)}/day",
            action="Try GPT-4o-mini or Claude Haiku for this workflow",
        ))

    # ── Rule 9: Low relevance scores ─────────────────────────────────
    if rag and rag.get("avg_relevance_score", 1) < 0.5:
        suggestions.append(Suggestion(
            type="embedding_quality", impact=Impact.MEDIUM,
            title="Low RAG relevance scores detected",
            description=(
                f"Average chunk relevance is {rag['avg_relevance_score']:.2f}/1.0. "
                "Low relevance means retrieved chunks aren't helping the model — "
                "you're paying for noise that reduces answer quality."
            ),
            estimated_saving="Better quality + lower waste",
            action="Review your embedding model, chunking strategy, or query preprocessing",
        ))

    # Sort by impact: HIGH → MEDIUM → LOW
    order = {Impact.HIGH: 0, Impact.MEDIUM: 1, Impact.LOW: 2}
    return sorted(suggestions, key=lambda s: order[s.impact])


async def detect_unused_nodes(workflow_id: str, db: AsyncSession) -> list[dict]:
    """
    Detect nodes that consistently use 0 tokens — potentially unused or misconfigured.
    Returns list of node names with their token counts.
    """
    wf_uuid = to_uuid(workflow_id)
    result = await db.execute(
        select(Run).where(Run.workflow_id == wf_uuid)
        .order_by(Run.created_at.desc()).limit(20)
    )
    runs = result.scalars().all()
    if not runs:
        return []

    run_ids = [r.id for r in runs]
    token_result = await db.execute(
        select(TokenUsage).where(TokenUsage.run_id.in_(run_ids))
    )
    tokens = token_result.scalars().all()

    node_stats: dict = {}
    for t in tokens:
        n = t.node_name
        if n not in node_stats:
            node_stats[n] = {"total_tokens": 0, "appearances": 0, "total_cost": 0.0}
        node_stats[n]["total_tokens"]  += t.total_tokens
        node_stats[n]["appearances"]   += 1
        node_stats[n]["total_cost"]    += t.cost_usd

    unused = [
        {
            "node_name":    name,
            "appearances":  stats["appearances"],
            "avg_tokens":   stats["total_tokens"] / stats["appearances"],
            "total_cost":   round(stats["total_cost"], 6),
            "warning":      "This node uses very few tokens — verify it is working correctly",
        }
        for name, stats in node_stats.items()
        if stats["appearances"] > 0 and (stats["total_tokens"] / stats["appearances"]) < 10
    ]

    return unused


async def detect_redundant_retrievals(workflow_id: str, db: AsyncSession) -> dict:
    """
    Detect if the same queries are being retrieved repeatedly.
    High chunk retrieval with low variation = caching opportunity.
    """
    from app.models.rag import RAGMetrics
    wf_uuid = to_uuid(workflow_id)

    result = await db.execute(
        select(RAGMetrics).where(RAGMetrics.workflow_id == wf_uuid)
        .order_by(RAGMetrics.recorded_at.desc()).limit(20)
    )
    metrics = result.scalars().all()
    if len(metrics) < 3:
        return {"redundant_detected": False}

    # Low variance in chunks retrieved = same queries every time
    retrieval_counts = [m.chunks_retrieved for m in metrics]
    avg = sum(retrieval_counts) / len(retrieval_counts)
    variance = sum((x - avg) ** 2 for x in retrieval_counts) / len(retrieval_counts)

    redundant = variance < 1.0 and avg > 3

    return {
        "redundant_detected":    redundant,
        "avg_chunks_retrieved":  round(avg, 2),
        "retrieval_variance":    round(variance, 3),
        "recommendation":        (
            "Low variance in chunk retrieval suggests repeated identical queries. "
            "Consider caching retrieval results for common queries."
        ) if redundant else "No redundant retrieval pattern detected",
    }
