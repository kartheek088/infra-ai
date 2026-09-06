from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    auth, workflows, runs, webhook,
    api_keys, rag, suggestions,
    analytics, alerts, dashboard,
)
from app.middleware.error_handler import global_exception_handler

app = FastAPI(
    title="Inferago API",
    description="""
Multi-platform AI workflow token monitoring and optimization.

## Features
- **Real-time monitoring** — every run captured via webhook instantly
- **Token tracking** — prompt + completion tokens per node per run
- **Cost calculation** — per-model USD pricing, per-run and per-day
- **Health scoring** — composite 0-100 score with grade A/B/C/D
- **Anomaly detection** — cost spikes, token spikes, loop detection
- **RAG analytics** — chunk efficiency, relevance scores, duplicate detection
- **Suggestions engine** — 9 rules, ranked by impact with savings estimates
- **Inefficiency scoring** — 0-100 score with specific flags
- **Run filtering** — by status, platform, date, cost
- **Node-level traces** — step-by-step execution breakdown with error hints
- **Alerts** — cost threshold, token spike, error rate, inactivity, daily/monthly budget
- **Multi-platform** — n8n, Make, Zapier, Custom

## Platforms
Connect via webhook URL: `/api/webhook/{platform}?api_key=YOUR_KEY`
    """,
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

from app.core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)

app.include_router(auth.router)
app.include_router(workflows.router)
app.include_router(runs.router)
app.include_router(webhook.router)
app.include_router(api_keys.router)
app.include_router(rag.router)
app.include_router(suggestions.router)
app.include_router(analytics.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status":    "ok",
        "service":   "inferago",
        "version":   "0.4.0",
        "platforms": ["n8n", "make", "zapier", "custom"],
        "features":  [
            "token_tracking", "cost_calculation", "health_score",
            "anomaly_detection", "loop_detection", "rag_analytics",
            "suggestions", "inefficiency_score", "run_filtering",
            "node_traces", "alerts", "multi_platform",
        ],
    }
