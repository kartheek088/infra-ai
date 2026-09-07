"""
n8n adapter — captures all 17 n8n event types and all node executions.

n8n webhook payload highlights:
  executionLifecycleEvents  → ExecutionEvent list
  data.resultData.runData  → per-node execution details (timing, error, tokens)
  data.resultData.errorData → execution-level error

Node types are inferred from n8n node class names:
  AiNode             → llm
  HttpRequestNode    → http_request
  ScheduleTrigger    → trigger
  Webhook            → trigger
  CodeNode           → transform
  IfNode / SwitchNode → logic
  Default            → other
"""
from datetime import datetime
from app.adapters.base_adapter import StandardExecution, NodeExecution, ExecutionEvent
from app.services.token_parser import parse_node_tokens, calculate_cost, calculate_run_duration


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return None


def _node_type_from_class(node_class: str | None) -> str:
    """Infer node_type from n8n node class name."""
    if not node_class:
        return "other"
    c = node_class.lower()
    if "ainode" in c or "aiform" in c or "aitext" in c or "lm" in c:
        return "llm"
    if "httprequest" in c:
        return "http_request"
    if "trigger" in c or "webhook" in c or "schedule" in c:
        return "trigger"
    if "code" in c:
        return "transform"
    if "if" in c or "switch" in c or "condition" in c:
        return "logic"
    if "set" in c or "edit" in c or "convert" in c or "split" in c:
        return "data"
    return "other"


def _provider_from_model(model: str | None) -> str:
    """Infer provider from model name."""
    if not model:
        return "unknown"
    m = model.lower()
    if "gpt" in m or "o1" in m or "o3" in m:
        return "openai"
    if "claude" in m or "anthropic" in m:
        return "anthropic"
    if "gemini" in m or "google" in m:
        return "google"
    if "azure" in m or "azure_openai" in m:
        return "azure"
    if "mistral" in m:
        return "mistral"
    if "cohere" in m:
        return "cohere"
    return "custom"


def _extract_error(node_run: dict) -> str:
    """Pull error message from a node run if present."""
    error_data = node_run.get("error", {})
    if isinstance(error_data, dict):
        return error_data.get("message", error_data.get("name", ""))
    if isinstance(error_data, str):
        return error_data
    return ""


# ── lifecycle events ───────────────────────────────────────────────────────────

def _parse_lifecycle_events(payload: dict) -> list[ExecutionEvent]:
    """
    Parse executionLifecycleEvents from n8n webhook payload.
    These cover: execution_triggered, node_started, node_finished,
    execution_finished, execution_failed, etc.
    """
    events: list[ExecutionEvent] = []
    raw_events = payload.get("executionLifecycleEvents") or []

    for ev in raw_events:
        raw_ts = ev.get("timestamp")
        event_type = ev.get("event", "unknown")
        events.append(ExecutionEvent(
            event_type=event_type,
            timestamp=_parse_dt(raw_ts),
            node_name=ev.get("nodeName"),
            source=ev.get("source"),
            message=ev.get("message"),
            metadata={k: v for k, v in ev.items()
                      if k not in ("event", "timestamp", "nodeName", "source", "message")},
        ))

    # If no lifecycle events array, synthesize top-level status events
    if not events:
        status = payload.get("status", "unknown")
        started_raw = payload.get("startedAt")
        stopped_raw = payload.get("stoppedAt")

        if started_raw:
            events.append(ExecutionEvent(
                event_type="execution_triggered",
                timestamp=_parse_dt(started_raw),
                source=payload.get("mode"),
            ))
        if status in ("success", "finished"):
            ts = stopped_raw or started_raw
            events.append(ExecutionEvent(
                event_type="execution_finished",
                timestamp=_parse_dt(ts),
            ))
        elif status in ("error", "failed"):
            ts = stopped_raw or started_raw
            events.append(ExecutionEvent(
                event_type="execution_failed",
                timestamp=_parse_dt(ts),
                message=payload.get("data", {}).get("errorData", {}).get("message", "Execution failed"),
            ))

    return events


# ── node executions ────────────────────────────────────────────────────────────

def _parse_all_nodes(payload: dict) -> list[NodeExecution]:
    """
    Parse ALL nodes from runData, not just LLM nodes.
    Each node run carries timing, error, and (optionally) token data.
    """
    nodes: list[NodeExecution] = []
    run_data = (
        payload.get("data", {})
        .get("resultData", {})
        .get("runData", {})
    )
    node_variants = payload.get("data", {}).get("variantData", {}).get("nodeVariantData", {})

    for node_name, node_runs in run_data.items():
        if not node_runs:
            continue

        # Use first run for metadata; aggregate tokens across runs
        first_run = node_runs[0] if isinstance(node_runs, list) else node_runs
        node_class = first_run.get("type")
        error_msg = _extract_error(first_run)
        execution_time_ms = first_run.get("executionTime")

        # Try token parsing (LLM nodes)
        token_data = parse_node_tokens(node_name, node_runs) if isinstance(node_runs, list) else None

        if token_data:
            model = token_data["model"]
        else:
            model = first_run.get("data", {}).get("main", [[{}]])[0][0].get("json", {}).get("model", "")

        provider = _provider_from_model(model)
        node_type = "llm" if token_data else _node_type_from_class(node_class)

        # Aggregate tokens across multiple runs
        total_prompt = 0
        total_completion = 0
        total_cost = 0.0
        for nr in (node_runs if isinstance(node_runs, list) else [node_runs]):
            td = parse_node_tokens(node_name, [nr]) if isinstance(node_runs, list) else None
            if td:
                total_prompt += td["prompt_tokens"]
                total_completion += td["completion_tokens"]
                total_cost += td["cost_usd"]
        total_tokens = total_prompt + total_completion

        # Determine event type
        event_type = "node_finished"
        if error_msg:
            event_type = "node_failed"
        elif first_run.get("sourceData"):
            event_type = "node_started"

        nodes.append(NodeExecution(
            node_name=node_name,
            node_type=node_type,
            model=model,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            total_tokens=total_tokens,
            cost_usd=round(total_cost, 8),
            event_type=event_type,
            provider=provider,
            error_message=error_msg,
            latency_ms=int(execution_time_ms) if execution_time_ms else None,
            metadata={
                "node_class": node_class,
                "runs_count": len(node_runs) if isinstance(node_runs, list) else 1,
                "output": str(first_run.get("data", {}).get("main", [[{}]])[0][0].get("json", {})) if not error_msg else "",
            },
        ))

    return nodes


# ── adapter ───────────────────────────────────────────────────────────────────

class N8NAdapter:
    platform = "n8n"

    @staticmethod
    def normalize(payload: dict) -> StandardExecution:
        started_raw = payload.get("startedAt")
        stopped_raw = payload.get("stoppedAt")

        return StandardExecution(
            platform="n8n",
            execution_id=str(
                payload.get("executionId") or payload.get("id") or ""
            ),
            workflow_id=str(
                payload.get("workflowId") or payload.get("workflowData", {}).get("id") or ""
            ),
            status=payload.get("status", "unknown"),
            triggered_by=payload.get("mode", "unknown"),
            started_at=_parse_dt(started_raw),
            finished_at=_parse_dt(stopped_raw),
            duration_ms=calculate_run_duration(started_raw, stopped_raw),
            nodes=_parse_all_nodes(payload),
            events=_parse_lifecycle_events(payload),
        )
