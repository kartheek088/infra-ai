"""
Send a test execution to ARI via the /api/webhook/custom endpoint.

Usage:
    cd backend && python -m scripts.send_test_execution --type llm
    cd backend && python -m scripts.send_test_execution --type rag
    cd backend && python -m scripts.send_test_execution --type tool
    cd backend && python -m scripts.send_test_execution --type multi

Uses email/password auth (JWT) to call the webhook — no API key needed here.
"""
from __future__ import annotations

import argparse
import asyncio
import uuid
from datetime import datetime, timezone

import httpx

BASE_URL = "http://localhost:8000"

# ── Payload templates ─────────────────────────────────────────────────────────

LLM_PAYLOAD = {
    "workflow_id":   "wf-llm-demo-001",
    "execution_id": f"exec-llm-{uuid.uuid4().hex[:8]}",
    "status":        "success",
    "triggered_by":  "test-cli",
    "started_at":    datetime.now(timezone.utc).isoformat(),
    "finished_at":   datetime.now(timezone.utc).isoformat(),
    "nodes": [
        {
            "node_name":         "GPT-4o Completion",
            "node_type":         "llm",
            "model":             "gpt-4o",
            "provider":          "openai",
            "prompt_tokens":     1500,
            "completion_tokens": 500,
            "total_tokens":      2000,
            "cost_usd":          0.010,
            "latency_ms":        2500,
        }
    ],
}

RAG_PAYLOAD = {
    "workflow_id":   "wf-rag-demo-001",
    "execution_id": f"exec-rag-{uuid.uuid4().hex[:8]}",
    "status":        "success",
    "triggered_by":  "test-cli",
    "started_at":    datetime.now(timezone.utc).isoformat(),
    "finished_at":   datetime.now(timezone.utc).isoformat(),
    "nodes": [
        {
            "node_name":         "Embed Query",
            "node_type":         "embedding",
            "model":             "text-embedding-3-small",
            "provider":          "openai",
            "prompt_tokens":     50,
            "completion_tokens": 0,
            "total_tokens":      50,
            "cost_usd":          0.0001,
            "latency_ms":        150,
        },
        {
            "node_name":         "Vector Search",
            "node_type":         "search",
            "model":             "",
            "provider":          "pinecone",
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "total_tokens":      0,
            "cost_usd":          0.0,
            "latency_ms":        80,
        },
        {
            "node_name":         "GPT-4o Synthesis",
            "node_type":         "llm",
            "model":             "gpt-4o",
            "provider":          "openai",
            "prompt_tokens":     1200,
            "completion_tokens": 300,
            "total_tokens":      1500,
            "cost_usd":          0.0075,
            "latency_ms":        2000,
        },
    ],
}

TOOL_PAYLOAD = {
    "workflow_id":   "wf-tool-demo-001",
    "execution_id": f"exec-tool-{uuid.uuid4().hex[:8]}",
    "status":        "success",
    "triggered_by":  "test-cli",
    "started_at":    datetime.now(timezone.utc).isoformat(),
    "finished_at":   datetime.now(timezone.utc).isoformat(),
    "nodes": [
        {
            "node_name":         "Router LLM",
            "node_type":         "llm",
            "model":             "gpt-4o-mini",
            "provider":          "openai",
            "prompt_tokens":     100,
            "completion_tokens": 20,
            "total_tokens":      120,
            "cost_usd":          0.0001,
            "latency_ms":        500,
        },
        {
            "node_name":         "Web Search Tool",
            "node_type":         "tool",
            "model":             "",
            "provider":          "serpapi",
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "total_tokens":      0,
            "cost_usd":          0.005,
            "latency_ms":        1200,
        },
        {
            "node_name":         "Response Synthesizer",
            "node_type":         "llm",
            "model":             "gpt-4o",
            "provider":          "openai",
            "prompt_tokens":     800,
            "completion_tokens": 200,
            "total_tokens":      1000,
            "cost_usd":          0.005,
            "latency_ms":        1800,
        },
    ],
}

MULTI_PAYLOAD = {
    "workflow_id":   "wf-multi-001",
    "execution_id": f"exec-multi-{uuid.uuid4().hex[:8]}",
    "status":        "success",
    "triggered_by":  "test-cli",
    "started_at":    datetime.now(timezone.utc).isoformat(),
    "finished_at":   datetime.now(timezone.utc).isoformat(),
    "nodes": [
        {
            "node_name":         "Input Parser",
            "node_type":         "transform",
            "model":             "",
            "provider":          "",
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "total_tokens":      0,
            "cost_usd":          0.0,
            "latency_ms":        50,
        },
        {
            "node_name":         "Claude 3.5 Reasoning",
            "node_type":         "llm",
            "model":             "claude-3-5-sonnet-20241022",
            "provider":          "anthropic",
            "prompt_tokens":     2000,
            "completion_tokens": 800,
            "total_tokens":      2800,
            "cost_usd":          0.021,
            "latency_ms":        4000,
        },
        {
            "node_name":         "Code Executor",
            "node_type":         "tool",
            "model":             "",
            "provider":          "bash",
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "total_tokens":      0,
            "cost_usd":          0.0,
            "latency_ms":        1500,
        },
        {
            "node_name":         "Output Formatter",
            "node_type":         "transform",
            "model":             "",
            "provider":          "",
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "total_tokens":      0,
            "cost_usd":          0.0,
            "latency_ms":        100,
        },
    ],
}

PAYLOADS = {
    "llm":   LLM_PAYLOAD,
    "rag":   RAG_PAYLOAD,
    "tool":  TOOL_PAYLOAD,
    "multi": MULTI_PAYLOAD,
}


async def get_api_key(base_url: str, email: str, password: str) -> str:
    """Authenticate and return an API key for the user."""
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Register — idempotent, creates user if not exists
        reg_resp = await client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": "Test User"},
        )
        reg_resp.raise_for_status()
        print(f"  [auth] Registered / logged in as {email}")

        # Login to get JWT
        login_resp = await client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
        )
        login_resp.raise_for_status()
        token = login_resp.json()["access_token"]
        print("  [auth] Got JWT token")

        # Generate an API key
        headers = {"Authorization": f"Bearer {token}"}
        key_resp = await client.post("/api/keys/generate", headers=headers, json={"name": "CLI Test Key"})
        key_resp.raise_for_status()
        api_key = key_resp.json()["key"]
        print(f"  [auth] Got API key: {api_key[:20]}...")
        return api_key


async def send_execution(
    base_url: str,
    api_key: str,
    payload: dict,
) -> dict:
    """POST a test execution to the custom webhook."""
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        resp = await client.post(
            "/api/webhook/custom",
            json=payload,
            headers={"X-API-Key": api_key},
        )
        resp.raise_for_status()
        return resp.json()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test execution to ARI")
    parser.add_argument(
        "--type",
        choices=["llm", "rag", "tool", "multi"],
        default="llm",
        help="Execution template type (default: llm)",
    )
    parser.add_argument(
        "--url",
        default=BASE_URL,
        help=f"ARI backend base URL (default: {BASE_URL})",
    )
    parser.add_argument(
        "--email",
        default="test@ari.local",
        help="Email for auth (default: test@ari.local)",
    )
    parser.add_argument(
        "--password",
        default="testpassword123",
        help="Password for auth (default: testpassword123)",
    )
    args = parser.parse_args()

    payload = PAYLOADS[args.type]
    print(f"Sending {args.type} execution to {args.url}")
    print(f"  workflow_id : {payload['workflow_id']}")
    print(f"  execution_id: {payload['execution_id']}")
    print(f"  nodes       : {len(payload['nodes'])}")
    print()

    api_key = await get_api_key(args.url, args.email, args.password)

    result = await send_execution(args.url, api_key, payload)

    print()
    print("✓  Execution recorded!")
    print(f"    run_id        : {result.get('run_id')}")
    print(f"    workflow      : {result.get('workflow')}")
    print(f"    platform      : {result.get('platform')}")
    print(f"    total_tokens  : {result.get('total_tokens')}")
    print(f"    total_cost_usd: ${result.get('total_cost_usd'):.6f}")
    print(f"    nodes_tracked : {result.get('nodes_tracked')}")


if __name__ == "__main__":
    asyncio.run(main())
