# Pricing per 1,000 tokens (USD) — updated Sep 2026
MODEL_COSTS = {
    # OpenAI
    "gpt-4o":              {"prompt": 0.005,   "completion": 0.015},
    "gpt-4o-mini":         {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4-turbo":         {"prompt": 0.01,    "completion": 0.03},
    "gpt-4":               {"prompt": 0.03,    "completion": 0.06},
    "gpt-3.5-turbo":       {"prompt": 0.0005,  "completion": 0.0015},
    # Anthropic
    "claude-3-5-sonnet":   {"prompt": 0.003,   "completion": 0.015},
    "claude-3-5-haiku":    {"prompt": 0.00025, "completion": 0.00125},
    "claude-3-opus":       {"prompt": 0.015,   "completion": 0.075},
    "claude-3-sonnet":     {"prompt": 0.003,   "completion": 0.015},
    "claude-3-haiku":      {"prompt": 0.00025, "completion": 0.00125},
}
DEFAULT_COST = {"prompt": 0.01, "completion": 0.03}


def _normalize_model_name(model: str) -> str:
    """
    Strip version suffixes from model names so they match MODEL_COSTS keys.

    Handles:
      gpt-4o-2024-05-13          → gpt-4o
      gpt-4o-mini-2024-07-18     → gpt-4o-mini
      claude-3-5-sonnet-20240620  → claude-3-5-sonnet
      anthropic/claude-3-5-sonnet → claude-3-5-sonnet
    """
    # Remove any provider prefix (e.g. "anthropic/", "openai/")
    if "/" in model:
        model = model.split("/")[-1]
    # Strip trailing version/date segments — split on first '-'
    # Works for: gpt-4o-mini, claude-3-5-sonnet, gpt-4-turbo
    base = model.split("-202")[0] if "-202" in model else model
    base = base.split("-2024")[0] if "-2024" in base else base
    base = base.split("-2025")[0] if "-2025" in base else base
    return base


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate cost in USD for a model call.
    Falls back to DEFAULT_COST when the model is unknown.
    """
    base = _normalize_model_name(model)
    costs = MODEL_COSTS.get(base, DEFAULT_COST)
    return round((prompt_tokens / 1000) * costs["prompt"] +
                (completion_tokens / 1000) * costs["completion"], 8)

def parse_node_tokens(node_name: str, node_runs: list) -> dict | None:
    for node_run in node_runs:
        outputs = node_run.get("data", {}).get("main", [[]])
        for output_list in outputs:
            for item in output_list:
                j = item.get("json", {})
                if "usage" in j:
                    u = j["usage"]
                    p = u.get("prompt_tokens", 0)
                    c = u.get("completion_tokens", 0)
                    m = j.get("model", "unknown")
                    return {"node_name": node_name, "model": m, "prompt_tokens": p,
                            "completion_tokens": c, "total_tokens": p+c, "cost_usd": calculate_cost(m,p,c)}
                if "inputTokens" in j or "outputTokens" in j:
                    p = j.get("inputTokens", 0)
                    c = j.get("outputTokens", 0)
                    m = j.get("model", "unknown")
                    return {"node_name": node_name, "model": m, "prompt_tokens": p,
                            "completion_tokens": c, "total_tokens": p+c, "cost_usd": calculate_cost(m,p,c)}
    return None

def parse_n8n_execution(payload: dict) -> list[dict]:
    token_data = []
    run_data = payload.get("data",{}).get("resultData",{}).get("runData",{})
    for node_name, node_runs in run_data.items():
        parsed = parse_node_tokens(node_name, node_runs)
        if parsed:
            token_data.append(parsed)
    return token_data

def calculate_run_duration(started_at: str | None, stopped_at: str | None) -> int | None:
    if not started_at or not stopped_at:
        return None
    try:
        from datetime import datetime
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        s = datetime.strptime(started_at[:26].replace("Z",""), fmt)
        e = datetime.strptime(stopped_at[:26].replace("Z",""), fmt)
        return int((e-s).total_seconds()*1000)
    except Exception:
        return None
