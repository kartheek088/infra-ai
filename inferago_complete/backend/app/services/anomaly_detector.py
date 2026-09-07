"""
Anomaly detection + timeline builder — Phase 4.

Both functions are pure read-side analytics that take data already persisted
in the DB (Run + TokenUsage + Event rows) and produce JSON for the frontend.
No new writes happen here.

Sourced from ai-observability's analyzer.py but rewritten for the ARI schema
(multi-tenant, Event rows, TokenUsage rows, node-level granularity).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import to_uuid
from app.models.event import Event
from app.models.run import Run, TokenUsage


# ── tunables ──────────────────────────────────────────────────────────────────

# Latency above this is flagged as a "latency spike" (ms)
LATENCY_SPIKE_MS = 3000

# Per-node token usage above this is a "token spike"
TOKEN_SPIKE = 500

# Idle gap (seconds) between consecutive events is flagged
IDLE_GAP_SECONDS = 2.0

# Cost multipliers relative to the workflow's rolling average that count as
# a "cost spike" (e.g. 2.0 = this run cost 2× the recent average)
COST_SPIKE_MULTIPLIER = 2.0

# Minimum number of historical runs before we can detect cost spikes
# (without history we have nothing to compare against)
COST_SPIKE_MIN_HISTORY = 5


# ── types ────────────────────────────────────────────────────────────────────

@dataclass
class TimelineStep:
    """One entry in the execution timeline — either a node or a platform event."""
    step: str
    kind: str                          # "node" | "event"
    status: str                        # "success" | "failed" | "info" | ...
    duration_ms: int | None
    tokens: int | None
    cost_usd: float | None
    timestamp: datetime | None
    error_message: str | None = None
    model: str | None = None
    provider: str | None = None
    node_type: str | None = None
    severity: str | None = None        # for events: critical | high | medium | low | info


# ── public API ────────────────────────────────────────────────────────────────

async def build_timeline(
    run_id: str,
    tenant_id: str,
    db: AsyncSession,
) -> dict:
    """
    Build a JSON-serializable timeline for one execution.

    Combines:
      • Node executions from TokenUsage rows (per-node timing, tokens, cost)
      • Structured events from the events table (lifecycle, errors, security)

    Returns a dict with execution_id, workflow_id, status, started_at,
    finished_at, duration_ms, total_cost, total_tokens, and a sorted
    `steps` list.
    """
    run_uuid = to_uuid(run_id)
    tenant_uuid = to_uuid(tenant_id)

    run = await _load_run(run_uuid, tenant_uuid, db)
    if not run:
        return _empty_timeline(run_id)

    # Nodes first (per-node detail is richer than generic events)
    node_rows = await _load_node_rows(run_uuid, tenant_uuid, db)
    event_rows = await _load_event_rows(run_uuid, tenant_uuid, db)

    steps: list[TimelineStep] = []

    for n in node_rows:
        steps.append(TimelineStep(
            step=n.node_name,
            kind="node",
            status="failed" if n.error_message else "success",
            duration_ms=n.latency_ms,
            tokens=n.total_tokens,
            cost_usd=float(n.cost_usd) if n.cost_usd is not None else None,
            timestamp=run.started_at,  # nodes don't have their own ts at row level
            error_message=n.error_message or None,
            model=n.model or None,
            provider=n.provider or None,
            node_type=n.node_type or None,
        ))

    for e in event_rows:
        # Skip synthesized events for nodes we already cover above
        if e.component == "platform_adapter" and e.operation.startswith("execution_"):
            op = e.operation
        else:
            op = e.operation

        steps.append(TimelineStep(
            step=e.operation,
            kind="event",
            status=_event_status(e),
            duration_ms=None,
            tokens=None,
            cost_usd=None,
            timestamp=e.occurred_at,
            error_message=(e.payload or {}).get("error_message"),
            model=(e.payload or {}).get("model"),
            provider=(e.payload or {}).get("provider"),
            node_type=(e.payload or {}).get("node_type"),
            severity=e.severity,
        ))

    # Stable chronological ordering — nodes with no timestamp sort to top
    steps.sort(key=lambda s: (s.timestamp is None, s.timestamp or datetime.min))

    total_cost   = sum((s.cost_usd or 0) for s in steps if s.kind == "node")
    total_tokens = sum((s.tokens or 0) for s in steps if s.kind == "node")

    return {
        "execution_id":   run.n8n_execution_id or str(run.id),
        "run_id":         str(run.id),
        "workflow_id":    str(run.workflow_id),
        "platform":       run.platform,
        "status":         run.status,
        "started_at":     run.started_at.isoformat() if run.started_at else None,
        "finished_at":    run.finished_at.isoformat() if run.finished_at else None,
        "duration_ms":    run.duration_ms,
        "total_cost":     round(total_cost, 6),
        "total_tokens":   total_tokens,
        "step_count":     len(steps),
        "steps":          [_step_to_dict(s) for s in steps],
    }


async def detect_anomalies(
    run_id: str,
    tenant_id: str,
    db: AsyncSession,
) -> list[dict]:
    """
    Anomaly list for one execution — pure read.

    Each anomaly is a dict with:
      • kind:   "latency_spike" | "token_spike" | "node_failed" |
                "idle_gap" | "cost_spike" | "execution_failed"
      • step:   node name or event operation
      • detail: human-readable explanation
      • severity: "low" | "medium" | "high"

    Cost-spike detection uses the workflow's rolling average (excluding the
    current run) so a single expensive run doesn't poison its own baseline.
    """
    run_uuid = to_uuid(run_id)
    tenant_uuid = to_uuid(tenant_id)

    run = await _load_run(run_uuid, tenant_uuid, db)
    if not run:
        return []

    anomalies: list[dict] = []

    # 1) Execution-level failure
    if run.status in ("failed", "error"):
        anomalies.append({
            "kind":     "execution_failed",
            "step":     "execution",
            "detail":   f"Execution ended with status '{run.status}'",
            "severity": "high",
        })

    # 2) Node-level anomalies
    node_rows = await _load_node_rows(run_uuid, tenant_uuid, db)
    for n in node_rows:
        if n.error_message:
            anomalies.append({
                "kind":     "node_failed",
                "step":     n.node_name,
                "detail":   f"Node failed: {n.error_message[:200]}",
                "severity": "high",
            })
        if n.latency_ms and n.latency_ms > LATENCY_SPIKE_MS:
            anomalies.append({
                "kind":     "latency_spike",
                "step":     n.node_name,
                "detail":   f"Latency {n.latency_ms}ms exceeds {LATENCY_SPIKE_MS}ms threshold",
                "severity": "medium" if n.latency_ms < LATENCY_SPIKE_MS * 2 else "high",
            })
        if n.total_tokens and n.total_tokens > TOKEN_SPIKE:
            anomalies.append({
                "kind":     "token_spike",
                "step":     n.node_name,
                "detail":   f"Used {n.total_tokens} tokens (threshold {TOKEN_SPIKE})",
                "severity": "medium",
            })

    # 3) Idle-gap detection — only meaningful when we have ≥2 ordered events
    event_rows = await _load_event_rows(run_uuid, tenant_uuid, db)
    ordered = sorted(
        [e for e in event_rows if e.occurred_at is not None],
        key=lambda e: e.occurred_at,
    )
    for prev, curr in zip(ordered, ordered[1:]):
        gap = (curr.occurred_at - prev.occurred_at).total_seconds()
        if gap > IDLE_GAP_SECONDS:
            anomalies.append({
                "kind":     "idle_gap",
                "step":     curr.operation,
                "detail":   f"{gap:.1f}s idle gap before '{curr.operation}'",
                "severity": "low",
            })

    # 4) Cost-spike vs. rolling average of prior runs on the same workflow
    history_avg = await _rolling_avg_cost(run.workflow_id, exclude_run_id=run.id, db=db)
    run_cost = sum(float(n.cost_usd or 0) for n in node_rows)
    if history_avg is not None and history_avg > 0 and run_cost > history_avg * COST_SPIKE_MULTIPLIER:
        anomalies.append({
            "kind":     "cost_spike",
            "step":     "execution",
            "detail":   (
                f"Cost ${run_cost:.4f} is "
                f"{run_cost / history_avg:.1f}× the recent average "
                f"(${history_avg:.4f})"
            ),
            "severity": "medium" if run_cost < history_avg * 4 else "high",
        })

    # Stable order: severity desc, then step asc
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    anomalies.sort(key=lambda a: (severity_rank.get(a["severity"], 9), a["step"]))

    return anomalies


# ── helpers ──────────────────────────────────────────────────────────────────

async def _load_run(run_uuid, tenant_uuid, db: AsyncSession) -> Run | None:
    result = await db.execute(
        select(Run).where(Run.id == run_uuid, Run.tenant_id == tenant_uuid)
    )
    return result.scalar_one_or_none()


async def _load_node_rows(run_uuid, tenant_uuid, db: AsyncSession) -> list[TokenUsage]:
    result = await db.execute(
        select(TokenUsage)
        .where(TokenUsage.run_id == run_uuid, TokenUsage.tenant_id == tenant_uuid)
        .order_by(TokenUsage.node_name)
    )
    return list(result.scalars().all())


async def _load_event_rows(run_uuid, tenant_uuid, db: AsyncSession) -> list[Event]:
    result = await db.execute(
        select(Event)
        .where(Event.run_id == run_uuid, Event.tenant_id == tenant_uuid)
        .order_by(Event.occurred_at)
    )
    return list(result.scalars().all())


async def _rolling_avg_cost(
    workflow_id, exclude_run_id, db: AsyncSession, limit: int = 30
) -> float | None:
    """Average cost of the most recent N runs before the current one."""
    result = await db.execute(
        select(Run.cost_usd)
        .where(
            Run.workflow_id == workflow_id,
            Run.id != exclude_run_id,
        )
        .order_by(Run.created_at.desc())
        .limit(limit)
    )
    costs: list[float] = [float(c) for c in result.scalars().all() if c is not None]
    if len(costs) < COST_SPIKE_MIN_HISTORY:
        return None
    return sum(costs) / len(costs)


def _event_status(e: Event) -> str:
    if e.event_type == "execution.failed" or e.severity == "error":
        return "failed"
    if e.event_type in ("execution.completed",):
        return "success"
    return e.severity or "info"


def _step_to_dict(s: TimelineStep) -> dict:
    return {
        "step":          s.step,
        "kind":          s.kind,
        "status":        s.status,
        "duration_ms":   s.duration_ms,
        "tokens":        s.tokens,
        "cost_usd":      s.cost_usd,
        "timestamp":     s.timestamp.isoformat() if s.timestamp else None,
        "error_message": s.error_message,
        "model":         s.model,
        "provider":      s.provider,
        "node_type":     s.node_type,
        "severity":      s.severity,
    }


def _empty_timeline(run_id: str) -> dict:
    return {
        "execution_id": None,
        "run_id":       run_id,
        "workflow_id":  None,
        "platform":     None,
        "status":       "not_found",
        "started_at":   None,
        "finished_at":  None,
        "duration_ms":  None,
        "total_cost":   0.0,
        "total_tokens": 0,
        "step_count":   0,
        "steps":        [],
    }


# ── sync helpers (kept for tests / non-async callers) ────────────────────────

def detect_anomalies_sync(steps: Iterable[TimelineStep]) -> list[dict]:
    """
    Pure-function variant of `detect_anomalies` that operates on already-loaded
    timeline steps. Used by unit tests and by callers that want to re-detect
    anomalies over an in-memory timeline.
    """
    anomalies: list[dict] = []
    steps_list = list(steps)

    for s in steps_list:
        if s.kind == "node":
            if s.error_message:
                anomalies.append({
                    "kind": "node_failed", "step": s.step,
                    "detail": f"Node failed: {s.error_message[:200]}",
                    "severity": "high",
                })
            if s.duration_ms and s.duration_ms > LATENCY_SPIKE_MS:
                anomalies.append({
                    "kind": "latency_spike", "step": s.step,
                    "detail": f"Latency {s.duration_ms}ms exceeds {LATENCY_SPIKE_MS}ms threshold",
                    "severity": "medium" if s.duration_ms < LATENCY_SPIKE_MS * 2 else "high",
                })
            if s.tokens and s.tokens > TOKEN_SPIKE:
                anomalies.append({
                    "kind": "token_spike", "step": s.step,
                    "detail": f"Used {s.tokens} tokens (threshold {TOKEN_SPIKE})",
                    "severity": "medium",
                })

    ordered = [s for s in steps_list if s.timestamp is not None]
    ordered.sort(key=lambda s: s.timestamp)
    for prev, curr in zip(ordered, ordered[1:]):
        gap = (curr.timestamp - prev.timestamp).total_seconds()
        if gap > IDLE_GAP_SECONDS:
            anomalies.append({
                "kind": "idle_gap", "step": curr.step,
                "detail": f"{gap:.1f}s idle gap before '{curr.step}'",
                "severity": "low",
            })

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    anomalies.sort(key=lambda a: (severity_rank.get(a["severity"], 9), a["step"]))
    return anomalies
