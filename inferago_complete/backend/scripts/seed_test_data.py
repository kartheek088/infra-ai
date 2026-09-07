"""
Seed test data for ARI — no external services required.

Creates:
  - Tenant  : ari-test-tenant
  - User    : test@ari.local / testpassword123
  - API key : ari-test-key-001  (shown in the terminal output)
  - 3 Workflows with deterministic n8n_workflow_id values so the
    send_test_execution.py CLI and the Test Playground can reference them.

Run:
    cd backend && python -m scripts.seed_test_data

The script is idempotent — re-running it is safe.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.api_key import ApiKey
from app.models.workflow import Workflow
from app.core.security import hash_password


# ── Fixed IDs so other scripts / the Playground can hard-code these ──────────
TEST_TENANT_ID   = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_ID     = uuid.UUID("00000000-0000-0000-0000-000000000002")
TEST_API_KEY_STR = "ari-test-key-001"
TEST_EMAIL       = "test@ari.local"
TEST_PASSWORD    = "testpassword123"
TEST_TENANT_SLUG = "ari-test-tenant"


async def seed(db: AsyncSession) -> None:
    # ── 1. Tenant ─────────────────────────────────────────────────────────────
    result = await db.execute(select(Tenant).where(Tenant.id == TEST_TENANT_ID))
    tenant = result.scalar_one_or_none()
    if not tenant:
        tenant = Tenant(
            id=TEST_TENANT_ID,
            name="ARI Test Tenant",
            slug=TEST_TENANT_SLUG,
            plan="free",
            is_active=True,
        )
        db.add(tenant)
        print("✓  Created tenant  : ari-test-tenant")
    else:
        print("✓  Tenant already exists (skipping)")

    # ── 2. User ───────────────────────────────────────────────────────────────
    result = await db.execute(select(User).where(User.email == TEST_EMAIL))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            id=TEST_USER_ID,
            tenant_id=TEST_TENANT_ID,
            email=TEST_EMAIL,
            hashed_password=hash_password(TEST_PASSWORD),
            full_name="Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        print("✓  Created user    : test@ari.local / testpassword123")
    else:
        print("✓  User already exists (skipping)")

    # ── 3. API Key ────────────────────────────────────────────────────────────
    result = await db.execute(select(ApiKey).where(ApiKey.key == TEST_API_KEY_STR))
    api_key = result.scalar_one_or_none()
    if not api_key:
        api_key = ApiKey(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            key=TEST_API_KEY_STR,
            name="Test API Key",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(api_key)
        print("✓  Created API key : ari-test-key-001")
    else:
        print("✓  API key already exists (skipping)")

    # ── 4. Workflows ───────────────────────────────────────────────────────────
    workflows = [
        {
            "id":               uuid.UUID("00000000-0000-0000-0001-000000000001"),
            "name":             "LLM Agent Demo",
            "description":      "A simple LLM completion call — single node, tests token tracking.",
            "n8n_workflow_id":  "wf-llm-demo-001",
        },
        {
            "id":               uuid.UUID("00000000-0000-0000-0001-000000000002"),
            "name":             "RAG Pipeline Demo",
            "description":      "Embedding → vector search → synthesis. Three nodes cover the full RAG stack.",
            "n8n_workflow_id":  "wf-rag-demo-001",
        },
        {
            "id":               uuid.UUID("00000000-0000-0000-0001-000000000003"),
            "name":             "Tool Calling Demo",
            "description":      "Router LLM → external tool call → synthesizer. Tests tool and multi-node chains.",
            "n8n_workflow_id":  "wf-tool-demo-001",
        },
    ]

    for wf_data in workflows:
        result = await db.execute(
            select(Workflow).where(Workflow.n8n_workflow_id == wf_data["n8n_workflow_id"])
        )
        existing = result.scalar_one_or_none()
        if not existing:
            wf = Workflow(
                id=wf_data["id"],
                tenant_id=TEST_TENANT_ID,
                user_id=TEST_USER_ID,
                name=wf_data["name"],
                description=wf_data["description"],
                n8n_workflow_id=wf_data["n8n_workflow_id"],
                config={},
                created_at=datetime.now(timezone.utc),
            )
            db.add(wf)
            print(f"✓  Created workflow: {wf_data['name']}  (n8n_workflow_id={wf_data['n8n_workflow_id']})")
        else:
            print(f"✓  Workflow already exists: {wf_data['name']} (skipping)")

    await db.commit()
    print()
    print("=" * 60)
    print("  Seed complete! Use these values in the Test Playground:")
    print()
    print(f"  Email    : test@ari.local")
    print(f"  Password : testpassword123")
    print(f"  API key  : ari-test-key-001")
    print()
    print("  Workflow IDs (for Custom adapter payload):")
    print(f"    LLM Agent      : wf-llm-demo-001")
    print(f"    RAG Pipeline   : wf-rag-demo-001")
    print(f"    Tool Calling   : wf-tool-demo-001")
    print()
    print("  CLI sender:")
    print("    cd backend && python -m scripts.send_test_execution --type llm")
    print("=" * 60)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
