from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    auth, workflows, executions, webhook,
    api_keys, rag, suggestions,
    analytics, alerts, dashboard,
    policies, security_findings, audit_logs,
    tenants, applications, review,
)
from app.middleware.error_handler import global_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup/shutdown.
    Seeds default governance policies for any user that has none.
    """
    from app.db.session import AsyncSessionLocal
    from app.core.default_policies import seed_default_policies_for_all_users

    async with AsyncSessionLocal() as db:
        try:
            count = await seed_default_policies_for_all_users(db)
            if count:
                logger.info(f"Startup: seeded {count} default policies")
        except Exception as exc:
            logger.warning(f"Startup policy seed failed: {exc}")

    yield


app = FastAPI(
    title="ARI — AI Runtime Intelligence",
    description="""
AI Runtime Security & Governance platform for multi-platform AI workflow monitoring.

## Features
- **Universal Event Telemetry** — structured events from n8n, Make, Zapier, Custom webhooks
- **Security Detection** — PII exposure, prompt injection, data exfiltration, anomalous behavior
- **Policy Engine** — rule-based governance with ALLOW / ALERT / REQUIRE_REVIEW / BLOCK actions
- **AI LLM Call Tracking** — token usage, cost, latency, provider breakdown
- **RAG Analytics** — chunk efficiency, relevance scores, duplicate detection
- **Inefficiency Scoring** — 0-100 score with specific optimization flags
- **Human-in-the-Loop Reviews** — REQUIRE_REVIEW action surfaces executions for approval
- **Audit Logging** — immutable record of all policy evaluations and governance actions
- **Multi-tenancy** — tenants, applications, and environment-scoped isolation

## Platforms
Connect via webhook URL: `/api/webhook/{platform}?api_key=YOUR_KEY`
    """,
    version="0.5.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

from app.core.config import settings
import logging
logger = logging.getLogger(__name__)

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
app.include_router(executions.router)
app.include_router(webhook.router)
app.include_router(api_keys.router)
app.include_router(rag.router)
app.include_router(suggestions.router)
app.include_router(analytics.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(policies.router)
app.include_router(security_findings.router)
app.include_router(audit_logs.router)
app.include_router(tenants.router)
app.include_router(applications.router)
app.include_router(review.router)


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status":    "ok",
        "service":   "ari",
        "version":   "0.5.0",
        "platforms": ["n8n", "make", "zapier", "custom"],
        "features":  [
            "multi_tenancy", "universal_telemetry", "security_detection",
            "policy_engine", "llm_tracking", "rag_analytics",
            "inefficiency_score", "run_filtering", "node_traces",
            "alerts", "human_review", "audit_logs",
            "ai_summaries", "execution_tracking",
        ],
    }


@app.get("/api/metrics", tags=["System"])
@app.get("/metrics", tags=["System"])
async def get_metrics():
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select, func
    from app.models.workflow import Workflow
    from app.models.run import Run

    async with AsyncSessionLocal() as db:
        wf_count = (await db.execute(select(func.count(Workflow.id)))).scalar() or 0
        run_count = (await db.execute(select(func.count(Run.id)))).scalar() or 0
        failure_count = (await db.execute(select(func.count(Run.id)).where(Run.status.in_(["failed", "error"])))).scalar() or 0
        
        avg_dur_ms = (await db.execute(select(func.avg(Run.duration_ms)).where(Run.duration_ms.isnot(None)))).scalar() or 0.0
        avg_latency_s = round((avg_dur_ms or 0.0) / 1000.0, 2)

        return {
            "automations": wf_count,
            "executions": run_count,
            "failures": failure_count,
            "avg_latency": avg_latency_s,
        }
