"""phase2_3_security_governance

Phase 2: Security Finding model
Phase 3: Policy and Audit Log models

Revision ID: phase2_3_security_governance
Revises: phase1_telemetry
Create Date: 2026-09-07 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'phase2_3_security_governance'
down_revision: Union[str, None] = 'phase1_telemetry'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── policies (must be first — security_findings FKs to it) ─────────────
    op.create_table(
        'policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name',      sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled',   sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('applies_to_all_workflows', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('workflow_ids', postgresql.JSONB(), nullable=True, server_default=sa.text('NULL')),
        sa.Column('conditions', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('action',    sa.String(32), nullable=False),
        sa.Column('priority',  sa.Integer(),  nullable=False, server_default=sa.text('0')),
        sa.Column('notify_on_trigger', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.Column('notification_channels', postgresql.JSONB(), nullable=True, server_default=sa.text('NULL')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_policies_user_id',          'policies', ['user_id'])
    op.create_index('ix_policies_user_enabled',     'policies', ['user_id', 'enabled'])
    op.create_index('ix_policies_priority',         'policies', ['priority'])

    # ── security_findings ────────────────────────────────────────────────
    op.create_table(
        'security_findings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id',       postgresql.UUID(as_uuid=True), sa.ForeignKey('runs.id',       ondelete='CASCADE'), nullable=False),
        sa.Column('workflow_id',  postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id',      postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id',     ondelete='CASCADE'), nullable=False),
        sa.Column('detector_id',    sa.String(64),  nullable=False),
        sa.Column('detector_name',  sa.String(128), nullable=False),
        sa.Column('severity',       sa.String(16),  nullable=False),
        sa.Column('confidence',     sa.Float(),     nullable=False, server_default=sa.text('1.0')),
        sa.Column('title',          sa.String(256), nullable=False),
        sa.Column('description',    sa.Text(),      nullable=True),
        sa.Column('finding_data',   postgresql.JSONB(), nullable=True, server_default=sa.text('NULL')),
        sa.Column('risk_score',     sa.Integer(),   nullable=False, server_default=sa.text('0')),
        sa.Column('risk_factors',   postgresql.JSONB(), nullable=True, server_default=sa.text('NULL')),
        sa.Column('governance_action', sa.String(32), nullable=True, server_default=sa.text('NULL')),
        sa.Column('policy_id',         postgresql.UUID(as_uuid=True), sa.ForeignKey('policies.id', ondelete='SET NULL'), nullable=True),
        sa.Column('policy_name',       sa.String(256), nullable=True),
        sa.Column('reviewed',    sa.String(16),  nullable=False, server_default=sa.text("'pending'")),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('node_name',   sa.String(256), nullable=True),
        sa.Column('provider',    sa.String(64),  nullable=True),
        sa.Column('created_at',  sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_security_findings_run_id',     'security_findings', ['run_id'])
    op.create_index('ix_security_findings_workflow_id','security_findings', ['workflow_id'])
    op.create_index('ix_security_findings_user_id',    'security_findings', ['user_id'])
    op.create_index('ix_security_findings_severity',   'security_findings', ['severity'])
    op.create_index('ix_security_findings_risk_score', 'security_findings', ['risk_score'])
    op.create_index('ix_security_findings_reviewed',   'security_findings', ['reviewed'])
    op.create_index('ix_security_findings_detector_id','security_findings', ['detector_id'])
    op.create_index('ix_security_findings_user_created','security_findings', ['user_id', 'created_at'])

    # ── audit_logs ────────────────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_type', sa.String(32), nullable=False),
        sa.Column('entity_id',   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action',      sa.String(64), nullable=False),
        sa.Column('performed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('snapshot',   postgresql.JSONB(), nullable=True, server_default=sa.text('NULL')),
        sa.Column('note',       sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_audit_logs_user_id',          'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_user_created',     'audit_logs', ['user_id', 'created_at'])
    op.create_index('ix_audit_logs_entity_type_id',   'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('ix_audit_logs_action',           'audit_logs', ['action'])


def downgrade() -> None:
    op.drop_index('ix_audit_logs_action',         table_name='audit_logs', if_exists=True)
    op.drop_index('ix_audit_logs_entity_type_id', table_name='audit_logs', if_exists=True)
    op.drop_index('ix_audit_logs_user_created',   table_name='audit_logs', if_exists=True)
    op.drop_index('ix_audit_logs_user_id',        table_name='audit_logs', if_exists=True)
    op.drop_table('audit_logs')

    # security_findings FKs to policies, so drop it first
    op.drop_index('ix_security_findings_user_created','security_findings', if_exists=True)
    op.drop_index('ix_security_findings_detector_id','security_findings', if_exists=True)
    op.drop_index('ix_security_findings_reviewed',   'security_findings', if_exists=True)
    op.drop_index('ix_security_findings_risk_score', 'security_findings', if_exists=True)
    op.drop_index('ix_security_findings_severity',   'security_findings', if_exists=True)
    op.drop_index('ix_security_findings_user_id',    'security_findings', if_exists=True)
    op.drop_index('ix_security_findings_workflow_id','security_findings', if_exists=True)
    op.drop_index('ix_security_findings_run_id',     'security_findings', if_exists=True)
    op.drop_table('security_findings')

    op.drop_index('ix_policies_priority',     table_name='policies', if_exists=True)
    op.drop_index('ix_policies_user_enabled',table_name='policies', if_exists=True)
    op.drop_index('ix_policies_user_id',      table_name='policies', if_exists=True)
    op.drop_table('policies')
