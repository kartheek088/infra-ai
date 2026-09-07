"""
OpenRouter AI explanation client — Phase 8.

The client explains an execution's risk, anomalies, and security findings.
It does NOT compute or modify the authoritative risk score — that always
comes from the DB. The LLM is a *narrator*, not a judge.

Behavior contract:
  • `explain_execution(...)` returns (text, ok) — text is None on failure
  • Never raises into the caller — all network / parse errors are caught
  • Uses httpx.AsyncClient with a short timeout so webhook background tasks
    can't hang
  • If OPENROUTER_API_KEY is unset, returns (None, False) immediately
  • The prompt is bounded: we summarize, never dump raw events/JSON

The model is configured by `OPENROUTER_MODEL` (default anthropic/claude-3-haiku).
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


OPENROUTER_URL    = "https://openrouter.ai/api/v1/chat/completions"
HTTP_TIMEOUT_S    = 25.0
MAX_COMPLETION    = 600   # tokens — keeps the explanation short and snappy


# ── public API ────────────────────────────────────────────────────────────────

async def explain_execution(
    *,
    run_status: str,
    platform: str,
    duration_ms: int | None,
    total_cost: float,
    total_tokens: int,
    node_count: int,
    failed_node_count: int,
    anomalies: list[dict],
    findings: list[dict],
    top_nodes: list[dict],
) -> tuple[str | None, bool]:
    """
    Generate a human-readable explanation of the execution.

    Returns (text, ok). When ok=False, text is None and the caller should
    leave ai_explanation as NULL on the Run row.
    """
    if not settings.OPENROUTER_API_KEY:
        logger.info("OPENROUTER_API_KEY not configured — skipping AI explanation")
        return None, False

    payload = _build_payload(
        run_status=run_status,
        platform=platform,
        duration_ms=duration_ms,
        total_cost=total_cost,
        total_tokens=total_tokens,
        node_count=node_count,
        failed_node_count=failed_node_count,
        anomalies=anomalies,
        findings=findings,
        top_nodes=top_nodes,
    )

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as client:
            resp = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type":  "application/json",
                    # Recommended by OpenRouter for attribution
                    "HTTP-Referer":  "https://ari.local",
                    "X-Title":       "ARI — AI Runtime Intelligence",
                },
                json={
                    "model":       settings.OPENROUTER_MODEL,
                    "max_tokens":  MAX_COMPLETION,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": _system_prompt()},
                        {"role": "user",   "content": payload},
                    ],
                },
            )
    except httpx.HTTPError as exc:
        logger.warning("OpenRouter request failed: %s", exc)
        return None, False

    if resp.status_code != 200:
        logger.warning(
            "OpenRouter returned %s: %s", resp.status_code, resp.text[:200]
        )
        return None, False

    try:
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("OpenRouter response parse failed: %s", exc)
        return None, False

    return text, True


# ── prompt construction ───────────────────────────────────────────────────────

def _system_prompt() -> str:
    return (
        "You are an SRE assistant explaining one AI-workflow execution for the "
        "ARI observability platform. You DO NOT compute risk scores — risk is "
        "authoritative in the database. You only describe what already happened.\n\n"
        "Be specific, short, and actionable. Use plain English. If everything looks "
        "normal, say so plainly. Do not invent data. If something looks anomalous, "
        "explain the likely cause. Max 200 words."
    )


def _build_payload(
    *,
    run_status: str,
    platform: str,
    duration_ms: int | None,
    total_cost: float,
    total_tokens: int,
    node_count: int,
    failed_node_count: int,
    anomalies: list[dict],
    findings: list[dict],
    top_nodes: list[dict],
) -> str:
    lines: list[str] = []
    lines.append(f"Platform:       {platform}")
    lines.append(f"Status:         {run_status}")
    lines.append(f"Duration:       {duration_ms} ms" if duration_ms is not None else "Duration:       (unknown)")
    lines.append(f"Nodes:          {node_count}  ({failed_node_count} failed)")
    lines.append(f"Total tokens:   {total_tokens:,}")
    lines.append(f"Total cost:     ${total_cost:.4f}")

    if top_nodes:
        lines.append("\nTop nodes by cost:")
        for n in top_nodes[:5]:
            name     = n.get("node_name", "?")
            model    = n.get("model") or "(no model)"
            cost     = float(n.get("cost_usd") or 0)
            tokens   = int(n.get("total_tokens") or 0)
            latency  = n.get("latency_ms")
            latency_s = f"{int(latency)} ms" if latency is not None else "n/a"
            err      = n.get("error_message") or ""
            err_s    = f"  ERR={err[:80]}" if err else ""
            lines.append(f"  • {name} [{model}] cost=${cost:.4f} tokens={tokens:,} latency={latency_s}{err_s}")

    if anomalies:
        lines.append(f"\nAnomalies detected ({len(anomalies)}):")
        for a in anomalies[:8]:
            kind     = a.get("kind", "?")
            step     = a.get("step", "?")
            detail   = a.get("detail", "")
            severity = a.get("severity", "")
            lines.append(f"  - [{severity}] {kind} on '{step}': {detail}")

    if findings:
        lines.append(f"\nSecurity findings ({len(findings)}):")
        for f in findings[:6]:
            det    = f.get("detector_id", "?")
            sev    = f.get("severity", "?")
            score  = f.get("risk_score")
            score_s = f" (risk={score})" if score is not None else ""
            node   = f.get("node_name") or "execution-level"
            lines.append(f"  - [{sev}{score_s}] {det} on '{node}'")

    lines.append(
        "\nExplain in 2-4 short paragraphs: what happened, what stands out, "
        "and what an operator should look at first. Be specific to the data above."
    )
    return "\n".join(lines)


# ── prompt helpers (for tests) ────────────────────────────────────────────────

def _truncate(s: str | None, n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[: n - 1] + "…"


def _safe_float(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(v: Any) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0
