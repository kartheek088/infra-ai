# Phase 0 — Architecture Map (ARI rebuild)

> Goal: Produce an internal map of current architecture, old/reference architecture (ai-observability), reusable components, broken components, missing components, and migration risks. This is the source of truth for the 12-phase rebuild plan.
>
> Constraints carried forward from earlier sessions:
> - No fake data, no hardcoded executions, no fake AI explanations
> - Do NOT simulate backend success in the frontend
> - The LLM may *explain* risk, it must not *determine* the authoritative risk score
> - NEVER expose the OpenRouter key to React/Vite/browser code
> - The rebuild must actually be implemented, not just recommended
> - ai-observability felt coherent because of the chain:
>   **Automation → Execution → Events → Timeline → Anomalies → Explanation**

---

## 1 · Current ARI architecture (what we have today)

### 1.1 — Stack
- **Backend**: FastAPI (async), SQLAlchemy 2.0 async + asyncpg, PostgreSQL, JWT auth (python-jose + bcrypt)
- **Frontend**: React + Vite + TypeScript, Zustand for auth store, React Router, custom hooks layer
- **Pipeline model**: webhook → adapter → `StandardExecution` → `process_execution()` → two background tasks (alerts + security)

### 1.2 — Backend surface (16 routers in `app/main.py`)
`auth`, `workflows`, `executions`, `webhook`, `api_keys`, `rag`, `suggestions`, `analytics`, `alerts`, `dashboard`, `policies`, `security_findings`, `audit_logs`, `tenants`, `applications`, plus `/health` root.

### 1.3 — Domain model (12 tables)
- **Multi-tenancy layer**: `Tenant` → `User`, `Application`, `Workflow`
- **Ingestion layer**: `Run` (with `events_jsonb` JSONB column) + `TokenUsage` (per node) + `RAGMetrics`
- **Security layer**: `SecurityFinding` (with `risk_score`, `risk_factors`, `governance_action`, `policy_id`)
- **Governance layer**: `Policy` (condition tree) + `Alert` + `AuditLog`
- **Access layer**: `ApiKey`

### 1.4 — Universal event log (`app/models/event.py`)
- `Event` model is **fully defined** with `EventType` enum (EXECUTION_*, NODE_*, LLM_*, RAG_*, TOOL_*, SECURITY_FINDING, POLICY_EVALUATED, BLOCK_APPLIED, INFO/WARNING/ERROR) and `Component` enum (PLATFORM_ADAPTER, SECURITY_ENGINE, POLICY_ENGINE, TELEMETRY, API, WEBHOOK)
- `Event` is **not yet wired** into `webhook.py` `process_execution()` — events currently land in the `Run.events_jsonb` JSONB blob instead of as rows
- Phase 3 must close this gap (and decide transition strategy to avoid double-write)

### 1.5 — Ingestion pipeline
- `validate_api_key()` → looks up `ApiKey`, returns user_id, updates `last_used_at`
- `process_execution()` matches workflow by `Workflow.id` OR `Workflow.n8n_workflow_id`
- Creates one `Run` + N `TokenUsage` rows
- Queues two `BackgroundTasks`:
  - `run_alert_checks_background` — opens own `AsyncSessionLocal`, runs threshold + inactivity checks
  - `run_security_analysis_background` — opens own `AsyncSessionLocal`, reconstructs `StandardExecution` from snapshots, runs `SecurityEngine.analyze_execution`, then for each persisted `SecurityFinding` calls `PolicyEvaluator.evaluate()` to apply governance, writes `AuditLog`
- `make_endpoint(platform)` factory creates `/api/webhook/{n8n|make|zapier|custom}` endpoints

### 1.6 — Adapters (`app/adapters/`)
- `base_adapter.py` defines three dataclasses:
  - `NodeExecution` (per-node tokens, timing, error metadata, plus Phase 1 extensions: `event_type`, `provider`, `error_message`, `latency_ms`, `metadata`)
  - `ExecutionEvent` (lifecycle event log)
  - `StandardExecution` (platform-agnostic container with `nodes: list[NodeExecution]` and `events: list[ExecutionEvent]`)
- Platform adapters: `custom_adapter.py`, `n8n_adapter.py`, `make_adapter.py`, `zapier_adapter.py`

### 1.7 — Security engine (`app/core/security/engine.py`)
- `SecurityEngine.analyze_execution(execution, nodes, run_id, workflow_id, user_id)` runs all detectors and persists findings
- `RiskScorer.compute()` — `BASE_SCORES` (critical=100, high=75, medium=50, low=25, info=10) + weighted contribution from `risk_factors` list, clamped 0–100
- Five detectors consolidated in `app/core/security/__init__.py`:
  - `SensitiveDataExposureDetector`
  - `APISecretLeakDetector`
  - `ExternalDataExfiltrationDetector`
  - `ModelAnomalyDetector`
  - `ErrorPatternDetector`
- `SecurityFinding` persists with `detector_id`, `detector_name`, `severity`, `confidence`, `title`, `description`, `finding_data`, `risk_score`, `risk_factors`, `node_name`, `provider`, `reviewed`

### 1.8 — Policy engine (`app/core/policy_engine.py`)
- `PolicyEvaluator.evaluate(finding, workflow_id)` — takes a persisted `SecurityFinding` (or `SecurityFindingCreate`), finds matching `Policy` rows, walks the condition tree (operators: `equals`, `not_equals`, `in`, `not_in`, `gt`, `lt`, `gte`, `lte`, `contains`; combinators: `all`, `any`)
- Returns `(governance_action, policy_id, policy_name)` tuple
- **Latent bug at line 41**: local `user_id` variable is computed but never used; line 47 still uses `finding.user_id`. Safe today because webhook only passes persisted `SecurityFinding` rows (which have `user_id`). Will break if `SecurityFindingCreate` is ever passed.

### 1.9 — Other services
- `services/rag_analyzer.py` — `get_rag_summary(workflow_id, db)` (avg chunks, fill %, relevance) + `get_rag_efficiency_trend()` (last 20 RAGMetrics)
- `services/suggestions.py` — rules-based engine producing 9 ranked optimization suggestions (RAG top_k, prompt cache, chunk size, cost spike, token spike, loop, error rate, model downgrade, embedding quality) + `detect_unused_nodes()` + `detect_redundant_retrievals()`
- `services/health_score.py` — composite inefficiency score
- `services/notifications.py` — alert delivery
- `services/token_parser.py` — token metrics
- `services/auth_service.py` — auth helpers

### 1.10 — Frontend (React + Vite)
- Pages: `Login`, `Register`, `Dashboard`, `WorkflowList`, `WorkflowDetail`, `ExecutionDetail`, `SecurityFindings`, `Policies`, `AuditLog`, `Settings`, `ApiKeys`, `TestPlayground`
- Custom hooks: `useWorkflows`, etc.
- Zustand `useAuthStore` (token, isAuthenticated, user)
- Protected routes + sidebar `Layout`
- `TestPlayground.tsx` — UI for sending mock executions (4 templates: LLM Agent, RAG, Tool Calling, Multi-Node) to `/api/webhook/custom` with `X-API-Key`

### 1.11 — Test infrastructure (already exists)
- `backend/scripts/seed_test_data.py` — idempotent seed: tenant, user, API key `ari-test-key-001`, 3 workflows
- `backend/scripts/send_test_execution.py` — CLI sender with 4 payload types (`--type llm|rag|tool|multi`)
- `TESTING.md` — quick-start guide covering seed → backend → frontend → Test Playground → CLI → dashboard verification

### 1.12 — Configuration (`app/core/config.py`)
- Pydantic `Settings`: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY` (default `"ari-super-secret-key-change-in-production"` — must override in prod), `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS`
- Auto-converts `postgres://` → `postgresql+asyncpg://`
- **No `OPENROUTER_API_KEY` setting yet** — required for Phase 8

### 1.13 — Database session (`app/db/session.py`)
- `engine = create_async_engine(settings.DATABASE_URL, echo=True, pool_size=10, max_overflow=20)`
- `AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`
- `get_db()` — yields session with commit/rollback
- **`echo=True` should be a setting toggle** for production (currently always on — noisy SQL logs in prod)

---

## 2 · Reference architecture (ai-observability — the "old" one)

This is the project whose coherent chain we must reproduce. Source: `ai-observability.zip`.

### 2.1 — Data model
Synchronous SQLAlchemy + SQLite. Three tables: `Automation` → `Execution` (with `timeline_json` + `anomalies_json` JSON columns) → `Event`.

### 2.2 — Coherent chain
```
Automation → Execution → Events → Timeline → Anomalies → Explanation
```

### 2.3 — `services/analyzer.py` (the small, clean module we must port)
- `compute_execution_status(events)` — FAILED > DELAYED (>3s) > SUCCESS
- `detect_anomalies(events)`:
  - `e.duration > 3` → "latency spike"
  - `e.tokens > 500` → "token spike"
  - `e.status != SUCCESS` → "failed"
  - `(e.timestamp - prev.timestamp).total_seconds() > 2` → "idle gap before {step} ({gap:.1f}s)"
- `build_timeline_dict(events)` — `{"execution_id": ..., "steps": [{step, status, duration, tokens, cost, timestamp}]}`

### 2.4 — `services/groq_client.py`
- `analyze_with_groq(timeline, health, anomalies, total_tokens, total_cost)` — calls Groq `llama-3.1-8b-instant` with a single prompt
- Returns plain-text analysis: analytical summary + anomaly callouts + cost/token risks + improvements
- Failsafe: returns "Analysis unavailable…" if `GROQ_API_KEY` missing
- **Anti-pattern to avoid**: ai-observability's `ingestion.py` calls `analyze_with_groq()` on **every event ingestion**, not on execution completion. This is wasteful and slow. ARI must call AI once per execution completion (or once per page-load of ExecutionDetail with caching).

### 2.5 — `services/ingestion.py` (note the anti-pattern)
- Called on every event
- Calls `analyze_with_groq()` per event
- DO NOT port this pattern

### 2.6 — `services/automation_service.py`
- Wrapper around the Automation CRUD + on-platform execution
- Less relevant to ARI (we have multi-tenancy + adapters), kept here for reference

### 2.7 — Frontend killer page (ExecutionTrace component)
- The "killer page" pattern: a single execution detail view that combines timeline + per-step metrics + AI explanation panel
- ARI's `ExecutionDetail.tsx` is missing this — it currently shows per-node token usage, latency, and cost, but no timeline graph, no anomalies panel, no AI explanation

### 2.8 — What made it feel coherent
- Small surface area (3 tables, 4 services)
- Hardcoded but transparent thresholds (>3s, >500 tokens, >2s idle)
- All "intelligence" is derived from the same event list — no parallel data structures
- AI explanation is a *post-processing* of the timeline, not the source of truth

---

## 3 · Reusable components (keep, do not rewrite)

| Component | Location | Why reusable |
|---|---|---|
| `StandardExecution` / `NodeExecution` / `ExecutionEvent` dataclasses | `app/adapters/base_adapter.py` | Platform-agnostic; Phase 1 extensions already merged (`event_type`, `provider`, `error_message`, `latency_ms`, `metadata`) |
| Webhook router pattern + `process_execution()` flow | `app/routers/webhook.py` | Validates key → matches workflow → creates Run + TokenUsage → queues 2 background tasks; this is the spine |
| Background task pattern (each task opens own `AsyncSessionLocal`) | `app/routers/webhook.py` | Avoids "session is closed" errors and gives true parallelism — keep as the pattern for new AI explanation task |
| `SecurityEngine` + 5 detectors | `app/core/security/engine.py`, `app/core/security/__init__.py` | Already orchestrates detection + risk + persistence. Just integrate into hot path and add `analyze_execution` return value wiring |
| `RiskScorer.compute()` | `app/core/security/engine.py` | Deterministic 0–100 scoring; matches the rule "LLM may explain, never determine risk" |
| `PolicyEvaluator` + condition tree | `app/core/policy_engine.py` | Reusable for the user-triggered policy UI; only needs the user_id bug fix |
| `Run` + `TokenUsage` models | `app/models/run.py` | Phase 1 extensions already present; no schema migration needed for ingestion |
| `Event` model | `app/models/event.py` | Already complete; only needs the integration wiring in `process_execution()` |
| `ApiKey` validation + last_used_at update | `app/routers/webhook.py` | Multi-tenant isolation already enforced |
| Rules-based suggestions engine | `app/services/suggestions.py` | 9 rules with impact ranking; integrate into Dashboard alongside the AI explanation |
| RAG analyzer | `app/services/rag_analyzer.py` | Already supports summary + trend; exposes the inputs the AI explanation will reference |
| `TestPlayground.tsx` + seed scripts | `frontend/src/pages/TestPlayground.tsx`, `backend/scripts/seed_test_data.py`, `backend/scripts/send_test_execution.py` | Already idempotent and documented in `TESTING.md`; Phase 0 workhorse |
| Frontend hooks layer (`useWorkflows` etc.) | `frontend/src/hooks/` | Reusable for any new view that needs workflow/run data |
| Zustand auth store + ProtectedRoute | `frontend/src/store/authStore.ts`, `frontend/src/App.tsx` | Just add a small `useExecutionDetail(runId)` hook |

---

## 4 · Broken components (must fix)

### 4.1 — `PolicyEvaluator` user_id dead code
- File: `app/core/policy_engine.py`, line 41 / 47
- Bug: local `user_id` variable computed but unused; line 47 uses `finding.user_id`
- Currently latent (webhook path only passes persisted `SecurityFinding` rows)
- Fix: use the local `user_id` on line 47, or refactor to query by `workflow_id` and filter by `tenant_id`

### 4.2 — `echo=True` in production DB engine
- File: `app/db/session.py`
- Bug: SQL echo is always on; in prod this is noise + small perf cost
- Fix: read from settings (`settings.DB_ECHO`, default `False`)

### 4.3 — Default `SECRET_KEY`
- File: `app/core/config.py`
- Bug: `SECRET_KEY = "ari-super-secret-key-change-in-production"`
- Fix: fail-fast at startup if `SECRET_KEY` is unset or matches the default in non-dev environments

### 4.4 — `Event` model not wired into ingestion
- File: `app/routers/webhook.py` `process_execution()`
- Bug: events are dumped into `Run.events_jsonb` JSONB; the typed `Event` table is empty
- Fix: write Event rows during `process_execution()` for each lifecycle + per-node event; keep `events_jsonb` for one release as a denormalized read cache, then drop

### 4.5 — `StandardExecution` / `NodeExecution` not written to dedicated tables
- The adapter's platform-agnostic objects are reconstructed in the security background task from `TokenUsage` rows
- Fix: persist the platform-agnostic snapshot alongside Run creation so the AI explanation + anomaly detection can replay without rebuilding

### 4.6 — Frontend `ExecutionDetail` is missing the killer-page experience
- File: `frontend/src/pages/ExecutionDetail.tsx`
- Bug: shows per-node table but no timeline, no anomalies, no AI explanation panel
- Fix: rebuild per Phase 9 (timeline component, anomalies list, AI panel, status badge)

### 4.7 — ai-observability per-event Groq call (anti-pattern to avoid)
- Source: `ai-observability/backend/app/services/ingestion.py`
- Bug: AI analysis is triggered on every event ingestion
- Fix: in ARI, AI explanation must run **once per execution completion** (or once per page-load with caching keyed by run_id) — never per event

---

## 5 · Missing components (must build)

### 5.1 — Anomaly detection engine
- Port `ai-observability/services/analyzer.py` → `app/services/anomaly_detector.py`
- Adapt thresholds: latency > 3s, tokens > 500, idle gap > 2s
- Inputs: `Event` rows (Phase 3 must land first) OR `TokenUsage` rows
- Outputs: list of `{type, node, severity, message, evidence}` items

### 5.2 — Timeline builder
- Port `build_timeline_dict()` → produce the same JSON shape that the AI prompt consumes
- Output: `{execution_id, started_at, finished_at, status, steps: [{step, status, duration, tokens, cost, timestamp, provider, model}]}`

### 5.3 — Server-side OpenRouter client
- File: `app/services/openrouter_client.py` (new)
- Config: add `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` to `app/core/config.py`
- Function: `explain_execution(timeline, anomalies, findings, total_tokens, total_cost, health_status)` → plain text
- Same failsafe pattern as Groq: if key missing, return `"Analysis unavailable — OpenRouter not configured in backend."`
- **Never** import this from frontend; never expose the key to Vite env

### 5.4 — AI explanation background task
- Add to `process_execution()` background queue: `run_ai_explanation_background`
- Opens own `AsyncSessionLocal`, loads timeline + anomalies + findings, calls `openrouter_client.explain_execution`, writes result to a new column on `Run` (e.g. `ai_explanation`, `ai_explained_at`) or a separate `AIExplanation` table
- Cache: keyed by run_id; if `ai_explained_at` is recent and inputs unchanged, return cached value

### 5.5 — API endpoint to fetch AI explanation
- `GET /api/executions/{run_id}/ai-explanation` — returns `{explanation, generated_at, model, cached}`
- Called by `ExecutionDetail.tsx` on mount; re-fetch button to force regeneration

### 5.6 — ExecutionDetail killer page
- File: `frontend/src/pages/ExecutionDetail.tsx` — rebuild per ai-observability's pattern
- Components: status badge, timeline (steps list with timing), per-node token table, anomalies panel, security findings panel, AI explanation panel (collapsible), "Re-analyze" button

### 5.7 — Anomaly/finding visualization in WorkflowDetail
- Currently WorkflowDetail shows aggregate stats; should also surface top anomalies and recent security findings

### 5.8 — Settings: API key management UX
- Already exists as `ApiKeys.tsx`; verify it exposes the new "regenerate" + "revoke" actions and shows the last-used timestamp

### 5.9 — Migration plan
- `alembic` setup (or equivalent) so Phase 1–9 schema changes are reproducible
- Phase 0 deliverable for ops; subsequent phases must not break the migrations

### 5.10 — LangChain demo workflow
- One registered `wf-langchain-demo-001` that uses LangChain on the client side and POSTs a representative execution
- Phase 10 deliverable — not blocking the rebuild but required to demonstrate a non-trivial multi-node chain end-to-end

### 5.11 — End-to-end tests
- One test that exercises seed → Playground send → dashboard render → security finding fired → policy applied → audit logged
- Phase 11 deliverable

### 5.12 — Production/deployment audit
- `docker-compose.yml` + `render.yaml` already exist
- Phase 12: verify env vars, CORS, DB connection, secret rotation, rate limiting, request size limits

---

## 6 · Migration risks

### 6.1 — Schema migration
- Adding `ai_explanation` and `ai_explained_at` columns to `Run` is a non-breaking additive change
- Adding the `Event` rows alongside `events_jsonb` doubles write volume during transition; mitigate by keeping `events_jsonb` as read-cache during Phase 3, then dropping after one release
- Indexes: `Event(run_id)`, `Event(tenant_id, occurred_at)`, `SecurityFinding(workflow_id, severity)` — verify they exist or add via migration

### 6.2 — Async vs sync boundaries
- ARI is fully async; ai-observability was sync. Porting `analyzer.py` is trivial (no I/O), but the OpenRouter call must be wrapped in `httpx.AsyncClient` and called from a background task
- Background task pattern is already established; reuse it

### 6.3 — Webhook contract stability
- `n8n/make/zapier/custom` payloads are already documented in `TESTING.md`
- Do **not** change the contract during rebuild; only add optional fields (e.g. `prompt_content` for richer AI explanations)
- If we add `prompt_content` we must redact it before storage (PII)

### 6.4 — Performance impact of AI explanation
- A single execution triggers one OpenRouter call; the page-load of ExecutionDetail should hit the cache, not re-call the model
- LLM calls must never block the webhook response — the webhook has already proven this pattern with `BackgroundTasks`
- Set a hard timeout (10s) and budget per execution

### 6.5 — OpenRouter key handling
- Add to backend env only; never read from `import.meta.env` or any frontend env
- Add a startup log that warns if `OPENROUTER_API_KEY` is missing but does **not** crash dev mode

### 6.6 — Risk score authority
- LLM explanation is text; `SecurityFinding.risk_score` is set by `RiskScorer` and is the authoritative number
- The UI must display risk_score from the DB, not from the AI text
- Phase 9 must make this explicit in the UI ("Risk score: 87 (deterministic). AI commentary below.")

### 6.7 — Multi-tenant isolation in new code
- All new queries must filter by `tenant_id` (and where relevant `user_id`)
- `openrouter_client` must never receive tenant data it doesn't need; pass summary aggregates, not raw events

### 6.8 — Test infrastructure
- Seed data + send_test_execution + TestPlayground already exist; do not break them during the rebuild
- Add an `--explain` flag to `send_test_execution.py` that waits a few seconds and prints the AI explanation for that run (useful for CI sanity check)

---

## 7 · Migration order (12 phases)

1. **Phase 1** — Infrastructure: `echo=True` toggle, secret key fail-fast, Redis, migrations, health endpoint, startup, env handling
2. **Phase 2** — Unify domain model: `Run.ai_explanation` + `ai_explained_at` columns; verify Event model is ready
3. **Phase 3** — Rebuild ingestion: wire `Event` rows into `process_execution()`; keep `events_jsonb` as cache
4. **Phase 4** — Rebuild runtime analysis: port `detect_anomalies` + `build_timeline_dict` → `app/services/anomaly_detector.py`
5. **Phase 5** — Security detection integration: confirm `SecurityEngine` runs in background task; consider splitting detectors into separate modules for clarity
6. **Phase 6** — Policy engine: fix the `user_id` bug, add per-workflow policy matching, add risk + policy + governance wiring
7. **Phase 7** — Review + audit: ensure every `SecurityFinding` has a review state, every governance action writes an `AuditLog` row
8. **Phase 8** — OpenRouter AI explanation: backend client + config + background task + endpoint
9. **Phase 9** — ExecutionDetail killer page: timeline + anomalies + findings + AI panel
10. **Phase 10** — LangChain demo workflow
11. **Phase 11** — End-to-end tests
12. **Phase 12** — Production/deployment audit

---

## 8 · Success criteria for the rebuild

- Sending a Test Playground execution produces a row in `Run` + N rows in `TokenUsage` + events in `Event` table
- Within ~2s of completion, the security engine has run and `SecurityFinding` rows exist (or none, if clean)
- Within ~5s of completion, the AI explanation is cached on the Run
- Opening `ExecutionDetail` shows: status, timeline, per-node table, anomalies list, security findings, AI explanation panel — all sourced from the backend, no client-side fabrication
- Risk score is always the DB value, never re-derived from the AI text
- `n8n/make/zapier/custom` webhook contracts are unchanged
- All tests pass; one end-to-end Playwright + one backend integration test
- `docker-compose up` brings the whole stack up and `seed_test_data` + `send_test_execution --explain` work in CI
