from datetime import datetime
from app.adapters.base_adapter import StandardExecution, NodeExecution, ExecutionEvent
from app.services.token_parser import calculate_cost


class CustomAdapter:
    platform = "custom"

    @staticmethod
    def normalize(payload: dict) -> StandardExecution:
        def parse_dt(raw):
            if not raw:
                return None
            if isinstance(raw, datetime):
                return raw
            try:
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except Exception:
                return None

        nodes = []
        for node in payload.get("nodes", []):
            prompt     = node.get("prompt_tokens", 0)
            completion = node.get("completion_tokens", 0)
            model      = node.get("model", "unknown")
            output = node.get("output") or node.get("response") or ""
            if output:
                metadata = {"output": output}
            else:
                metadata = {}

            nodes.append(NodeExecution(
                node_name=node.get("node_name", "Unknown Node"),
                node_type=node.get("node_type", "llm"),
                model=model,
                prompt_tokens=prompt,
                completion_tokens=completion,
                total_tokens=node.get("total_tokens", prompt + completion),
                cost_usd=node.get("cost_usd") or calculate_cost(model, prompt, completion),
                metadata=metadata if metadata else None,
            ))

        started_at  = parse_dt(payload.get("started_at"))
        finished_at = parse_dt(payload.get("finished_at"))
        duration_ms = payload.get("duration_ms")
        if not duration_ms and started_at and finished_at:
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        return StandardExecution(
            platform="custom",
            execution_id=str(payload.get("execution_id") or ""),
            workflow_id=str(payload.get("workflow_id") or ""),
            status=payload.get("status", "success"),
            triggered_by=payload.get("triggered_by", "unknown"),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            nodes=nodes,
            events=[],
        )
