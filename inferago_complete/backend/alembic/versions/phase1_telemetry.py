"""phase1_telemetry

Revision ID: phase1_telemetry
Revises: 02ac1eac24d2
Create Date: 2026-09-07 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'phase1_telemetry'
down_revision: Union[str, None] = '02ac1eac24d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── runs: raw event log ──────────────────────────────────────────────
    op.add_column(
        'runs',
        sa.Column(
            'events_jsonb',
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text('NULL'),
            comment='Full raw event log from platform webhook — execution_triggered, node_started, node_finished, etc.',
        ),
    )
    op.create_index(
        'ix_runs_events_jsonb',
        'runs',
        [sa.text('(events_jsonb)')],
        postgresql_using='gin',
        if_not_exists=True,
    )

    # ── token_usage: richer per-node metadata ────────────────────────────
    op.add_column(
        'token_usage',
        sa.Column(
            'node_type',
            sa.String(64),
            nullable=True,
            server_default=sa.text('NULL'),
            comment='llm | http_request | trigger | transform | logic | data | other',
        ),
    )
    op.add_column(
        'token_usage',
        sa.Column(
            'event_type',
            sa.String(64),
            nullable=True,
            server_default=sa.text('NULL'),
            comment='execution_triggered | node_started | node_finished | execution_finished | execution_failed | ...',
        ),
    )
    op.add_column(
        'token_usage',
        sa.Column(
            'provider',
            sa.String(64),
            nullable=True,
            server_default=sa.text('NULL'),
            comment='openai | anthropic | azure | google | custom',
        ),
    )
    op.add_column(
        'token_usage',
        sa.Column(
            'error_message',
            sa.Text(),
            nullable=True,
            server_default=sa.text('NULL'),
        ),
    )
    op.add_column(
        'token_usage',
        sa.Column(
            'latency_ms',
            sa.Integer(),
            nullable=True,
            server_default=sa.text('NULL'),
        ),
    )
    op.add_column(
        'token_usage',
        sa.Column(
            'metadata',
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text('NULL'),
        ),
    )

    # Index for node_type + event_type lookups (security detection queries)
    op.create_index(
        'ix_token_usage_node_type_event_type',
        'token_usage',
        ['node_type', 'event_type'],
        if_not_exists=True,
    )
    op.create_index(
        'ix_token_usage_error_message',
        'token_usage',
        [sa.text("(error_message)")],
        postgresql_where=sa.text("error_message IS NOT NULL AND error_message <> ''"),
        if_not_exists=True,
    )

    # ── workflows: multi-tenancy & risk classification ───────────────────
    op.add_column(
        'workflows',
        sa.Column(
            'tenant_id',
            sa.UUID(),
            nullable=True,
            server_default=sa.text('NULL'),
            comment='Multi-tenancy grouping — null means personal workflow',
        ),
    )
    op.add_column(
        'workflows',
        sa.Column(
            'risk_level',
            sa.String(32),
            nullable=True,
            server_default=sa.text('NULL'),
            comment='low | medium | high | critical',
        ),
    )
    op.create_index(
        'ix_workflows_tenant_id',
        'workflows',
        ['tenant_id'],
        if_not_exists=True,
    )
    op.create_index(
        'ix_workflows_risk_level',
        'workflows',
        ['risk_level'],
        if_not_exists=True,
    )


def downgrade() -> None:
    # workflows
    op.drop_index('ix_workflows_risk_level', table_name='workflows', if_exists=True)
    op.drop_index('ix_workflows_tenant_id', table_name='workflows', if_exists=True)
    op.drop_column('workflows', 'risk_level')
    op.drop_column('workflows', 'tenant_id')

    # token_usage
    op.drop_index('ix_token_usage_error_message', table_name='token_usage', if_exists=True)
    op.drop_index('ix_token_usage_node_type_event_type', table_name='token_usage', if_exists=True)
    op.drop_column('token_usage', 'metadata')
    op.drop_column('token_usage', 'latency_ms')
    op.drop_column('token_usage', 'error_message')
    op.drop_column('token_usage', 'provider')
    op.drop_column('token_usage', 'event_type')
    op.drop_column('token_usage', 'node_type')

    # runs
    op.drop_index('ix_runs_events_jsonb', table_name='runs', if_exists=True)
    op.drop_column('runs', 'events_jsonb')
