from datetime import datetime
from app.adapters.base_adapter import StandardExecution, NodeExecution
from app.services.token_parser import calculate_cost


class MakeAdapter:
    platform = "make"

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
        for module in payload.get("modules", []):
            app_name = module.get("app", "").lower()
            if any(x in app_name for x in ["openai", "anthropic", "gemini", "cohere", "ai"]):
                usage      = module.get("usage", {}) or module.get("tokens", {})
                prompt     = usage.get("input_tokens") or usage.get("prompt_tokens", 0)
                completion = usage.get("output_tokens") or usage.get("completion_tokens", 0)
                model      = module.get("model") or module.get("parameters", {}).get("model", "unknown")
                if prompt or completion:
                    nodes.append(NodeExecution(
                        node_name=module.get("name") or module.get("label") or "AI Module",
                        node_type="llm",
                        model=model,
                        prompt_tokens=prompt,
                        completion_tokens=completion,
                        total_tokens=prompt + completion,
                        cost_usd=calculate_cost(model, prompt, completion),
                    ))

        status = "failed" if (payload.get("error") or payload.get("status") == "failed") else "success"

        return StandardExecution(
            platform="make",
            execution_id=str(payload.get("executionId") or payload.get("id") or ""),
            workflow_id=str(payload.get("scenarioId") or payload.get("scenario_id") or ""),
            status=status,
            triggered_by=payload.get("trigger", "unknown"),
            started_at=parse_dt(payload.get("startedAt") or payload.get("start")),
            finished_at=parse_dt(payload.get("finishedAt") or payload.get("end")),
            duration_ms=payload.get("duration"),
            nodes=nodes,
        )
