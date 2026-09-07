"""
Policy evaluation engine — Phase 3.

Evaluates security findings against active policies and returns governance actions.
"""
import logging
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import Policy
from app.models.security_finding import SecurityFinding
from app.schemas.policy import PolicyConditionTree, PolicyCondition
from app.schemas.security_finding import SecurityFindingCreate

logger = logging.getLogger(__name__)


class PolicyEvaluator:
    """
    Matches a SecurityFinding against active policies for a user.
    Returns the highest-priority matching policy's action, or None.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(
        self,
        finding: SecurityFinding | SecurityFindingCreate,
        workflow_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> tuple[Optional[str], Optional[uuid.UUID], Optional[str]]:
        """
        Returns (governance_action, policy_id, policy_name) for the first
        matching policy, or (None, None, None) if no policy matches.

        Governance actions: ALLOW | ALERT | REQUIRE_REVIEW | BLOCK

        The owning user is read from the finding itself when it has been
        persisted (SecurityFinding). For pre-persist SecurityFindingCreate
        objects, callers MUST pass tenant_id so we can scope the policy
        search — this keeps us from leaking cross-tenant rules.
        """
        # Persisted finding: scope by tenant + user (multi-tenant safe)
        # Pre-persist finding: must have tenant_id provided
        if isinstance(finding, SecurityFinding):
            scope_user_id   = finding.user_id
            scope_tenant_id = finding.tenant_id
        else:
            if tenant_id is None:
                logger.warning(
                    "PolicyEvaluator.evaluate called with SecurityFindingCreate "
                    "and no tenant_id — skipping policy matching."
                )
                return None, None, None
            scope_user_id   = None
            scope_tenant_id = tenant_id

        # Fetch enabled policies for this user/tenant, ordered by priority desc.
        # If we have a user_id, scope to user; if not (pre-persist path), scope
        # to tenant so we still enforce tenant isolation.
        conds = [Policy.enabled == True]  # noqa: E712
        if scope_user_id is not None:
            conds.append(Policy.user_id == scope_user_id)
        else:
            conds.append(Policy.tenant_id == scope_tenant_id)

        q = (
            select(Policy)
            .where(*conds)
            .order_by(Policy.priority.desc())
        )
        result = await self.db.execute(q)
        policies = result.scalars().all()

        finding_dict = {
            "severity":     finding.severity,
            "detector_id":  finding.detector_id,
            "risk_score":   finding.risk_score,
            "node_name":    finding.node_name,
            "provider":     finding.provider,
        }

        for policy in policies:
            if not self._matches_workflow(policy, workflow_id):
                continue
            if self._matches_conditions(policy.conditions, finding_dict):
                return policy.action, policy.id, policy.name

        return None, None, None

    # ── internal matching helpers ─────────────────────────────────────────────

    @staticmethod
    def _matches_workflow(policy: Policy, workflow_id: uuid.UUID) -> bool:
        if policy.applies_to_all_workflows:
            return True
        if policy.workflow_ids is None:
            return False
        return str(workflow_id) in policy.workflow_ids

    @staticmethod
    def _matches_conditions(conditions: dict, finding: dict) -> bool:
        """
        Evaluate a condition tree (all/any) against finding fields.
        """
        tree = conditions or {}
        all_conds = tree.get("all", [])
        any_conds = tree.get("any", [])

        # AND: all "all" conditions must match
        if all_conds:
            for cond in all_conds:
                if not _eval_condition(cond, finding):
                    return False

        # OR: at least one "any" condition must match
        if any_conds:
            if not any(_eval_condition(c, finding) for c in any_conds):
                return False

        return True


def _eval_condition(cond: dict, finding: dict) -> bool:
    """
    Evaluate a single condition against a finding dict.
    cond keys: field, operator, value
    """
    field    = cond.get("field", "")
    operator = cond.get("operator", "")
    value    = cond.get("value")

    field_val = finding.get(field, "")

    op = operator.lower()
    if op == "equals":
        return str(field_val) == str(value)
    if op == "not_equals":
        return str(field_val) != str(value)
    if op == "in":
        return str(field_val) in (value or [])
    if op == "not_in":
        return str(field_val) not in (value or [])
    if op == "gt":
        return float(field_val) > float(value)
    if op == "lt":
        return float(field_val) < float(value)
    if op == "gte":
        return float(field_val) >= float(value)
    if op == "lte":
        return float(field_val) <= float(value)
    if op == "contains":
        return str(value) in str(field_val)

    logger.warning(f"Unknown operator: {operator}")
    return False
