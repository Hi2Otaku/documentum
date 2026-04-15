"""Celery periodic task -- refresh process analytics cache."""
from __future__ import annotations

import asyncio
import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.analytics_refresh.refresh_analytics")
def refresh_analytics() -> dict:
    """Refresh analytics cache by computing all analytics queries and storing in Redis.

    Scheduled by Celery Beat every 600 seconds (10 minutes).
    """
    return asyncio.run(_refresh_async())


async def _refresh_async() -> dict:
    from app.core.database import create_task_session_factory
    from app.services.analytics_service import refresh_analytics_cache

    session_factory = create_task_session_factory()
    async with session_factory() as db:
        try:
            await refresh_analytics_cache(db)
            logger.info("Analytics cache refresh task completed")
            return {"status": "refreshed"}
        except Exception:
            logger.exception("Analytics cache refresh task failed")
            raise
