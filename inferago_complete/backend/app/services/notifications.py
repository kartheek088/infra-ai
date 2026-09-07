import httpx
from app.core.utils import to_uuid


async def send_slack_alert(webhook_url: str, workflow_name: str, message: str, platform: str = "n8n"):
    """Send a Slack notification when an alert fires."""
    payload = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": f"ARI Alert — {workflow_name}"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Platform:*\n{platform}"},
                {"type": "mrkdwn", "text": f"*Alert:*\n{message}"},
            ]},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "ARI — AI Runtime Intelligence"}]},
        ]
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=payload, timeout=5.0)
    except Exception:
        pass


async def check_and_fire_alerts(
    workflow_id: str,
    workflow_name: str,
    user_id: str,
    run_cost: float,
    total_tokens: int,
    avg_cost: float,
    avg_tokens: float,
    error_rate: float,
    platform: str,
    db,
) -> None:
    """
    Check all active alerts and fire those triggered by the latest run.
    Only alerts belonging to the authenticated user are evaluated — this
    prevents cross-tenant alert leakage in multi-user deployments.

    Alert types handled:
      cost_threshold → run cost exceeded a fixed USD value
      token_spike    → tokens are X times above the average (threshold = multiplier e.g. 2.5)
      error_rate     → % of recent runs that failed (threshold = 0.0-1.0 e.g. 0.2 = 20%)
    """
    from sqlalchemy import select
    from app.models.alert import Alert
    from datetime import datetime

    wf_uuid = to_uuid(workflow_id)
    uid_uuid = to_uuid(user_id)
    result = await db.execute(
        select(Alert).where(
            Alert.workflow_id == wf_uuid,
            Alert.user_id == uid_uuid,
            Alert.is_active == True,
        )
    )
    alerts = result.scalars().all()

    for alert in alerts:
        triggered = False
        message   = ""

        # ── Cost threshold ─────────────────────────────────────────────
        if alert.alert_type == "cost_threshold" and run_cost > alert.threshold_value:
            triggered = True
            message   = (
                f"Run cost ${run_cost:.4f} exceeded your threshold of ${alert.threshold_value:.2f}. "
                f"Platform: {platform}"
            )

        # ── Token spike ────────────────────────────────────────────────
        elif alert.alert_type == "token_spike" and avg_tokens > 0:
            ratio = total_tokens / avg_tokens
            if ratio >= alert.threshold_value:
                triggered = True
                message   = (
                    f"Token spike! This run used {total_tokens:,} tokens — "
                    f"{ratio:.1f}x your average of {int(avg_tokens):,}. "
                    f"Platform: {platform}"
                )

        # ── Error rate ─────────────────────────────────────────────────
        elif alert.alert_type == "error_rate" and error_rate >= alert.threshold_value:
            triggered = True
            message   = (
                f"Error rate alert! {error_rate*100:.0f}% of recent runs failed — "
                f"exceeds your threshold of {alert.threshold_value*100:.0f}%."
            )

        if triggered:
            alert.last_triggered_at = datetime.utcnow()
            if alert.slack_webhook_url:
                await send_slack_alert(alert.slack_webhook_url, workflow_name, message, platform)

    await db.commit()


async def check_inactivity_alerts(workflow_id: str, workflow_name: str, db) -> None:
    """
    Check inactivity alerts — fires if workflow silent longer than threshold hours.
    Call this from the dashboard endpoint or a background scheduler.
    """
    from sqlalchemy import select
    from app.models.alert import Alert
    from app.models.run import Run
    from datetime import datetime

    wf_uuid = to_uuid(workflow_id)
    result = await db.execute(
        select(Alert).where(
            Alert.workflow_id == wf_uuid,
            Alert.alert_type == "inactivity",
            Alert.is_active == True,
        )
    )
    alerts = result.scalars().all()
    if not alerts:
        return

    last_run_result = await db.execute(
        select(Run)
        .where(Run.workflow_id == wf_uuid)
        .order_by(Run.created_at.desc())
        .limit(1)
    )
    last_run = last_run_result.scalar_one_or_none()

    for alert in alerts:
        if not last_run or not last_run.created_at:
            continue

        hours_silent = (datetime.utcnow() - last_run.created_at.replace(tzinfo=None)).total_seconds() / 3600
        if hours_silent >= alert.threshold_value:
            message = (
                f"Inactivity alert! Workflow has been silent for {hours_silent:.0f} hours. "
                f"Last run: {last_run.created_at.strftime('%Y-%m-%d %H:%M UTC')}. "
                f"Expected: every {alert.threshold_value:.0f} hours."
            )
            alert.last_triggered_at = datetime.utcnow()
            if alert.slack_webhook_url:
                await send_slack_alert(alert.slack_webhook_url, workflow_name, message)

    await db.commit()


async def check_budget_alerts(workflow_id: str, workflow_name: str, db) -> None:
    """
    Check daily and monthly budget alerts.
    Call this from a scheduled job or after each run.
    """
    from sqlalchemy import select
    from app.models.alert import Alert
    from app.models.run import Run, TokenUsage
    from datetime import datetime, timedelta

    wf_uuid = to_uuid(workflow_id)
    result = await db.execute(
        select(Alert).where(
            Alert.workflow_id == wf_uuid,
            Alert.alert_type.in_(["daily_budget", "monthly_budget"]),
            Alert.is_active == True,
        )
    )
    alerts = result.scalars().all()
    if not alerts:
        return

    now   = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get today's runs
    day_runs_result = await db.execute(
        select(Run).where(Run.workflow_id == wf_uuid, Run.created_at >= today)
    )
    day_run_ids = [r.id for r in day_runs_result.scalars().all()]

    # Get this month's runs
    month_runs_result = await db.execute(
        select(Run).where(Run.workflow_id == wf_uuid, Run.created_at >= month_start)
    )
    month_run_ids = [r.id for r in month_runs_result.scalars().all()]

    # Calculate costs
    async def get_total_cost(run_ids):
        if not run_ids:
            return 0.0
        t_result = await db.execute(select(TokenUsage).where(TokenUsage.run_id.in_(run_ids)))
        return sum(t.cost_usd for t in t_result.scalars().all())

    day_cost   = await get_total_cost(day_run_ids)
    month_cost = await get_total_cost(month_run_ids)

    for alert in alerts:
        triggered = False
        message   = ""

        if alert.alert_type == "daily_budget" and day_cost >= alert.threshold_value:
            triggered = True
            message   = (
                f"Daily budget limit reached! Spent ${day_cost:.4f} today — "
                f"limit is ${alert.threshold_value:.2f}/day."
            )

        elif alert.alert_type == "monthly_budget" and month_cost >= alert.threshold_value:
            triggered = True
            message   = (
                f"Monthly budget limit reached! Spent ${month_cost:.4f} this month — "
                f"limit is ${alert.threshold_value:.2f}/month."
            )

        if triggered:
            alert.last_triggered_at = datetime.utcnow()
            if alert.slack_webhook_url:
                await send_slack_alert(alert.slack_webhook_url, workflow_name, message)

    await db.commit()
