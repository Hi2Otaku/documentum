"""Notification service -- create, list, and manage in-app notifications."""
from __future__ import annotations

import json
import logging
import uuid

import redis.asyncio as aioredis
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import Notification

logger = logging.getLogger(__name__)

# Lazy-initialized Redis client for pub/sub notification delivery
_redis_client: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    """Return a lazily-initialized async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    message: str | None = None,
    notification_type: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> Notification:
    """Create and persist a new notification for a user."""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(notification)
    await db.flush()

    # Publish to Redis for SSE real-time delivery
    try:
        r = await _get_redis()
        payload = json.dumps({
            "id": str(notification.id),
            "user_id": str(user_id),
            "title": title,
            "message": message or "",
            "notification_type": notification_type,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id else None,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
        })
        await r.publish("notifications", payload)
    except Exception:
        logger.warning("Failed to publish notification to Redis, SSE delivery skipped", exc_info=True)

    return notification


async def list_notifications(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    is_read: bool | None = None,
) -> tuple[list[Notification], int]:
    """Return paginated notifications for a user.

    Returns (items, total_count).
    """
    base = select(Notification).where(
        Notification.user_id == user_id,
        Notification.is_deleted == False,  # noqa: E712
    )
    if is_read is not None:
        base = base.where(Notification.is_read == is_read)

    # Total count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginated items (newest first)
    items_q = (
        base.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(items_q)
    items = list(result.scalars().all())

    return items, total


async def get_unread_count(db: AsyncSession, *, user_id: uuid.UUID) -> int:
    """Return the count of unread notifications for a user."""
    q = select(func.count()).where(
        Notification.user_id == user_id,
        Notification.is_read == False,  # noqa: E712
        Notification.is_deleted == False,  # noqa: E712
    )
    return (await db.execute(q)).scalar_one()


async def mark_read(
    db: AsyncSession, *, notification_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Mark a single notification as read. Returns True if found and updated."""
    stmt = (
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.is_deleted == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    return result.rowcount > 0  # type: ignore[union-attr]


async def mark_all_read(db: AsyncSession, *, user_id: uuid.UUID) -> int:
    """Mark all unread notifications as read. Returns count of updated rows."""
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
            Notification.is_deleted == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    return result.rowcount  # type: ignore[union-attr]
