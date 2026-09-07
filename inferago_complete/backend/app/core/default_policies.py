"""
Default policies seeded for new users on first run.

Governance philosophy:
- Critical findings (secrets, prompt injection) → BLOCK
- High severity + high risk → REQUIRE_REVIEW
- Medium severity → ALERT
- Low/info → ALLOW (informational only)
"""
import logging
import uuid
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import Policy
from app.models.user import User

logger = logging.getLogger(__name__)


def _default_policies_for(user_id: uuid.UUID) -> list[Policy]:
    return [
        Policy(
            id=uuid.uuid4(),
            user_id=user_id,
            name="Block critical security findings",
            description=(
                "Any critical severity finding (secrets leakage, prompt "
                "injection, jailbreak attempts) requires immediate blocking."
            ),
            enabled=True,
            applies_to_all_workflows=True,
            workflow_ids=None,
            conditions={
                "all": [{"field": "severity", "operator": "equals", "value": "critical"}],
            },
            action="BLOCK",
            priority=100,
            notify_on_trigger=True,
        ),
        Policy(
            id=uuid.uuid4(),
            user_id=user_id,
            name="Require review for high-risk findings",
            description=(
                "High severity findings OR any finding with risk score ≥ 75 "
                "must be reviewed by a human before continuing."
            ),
            enabled=True,
            applies_to_all_workflows=True,
            workflow_ids=None,
            conditions={
                "any": [
                    {"field": "severity",   "operator": "equals", "value": "high"},
                    {"field": "risk_score", "operator": "gte",    "value": 75},
                ],
            },
            action="REQUIRE_REVIEW",
            priority=80,
            notify_on_trigger=True,
        ),
        Policy(
            id=uuid.uuid4(),
            user_id=user_id,
            name="Alert on medium-severity findings",
            description=(
                "Medium-severity findings trigger an alert but do not block "
                "or require review."
            ),
            enabled=True,
            applies_to_all_workflows=True,
            workflow_ids=None,
            conditions={
                "all": [{"field": "severity", "operator": "equals", "value": "medium"}],
            },
            action="ALERT",
            priority=50,
            notify_on_trigger=False,
        ),
        Policy(
            id=uuid.uuid4(),
            user_id=user_id,
            name="Block PII exposure in LLM responses",
            description=(
                "Any PII exposure detector (email, SSN, phone, credit card) "
                "is treated as critical and blocked."
            ),
            enabled=True,
            applies_to_all_workflows=True,
            workflow_ids=None,
            conditions={
                "all": [
                    {
                        "field": "detector_id",
                        "operator": "in",
                        "value": ["pii_exposure"],
                    }
                ],
            },
            action="BLOCK",
            priority=90,
            notify_on_trigger=True,
        ),
        Policy(
            id=uuid.uuid4(),
            user_id=user_id,
            name="Block API key / secret leakage",
            description=(
                "Any secret or API key found in execution data is blocked."
            ),
            enabled=True,
            applies_to_all_workflows=True,
            workflow_ids=None,
            conditions={
                "all": [
                    {
                        "field": "detector_id",
                        "operator": "in",
                        "value": ["sensitive_data_exposure", "api_secret_leak"],
                    }
                ],
            },
            action="BLOCK",
            priority=95,
            notify_on_trigger=True,
        ),
    ]


async def seed_default_policies_for_user(
    db: AsyncSession, user: User
) -> list[Policy]:
    """
    Seed default policies for a user if they have none.
    Returns the list of policies created (empty if user already had some).
    """
    # Check if the specific default policies already exist for this user,
    # by name — not just whether any policy exists (which caused 3× duplication
    # when the seed ran on every server restart).
    for policy_name in [p.name for p in _default_policies_for(user.id)]:
        existing = await db.execute(
            select(Policy).where(Policy.user_id == user.id, Policy.name == policy_name).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            return []

    policies = _default_policies_for(user.id)
    for p in policies:
        db.add(p)
    await db.commit()
    logger.info(f"Seeded {len(policies)} default policies for user {user.id}")
    return policies


async def seed_default_policies_for_all_users(db: AsyncSession) -> int:
    """
    Seed default policies for every user that has none. Returns total count created.
    """
    users = (await db.execute(select(User))).scalars().all()
    total = 0
    for user in users:
        created = await seed_default_policies_for_user(db, user)
        total += len(created)
    return total
