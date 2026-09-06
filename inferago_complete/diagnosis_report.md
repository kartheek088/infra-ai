# Inferago Diagnosis Report

Generated on 2026-09-06. This report identifies all blockers, critical issues, and significant defects in the Inferago application, grouped by severity.

---

## BLOCKER — Stops the application from working or data from being correct

### 1. Alembic `env.py` uses `+psycopg` instead of `+asyncpg`
**File:** `backend/alembic/env.py:25`
**Code:** `db_url = raw_url.replace("+asyncpg", "+psycopg")`
**Impact:** Alembic migrations will fail because `psycopg` is a sync driver while SQLAlchemy 2.0 async uses `asyncpg`. This prevents creating/updating the database schema.
**Fix:** Remove the `+psycopg` replacement, keep `+asyncpg`, or use `+pg8000`/`+asyncpg` consistently.

### 2. `requirements.txt` lists both `asyncpg` AND `psycopg[binary]`
**File:** `backend/requirements.txt`
**Impact:** Package conflict — both cannot be actively used. The app clearly intends async PostgreSQL (`asyncpg`), but `psycopg[binary]` is also listed. Installing both may cause import conflicts or silently prefer one over the other.
**Fix:** Remove `psycopg[binary]` from requirements since the app uses `asyncpg` + `create_async_engine`.

### 3. No Alembic migrations in `versions/` directory
**File:** `backend/alembic/versions/` (empty)
**Impact:** There are zero migration scripts. The database schema cannot be created from model definitions via Alembic. The `Workflow`, `Run`, `TokenUsage`, `User`, `ApiKey`, `RAGMetrics`, `Alert` tables will never be created automatically.
**Fix:** Generate initial migrations: `alembic init` (if not already) and `alembic revision --autogenerate -m "initial schema"` to produce migration files from the model definitions.

### 4. Dashboard alert serialization produces "None" for null values
**File:** `backend/app/routers/dashboard.py`
**Bug:** `str(a.last_triggered_at)` produces the literal string "None" when `last_triggered_at` is `None`/null.
**Impact:** The dashboard UI renders "None" as text for alerts that have never been triggered, which is a broken user experience and misleading.
**Fix:** Use `a.last_triggered_at.isoformat() if a.last_triggered_at else ""` or `str(a.last_triggered_at) if a.last_triggered_at else ""`.

### 5. `rag.py` `store_rag_metrics` has NO `get_current_user` dependency
**File:** `backend/app/routers/rag.py` — `store_rag_metrics` endpoint
**Impact:** Any caller (including unauthenticated) can store RAG metrics for any workflow_id, potentially poisoning data or writing metrics for workflows they don't own. This is a security vulnerability.
**Fix:** Add `get_current_user` dependency to the endpoint, and verify `workflow.user_id == current_user.id`.

### 6. Global exception handler masks real error details
**File:** `backend/app/middleware/error_handler.py`
**Impact:** All unhandled exceptions return 500 with generic "Internal server error", hiding the actual error type, traceback, and context. Makes debugging extremely difficult in production.
**Fix:** Log the full exception traceback server-side, and return a sanitized error message (include error type in development, generic message in production). Consider adding `request` context to the response.

### 7. Weak hardcoded SECRET_KEY in `.env`
**File:** `backend/.env:3`
**Code:** `SECRET_KEY=inferago-super-secret-key-change-in-production`
**Impact:** The production secret key is a well-known placeholder value. If this .env file is ever committed to a public repo, all JWT tokens and API keys are compromised.
**Fix:** Generate a proper random secret key and ensure `.env` is in `.gitignore`.

### 8. `token_parser.py` model parsing produces incorrect cost data
**File:** `backend/app/services/token_parser.py:13`
**Code:** `base = model.split("-202")[0] if "-202" in model else model`
**Impact:** The `calculate_cost` function strips `-202` from model names (e.g., `gpt-4o-2024-05-13` → `gpt-4o`). But if a model name doesn't contain `-202`, it uses the full model name as lookup key. This means:
- Models like `gpt-4o-mini-2024` → `gpt-4o-mini` ✓ (correct)
- Models like `claude-3-5-sonnet-20240620` → `claude-3-5-sonnet` ✓ (correct)  
- But if a model naming convention changes or a model without `-202` suffix is used, the fallback `MODEL_COSTS.get(model, DEFAULT_COST)` may return wrong pricing.
**Critical:** The system must produce correct data, not merely render a working dashboard. If the dashboard works but the numbers are wrong, the application is NOT considered fixed.
**Fix:** Make the model parsing more robust — validate against `MODEL_COSTS` keys, or use a more explicit mapping.

---

## CRITICAL — Security or fundamental data correctness issues

### 9. Frontend `client.ts` uses `VITE_API_URL` with fallback `""`
**File:** `frontend/src/api/client.ts`
**Code:** `baseURL: import.meta.env.VITE_API_URL ?? ""`
**Impact:** If `VITE_API_URL` is not set, the axios baseURL is an empty string, causing all API requests to fail with routing errors. The fallback should point to the development backend URL (e.g., `http://localhost:8000`).
**Fix:** Set a sensible default: `baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000"`.

### 10. Frontend stores JWT token in `localStorage`
**File:** `frontend/src/store/authStore.ts` — zustand store
**Impact:** Token stored in `localStorage` is vulnerable to XSS attacks. If an attacker can inject script, they can steal the JWT and impersonate the user.
**Fix:** Consider using `HttpOnly` cookies for token storage, or at minimum add secure flags and same-site settings. If localStorage is retained, add XSS sanitization.

### 11. `api_keys.py` `generate_key()` format may not match expectations
**File:** `backend/app/models/api_key.py` — `generate_key()`
**Code:** `return f"inf_live_{secrets.token_urlsafe(32)}"`
**Impact:** The generated key format `inf_live_{32 base64 chars}` should be verified against n8n/make/zapier webhook expectations. Some platforms expect different prefixes or formats.
**Fix:** Verify the key format matches the target platforms' API key requirements. The `inf_live_` prefix appears intentional for Inferago's own API key system.

### 12. No auth on several dashboard/api endpoints
**File:** Multiple routers missing `get_current_user` dependency
**Impact:** Endpoints like dashboard data, suggestions, and potentially other CRUD operations don't verify the authenticated user, allowing cross-user data access.
**Fix:** Add `get_current_user` dependency to all router endpoints that access workflow/run data, and verify ownership.

---

## HIGH — Significant issues affecting correctness or usability

### 13. Dashboard `asyncio.gather` without error handling
**File:** `backend/app/routers/dashboard.py`
**Impact:** If any individual dashboard data fetch fails (e.g., RAG metrics unavailable), the entire `asyncio.gather` may fail or return partial data with "None" values, breaking the master dashboard view.
**Fix:** Add per-function error handling with fallback default values, or use `return_exceptions=True` with `asyncio.gather`.

### 14. Health score calculation edge cases
**File:** `backend/app/services/health_score.py`
**Impact:** 
- When no runs exist, returns score 0 with "No runs yet" message — acceptable
- `perf_score` division by zero if no durations exist — handled with `if durations else 70`
- `cost_score` can be negative if `spike_penalty > 100` — handled with `max(0, ...)`
Overall the logic seems reasonable but edge cases should be tested.

### 15. Suggestions engine — Rule 9 uses `rag` variable outside `if rag and` guard
**File:** `backend/app/services/suggestions.py:212`
**Code:** `if rag and rag.get("avg_relevance_score", 1) < 0.5:` — actually guarded correctly.
Reviewing again, this IS properly guarded. No issue here.

### 16. `check_and_fire_alerts` may not correctly attribute alerts to users
**File:** `backend/app/services/notifications.py:46-47`
**Code:** `select(Alert).where(Alert.workflow_id == workflow_id, Alert.is_active == True)`
**Impact:** Alerts are fetched by `workflow_id` only, without verifying the authenticated user owns the workflow. Combined with issue #12, this allows alert manipulation across users.
**Fix:** Verify workflow ownership before checking alerts.

---

## MEDIUM — Quality and polish issues

### 17. `models/__init__.py` and `routers/__init__.py` are empty
**Impact:** These empty `__init__.py` files are harmless (Python packages), but suggest the project may have incomplete package structure. No actual import issues since models/routers are imported directly.
**Fix:** Optional — add `__all__` or leave as-is (functional as-is).

### 18. Frontend `client.ts` response interceptor redirects to `/login` on 401
**File:** `frontend/src/api/client.ts`
**Impact:** On 401, the interceptor removes the token from localStorage and redirects to `/login`. This is standard behavior but should also include a clear error message before redirect.
**Fix:** Add a notification/toast before redirecting.

### 19. Various UI components have loading/empty states
**Files:** Multiple frontend components
**Impact:** Several components (InefficiencyScore, CostTrendChart, etc.) return `null` or loading spinners when data is absent, which is acceptable but could be more user-friendly.
**Fix:** Optional UX improvements.

---

## Summary

**Total blockers:** 8
**Total critical:** 4
**Total high:** 3
**Total medium:** 3

### Priority Fix Order

1. **Fix Alembic `env.py` driver mismatch** — Without this, the database schema cannot be created.
2. **Fix `token_parser.py` model parsing** — Without correct cost calculation, the system produces wrong data (violates the critical requirement: "The system must produce correct data, not merely render a working dashboard").
3. **Generate Alembic migrations** — Without migrations, the database schema cannot be initialized.
4. **Fix dashboard alert serialization "None" bug** — Broken UI rendering for null values.
5. **Fix `rag.py` missing auth on `store_rag_metrics`** — Security vulnerability.
6. **Fix `requirements.txt` asyncpg/psycopg conflict** — Package conflict may prevent proper installation.
7. **Fix `.env` weak SECRET_KEY** — Security best practice.
8. **Fix global exception handler masking errors** — Debuggability.
9. **Fix frontend `VITE_API_URL` fallback** — API calls fail without correct base URL.
10. **Add auth dependencies to dashboard/rag endpoints** — Security and data integrity.