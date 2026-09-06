from datetime import datetime
from app.adapters.base_adapter import StandardExecution, NodeExecution
from app.services.token_parser import parse_node_tokens, calculate_run_duration


class N8NAdapter:
    platform = "n8n"

    @staticmethod
    def normalize(payload: dict) -> StandardExecution:
        def parse_dt(raw):
            if not raw:
                return None
            try:
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except Exception:
                return None

        started_raw = payload.get("startedAt")
        stopped_raw = payload.get("stoppedAt")
        nodes = []

        run_data = (
            payload.get("data", {})
            .get("resultData", {})
            .get("runData", {})
        )
        for node_name, node_runs in run_data.items():
            token_data = parse_node_tokens(node_name, node_runs)
            if token_data:
                nodes.append(NodeExecution(
                    node_name=token_data["node_name"],
                    node_type="llm",
                    model=token_data["model"],
                    prompt_tokens=token_data["prompt_tokens"],
                    completion_tokens=token_data["completion_tokens"],
                    total_tokens=token_data["total_tokens"],
                    cost_usd=token_data["cost_usd"],
                ))

        return StandardExecution(
            platform="n8n",
            execution_id=str(payload.get("executionId") or payload.get("id") or ""),
            workflow_id=str(payload.get("workflowId") or payload.get("workflowData", {}).get("id") or ""),
            status=payload.get("status", "unknown"),
            triggered_by=payload.get("mode", "unknown"),
            started_at=parse_dt(started_raw),
            finished_at=parse_dt(stopped_raw),
            duration_ms=calculate_run_duration(started_raw, stopped_raw),
            nodes=nodes,
        )
