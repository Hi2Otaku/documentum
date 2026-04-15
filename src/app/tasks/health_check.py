"""Celery periodic task -- run health checks and create alert notifications."""
from __future__ import annotations

import asyncio
import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.health_check.run_health_checks")
def run_health_checks() -> dict:
    """Run all health checks, evaluate alert rules, and notify superusers on triggers.

    This task is scheduled by Celery Beat every 60 seconds.
    """
    return asyncio.run(_run_health_checks_async())


async def _run_health_checks_async() -> dict:
    from sqlalchemy import select

    from app.core.database import create_task_session_factory
    from app.models.user import User
    from app.services.monitoring_service import (
        check_all_health,
        evaluate_alert_rules,
        get_system_metrics,
    )
    from app.services.notification_service import create_notification

    health = await check_all_health()
    metrics = await get_system_metrics()

    session_factory = create_task_session_factory()
    triggered: list[str] = []

    async with session_factory() as db:
        try:
            triggered = await evaluate_alert_rules(db, health, metrics)

            if triggered:
                # Find all superusers to notify
                result = await db.execute(
                    select(User).where(
                        User.is_superuser == True,  # noqa: E712
                        User.is_active == True,  # noqa: E712
                    )
                )
                superusers = list(result.scalars().all())

                for rule_name in triggered:
                    for user in superusers:
                        await create_notification(
                            db,
                            user_id=user.id,
                            title=f"Alert triggered: {rule_name}",
                            message=f"Monitoring alert rule '{rule_name}' has been triggered.",
                            notification_type="system_alert",
                        )
                logger.warning(
                    "Health check triggered %d alert(s): %s",
                    len(triggered),
                    ", ".join(triggered),
                )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Error during health check alert evaluation")
            raise

    overall = health.status
    logger.info("Health check complete: %s (%d alerts triggered)", overall, len(triggered))
    return {
        "status": overall,
        "triggered_alerts": triggered,
        "component_count": len(health.components),
    }
