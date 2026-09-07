"""Phase 10: Reviews table + governance fields on runs.

Adds:
- reviews table: execution-level governance review queue
- runs.governance_decision, runs.max_risk_score, runs.review_required, runs.review_status
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "phase10"
down_revision = "phase8_ai_explanation"   # must match the last applied revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── reviews table ──────────────────────────────────────────────────────────
    op.create_table(
        "reviews",
        sa.Column("id",                       UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",                 UUID(as_uuid=True), nullable=False),
        sa.Column("run_id",                    UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id",               UUID(as_uuid=True), nullable=False),
        sa.Column("user_id",                   UUID(as_uuid=True), nullable=False),
        sa.Column("status",                    sa.String(16),      nullable=False, default="pending"),
        sa.Column("decision",                  sa.String(16),      nullable=True),
        sa.Column("max_risk_score",            sa.Integer(),       nullable=False, default=0),
        sa.Column("finding_count",             sa.Integer(),       nullable=False, default=0),
        sa.Column("top_finding_severity",     sa.String(16),      nullable=True),
        sa.Column("governing_policy_id",       UUID(as_uuid=True), nullable=True),
        sa.Column("governing_policy_name",     sa.String(256),     nullable=True),
        sa.Column("decision_by",               UUID(as_uuid=True), nullable=True),
        sa.Column("decision_at",               sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note",             sa.Text,            nullable=True),
        sa.Column("created_at",                sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",                sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reviews_tenant_id",    "reviews", ["tenant_id"])
    op.create_index("ix_reviews_run_id",       "reviews", ["run_id"])
    op.create_index("ix_reviews_workflow_id",  "reviews", ["workflow_id"])
    op.create_index("ix_reviews_user_id",      "reviews", ["user_id"])
    op.create_index("ix_reviews_status",       "reviews", ["status"])
    op.create_index("ix_reviews_user_created",    "reviews", ["user_id",       "created_at"])
    op.create_index("ix_reviews_workflow_created","reviews", ["workflow_id",   "created_at"])
    op.create_index("ix_reviews_tenant_created", "reviews", ["tenant_id",     "created_at"])

    op.create_foreign_key(
        "fk_reviews_tenant_id",   "reviews", "tenants",   ["tenant_id"],   ["id"]
    )
    op.create_foreign_key(
        "fk_reviews_run_id",      "reviews", "runs",      ["run_id"],      ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_reviews_workflow_id", "reviews", "workflows", ["workflow_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_reviews_user_id",     "reviews", "users",     ["user_id"],     ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_reviews_decision_by", "reviews", "users",     ["decision_by"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_reviews_policy_id",  "reviews", "policies",  ["governing_policy_id"], ["id"], ondelete="SET NULL"
    )

    # ── governance columns on runs ─────────────────────────────────────────────
    op.add_column("runs",    sa.Column("governance_decision", sa.String(16),  nullable=True))
    op.add_column("runs",    sa.Column("max_risk_score",      sa.Integer(),   nullable=True))
    op.add_column("runs",    sa.Column("review_required",     sa.String(1),   nullable=True, default="n"))
    op.add_column("runs",    sa.Column("review_status",       sa.String(16),  nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "review_status")
    op.drop_column("runs", "review_required")
    op.drop_column("runs", "max_risk_score")
    op.drop_column("runs", "governance_decision")

    op.drop_table("reviews")
