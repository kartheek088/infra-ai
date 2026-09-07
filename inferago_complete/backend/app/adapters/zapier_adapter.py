from datetime import datetime
from app.adapters.base_adapter import StandardExecution, NodeExecution, ExecutionEvent
from app.services.token_parser import calculate_cost


class ZapierAdapter:
    platform = "zapier"

    @staticmethod
    def normalize(payload: dict) -> StandardExecution:
        def parse_dt(raw):
            if not raw:
                return None
            try:
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except Exception:
                return None

        nodes = []
        for step in payload.get("steps", []) or payload.get("actions", []):
            app = step.get("app", "").lower()
            if any(x in app for x in ["openai", "anthropic", "ai", "chatgpt"]):
                usage      = step.get("usage", {}) or {}
                prompt     = usage.get("prompt_tokens", 0)
                completion = usage.get("completion_tokens", 0)
                model      = step.get("model", "unknown")
                if prompt or completion:
                    nodes.append(NodeExecution(
                        node_name=step.get("name") or step.get("title") or "AI Step",
                        node_type="llm",
                        model=model,
                        prompt_tokens=prompt,
                        completion_tokens=completion,
                        total_tokens=prompt + completion,
                        cost_usd=calculate_cost(model, prompt, completion),
                    ))

        return StandardExecution(
            platform="zapier",
            execution_id=str(payload.get("zapRunId") or payload.get("id") or ""),
            workflow_id=str(payload.get("zapId") or payload.get("zap_id") or ""),
            status=payload.get("status", "success"),
            triggered_by=payload.get("trigger", "unknown"),
            started_at=parse_dt(payload.get("startedAt")),
            finished_at=parse_dt(payload.get("finishedAt")),
            duration_ms=payload.get("duration_ms"),
            nodes=nodes,
            events=[],
        )
