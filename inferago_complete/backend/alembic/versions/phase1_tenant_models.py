"""Phase 1: Multi-tenancy — Tenant, Application, Event models + tenant_id on all tables.

Revision ID: phase1_tenant
Revises: phase1_telemetry
Create Date: 2025-01-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = "phase1_tenant"
down_revision: Union[str, None] = "phase1_telemetry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create tenants table ────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True),
        sa.Column("name",         sa.String(), nullable=False),
        sa.Column("slug",         sa.String(), nullable=False),
        sa.Column("plan",         sa.String(), nullable=False, server_default="free"),
        sa.Column("is_active",    sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    # ── 2. Create applications table ───────────────────────────────────────────
    op.create_table(
        "applications",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id",    UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name",         sa.String(), nullable=False),
        sa.Column("description",  sa.Text(), nullable=True),
        sa.Column("environment",  sa.String(), nullable=False, server_default="production"),
        sa.Column("is_active",   sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_applications_tenant_id", "applications", ["tenant_id"])

    # ── 3. Create events table ─────────────────────────────────────────────────
    op.create_table(
        "events",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id",    UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id",      UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("workflow_id",  UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=True),
        sa.Column("run_id",       UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=True),
        sa.Column("event_type",  sa.String(), nullable=False),
        sa.Column("component",    sa.String(), nullable=False),
        sa.Column("operation",   sa.String(), nullable=False),
        sa.Column("actor",       sa.String(), nullable=True),
        sa.Column("session_id",  sa.String(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload",     JSONB, nullable=True),
        sa.Column("severity",    sa.String(), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_events_tenant_id",     "events", ["tenant_id"])
    op.create_index("ix_events_user_id",      "events", ["user_id"])
    op.create_index("ix_events_workflow_id",  "events", ["workflow_id"])
    op.create_index("ix_events_run_id",       "events", ["run_id"])
    op.create_index("ix_events_event_type",   "events", ["event_type"])
    op.create_index("ix_events_session_id",   "events", ["session_id"])

    # ── 4. Add tenant_id to users ─────────────────────────────────────────────
    # Must drop the unique email constraint first, then add tenant_id + recreate unique
    op.add_column("users", sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False))
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    # After adding tenant_id, we need a unique constraint on (tenant_id, email)
    # Drop the existing unique constraint first
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.create_unique_constraint("uq_users_tenant_email", "users", ["tenant_id", "email"])

    # ── 5. Add tenant_id to workflows ────────────────────────────────────────
    op.add_column("workflows", sa.Column("tenant_id",      UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False))
    op.add_column("workflows", sa.Column("application_id", UUID(as_uuid=True), sa.ForeignKey("applications.id"), nullable=True))
    op.create_index("ix_workflows_tenant_id",      "workflows", ["tenant_id"])
    op.create_index("ix_workflows_application_id", "workflows", ["application_id"])

    # ── 6. Add tenant_id to audit_logs ───────────────────────────────────────
    op.add_column("audit_logs", sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False))
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])

    # ── 7. Add tenant_id to policies ──────────────────────────────────────────
    op.add_column("policies", sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False))
    op.create_index("ix_policies_tenant_id", "policies", ["tenant_id"])

    # ── 8. Add tenant_id to security_findings ────────────────────────────────
    op.add_column("security_findings", sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False))
    op.create_index("ix_security_findings_tenant_id", "security_findings", ["tenant_id"])

    # ── 9. Add tenant_id to runs ──────────────────────────────────────────────
    op.add_column("runs", sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False))
    op.create_index("ix_runs_tenant_id", "runs", ["tenant_id"])

    # ── 10. Add tenant_id to token_usage ──────────────────────────────────────
    op.add_column("token_usage", sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False))
    op.create_index("ix_token_usage_tenant_id", "token_usage", ["tenant_id"])

    # ── 11. Add tenant_id to rag_metrics ───────────────────────────────────────
    op.add_column("rag_metrics", sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False))
    op.create_index("ix_rag_metrics_tenant_id", "rag_metrics", ["tenant_id"])

    # ── 12. Add tenant_id to api_keys ──────────────────────────────────────────
    op.add_column("api_keys", sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False))
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])

    # ── 13. Add tenant_id to alerts ────────────────────────────────────────────
    op.add_column("alerts", sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False))
    op.create_index("ix_alerts_tenant_id", "alerts", ["tenant_id"])


def downgrade() -> None:
    op.drop_column("alerts",          "tenant_id")
    op.drop_column("api_keys",         "tenant_id")
    op.drop_column("rag_metrics",      "tenant_id")
    op.drop_column("token_usage",      "tenant_id")
    op.drop_column("runs",             "tenant_id")
    op.drop_column("security_findings", "tenant_id")
    op.drop_column("policies",         "tenant_id")
    op.drop_column("audit_logs",       "tenant_id")
    op.drop_column("workflows",        "application_id")
    op.drop_column("workflows",       "tenant_id")
    op.drop_column("users",            "tenant_id")
    op.drop_table("events")
    op.drop_table("applications")
    op.drop_table("tenants")
