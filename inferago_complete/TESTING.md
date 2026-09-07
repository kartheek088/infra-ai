# Testing ARI — Quick Start Guide

ARI (AI Runtime Intelligence) ingests AI workflow executions via webhooks from n8n, Make, Zapier, and any custom platform. This guide covers everything you need to send test data and verify the full pipeline — no external services required.

---

## 1 · Quick Start (No External Services)

The fastest path to seeing data flow through ARI's dashboard.

### 1.1 — Seed Test Data

```bash
cd backend
python -m scripts.seed_test_data
```

This creates:
- **Tenant**: `ari-test-tenant`
- **User**: `test@ari.local` / `testpassword123`
- **API key**: `ari-test-key-001`
- **3 Workflows**: LLM Agent Demo, RAG Pipeline Demo, Tool Calling Demo

> The script is **idempotent** — re-running it is safe.

### 1.2 — Start the Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 1.3 — Start the Frontend

```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### 1.4 — Register or Log In

Go to **Register** and create an account, or log in with:

```
Email:    test@ari.local
Password: testpassword123
```

### 1.5 — Send a Test Execution from the UI

1. In the sidebar, click **Test Playground** (⚡ icon)
2. Paste your API key: `ari-test-key-001`
3. Pick a template — e.g. **LLM Agent**
4. Select the matching workflow from the dropdown — e.g. `[Demo] LLM Agent`
5. Click **Send Test Execution**

On success you'll see:
```
✓  Execution recorded!
    run_id: abc-123-def-456
    nodes_tracked: 1
```

Click **View Execution →** to open the execution detail page.

### 1.6 — Send a Test Execution from the CLI

```bash
cd backend
python -m scripts.send_test_execution --type llm    # single LLM call
python -m scripts.send_test_execution --type rag     # embed → search → synthesis
python -m scripts.send_test_execution --type tool    # router → tool → synthesizer
python -m scripts.send_test_execution --type multi    # 4-node pipeline
```

The CLI authenticates via email/password, generates an API key, then POSTs to the webhook. All four share the same API key (`ari-test-key-001` from the seed).

### 1.7 — Verify in the Dashboard

After sending executions, open **Dashboard** — you'll see:
- Token trend chart populated
- Cost breakdown card with totals
- Inefficiency score
- Run history table in the bottom half

Click any run in the table to open **ExecutionDetail** and inspect per-node token usage, latency, and cost.

---

## 2 · n8n Integration

n8n can forward every workflow execution to ARI automatically.

### 2.1 — Start n8n (Docker)

```yaml
# docker-compose.yml
version: "3"
services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=adminpass
      - N8N_HOST=http://localhost:5678
      - WEBHOOK_URL=http://localhost:5678/
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=localhost
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=n8npass
    volumes:
      - n8n_data:/home/node/.n8n

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: n8n
      POSTGRES_USER: n8n
      POSTGRES_PASSWORD: n8npass
    volumes:
      - n8n_pgdata:/var/lib/postgresql/data

volumes:
  n8n_data:
  n8n_pgdata:
```

```bash
docker-compose up -d
# Open http://localhost:5678 → create your n8n credentials
```

### 2.2 — Create an ARI Workflow in the Dashboard

1. Go to **Workflows** → **Add Workflow**
2. Give it a name, e.g. "Production LLM Agent"
3. Copy the workflow ID (shown after creation)

### 2.3 — Add an HTTP Request Node in n8n

In your n8n workflow, add an **HTTP Request** node at the end (or after your LLM node):

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `https://your-ari-domain.com/api/webhook/n8n` |
| Authentication | `Header Authentication` |
| Name | `X-API-Key` |
| Value | `your-api-key-from-settings` |

**Body Content Type**: `JSON`

**Body** (example for an OpenAI LLM node named `GPT-4o Completion`):

```json
{
  "executionId": "{{ $json.executionId }}",
  "workflowId": "{{ $workflow.id }}",
  "status": "{{ $node.GPT_4o_Completion.json.status }}",
  "triggeredBy": "n8n_user",
  "startedAt": "{{ $now.toISO() }}",
  "finishedAt": "{{ $now.toISO() }}",
  "nodes": [
    {
      "nodeName": "GPT-4o Completion",
      "nodeType": "llm",
      "model": "gpt-4o",
      "provider": "openai",
      "promptTokens": {{ $node.GPT_4o_Completion.json.usage.prompt_tokens }},
      "completionTokens": {{ $node.GPT_4o_Completion.json.usage.completion_tokens }},
      "totalTokens": {{ $node.GPT_4o_Completion.json.usage.total_tokens }},
      "costUsd": {{ $node.GPT_4o_Completion.json.cost }},
      "latencyMs": {{ $node.GPT_4o_Completion.json.latency }}
    }
  ]
}
```

> Replace the placeholder values with expressions that match your n8n workflow's actual data structure.

### 2.4 — Test the Integration

1. Run the n8n workflow manually
2. Check ARI's **Dashboard** — the new execution should appear
3. Verify token counts and cost match what n8n logged

---

## 3 · Custom Adapter Payload Reference

The **Custom webhook** (`/api/webhook/custom`) accepts any JSON payload. Use it to integrate platforms not natively supported, or to send test data directly.

### Endpoint

```
POST /api/webhook/custom
Content-Type: application/json
X-API-Key: your-api-key
```

### Minimal Payload

```json
{
  "workflow_id": "your-workflow-id",
  "nodes": [
    {
      "node_name": "GPT-4o Completion",
      "model": "gpt-4o",
      "prompt_tokens": 1500,
      "completion_tokens": 500,
      "cost_usd": 0.01,
      "latency_ms": 2500
    }
  ]
}
```

### Full Payload Schema

```json
{
  "workflow_id": "string (required) — matches Workflow.n8n_workflow_id or Workflow.id",
  "execution_id": "string (optional) — defaults to auto-generated UUID",
  "status": "string (optional) — 'success' | 'failed' | 'running', default: 'success'",
  "triggered_by": "string (optional) — who/what triggered this run",
  "started_at": "ISO 8601 datetime string (optional)",
  "finished_at": "ISO 8601 datetime string (optional)",

  "nodes": [
    {
      "node_name": "string (required) — display name of the node",
      "node_type": "string (optional) — 'llm' | 'embedding' | 'search' | 'tool' | 'transform' | 'other', default: 'other'",
      "model": "string (optional) — e.g. 'gpt-4o', 'claude-3-5-sonnet-20241022'",
      "provider": "string (optional) — e.g. 'openai', 'anthropic', 'pinecone', 'serpapi', 'bash'",
      "prompt_tokens": "integer (optional, default: 0)",
      "completion_tokens": "integer (optional, default: 0)",
      "total_tokens": "integer (optional) — auto-computed if omitted",
      "cost_usd": "float (optional, default: 0.0)",
      "latency_ms": "integer (optional) — node execution time in milliseconds",
      "error_message": "string (optional) — populated if node failed"
    }
  ]
}
```

### Response

```json
{
  "status": "recorded",
  "run_id": "uuid-of-created-run",
  "workflow": "Workflow Name",
  "platform": "custom",
  "execution_id": "playground-1234567890",
  "nodes_tracked": 3,
  "events_tracked": 0,
  "total_tokens": 4550,
  "total_cost_usd": 0.0166
}
```

### Error Responses

| HTTP | Meaning | Fix |
|---|---|---|
| `401` | Invalid or revoked API key | Check your X-API-Key header |
| `422` | Malformed JSON | Validate the payload against the schema |
| `200 { "status": "skipped" }` | Workflow not registered | Add the workflow in ARI dashboard first |

---

## 4 · Understanding the Data Flow

```
[Your Platform]
     │
     │ POST /api/webhook/{n8n|make|zapier|custom}
     │ X-API-Key: your-api-key
     ▼
[Webhook Router — app/routers/webhook.py]
     │
     │ validate_api_key() → lookup ApiKey record
     │ adapter.normalize(payload) → StandardExecution dataclass
     │
     ▼
[process_execution() — shared by all platforms]
     │
     ├─► Match workflow by id OR n8n_workflow_id
     │
     ├─► Create Run record
     │
     ├─► Create TokenUsage record per node
     │
     └─► background_tasks.add_task(run_alert_checks_background)
          └─► Opens own DB session
               ├─► check_and_fire_alerts() — threshold + spike detection
               └─► check_inactivity_alerts()
               └─► Commit
               └─► rollback on error

     └─► background_tasks.add_task(run_security_analysis_background)
          └─► Opens own DB session
               ├─► SecurityEngine.analyze_execution() → SecurityFinding records
               ├─► PolicyEvaluator.evaluate() → governance action per finding
               └─► AuditLog entries
               └─► Commit
               └─► rollback on error
```

The webhook returns immediately after creating the Run + TokenUsage records. Alert checks and security analysis run asynchronously in background tasks, each with its own database session.

---

## 5 · CLI Reference

### seed_test_data.py

```bash
cd backend && python -m scripts.seed_test_data
```

Creates (or skips existing):
- Tenant: `ari-test-tenant` (UUID `00000000-0000-0000-0000-000000000001`)
- User: `test@ari.local` / `testpassword123` (UUID `00000000-0000-0000-0000-000000000002`)
- API key: `ari-test-key-001`
- Workflows:
  - `wf-llm-demo-001` → "LLM Agent Demo"
  - `wf-rag-demo-001` → "RAG Pipeline Demo"
  - `wf-tool-demo-001` → "Tool Calling Demo"

### send_test_execution.py

```bash
cd backend && python -m scripts.send_test_execution [options]
```

| Option | Description |
|---|---|
| `--type llm` | Single GPT-4o completion (default) |
| `--type rag` | Embed → vector search → synthesis (3 nodes) |
| `--type tool` | Router → web search → synthesizer (3 nodes) |
| `--type multi` | 4-node pipeline with Claude + bash |
| `--url URL` | Override backend base URL (default: `http://localhost:8000`) |
| `--email EMAIL` | Override auth email (default: `test@ari.local`) |
| `--password PASS` | Override auth password |

The CLI creates a fresh API key per run via `POST /api/keys/generate`, then POSTs to `/api/webhook/custom`.
