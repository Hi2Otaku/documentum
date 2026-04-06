"""Event handlers that react to domain events.

Handlers are registered on module import, so this module must be imported
at application startup (done in main.py lifespan).
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import DomainEvent
from app.services.event_bus import event_bus
from app.services import notification_service

logger = logging.getLogger(__name__)


@event_bus.on("work_item.assigned")
async def _notify_work_item_assigned(db: AsyncSession, event: DomainEvent) -> None:
    """Create an in-app notification when a work item is assigned."""
    payload = event.payload or {}
    performer_id = payload.get("performer_id")
    if not performer_id:
        return

    import uuid
    notification = await notification_service.create_notification(
        db,
        user_id=uuid.UUID(performer_id),
        title="New task assigned",
        message=payload.get("activity_name", "A new task has been assigned to you."),
        notification_type="work_item.assigned",
        entity_type="work_item",
        entity_id=event.entity_id,
    )

    # Dispatch email notification via Celery
    from app.tasks.notification import send_notification_email
    send_notification_email.delay(str(notification.id))


@event_bus.on("work_item.delegated")
async def _notify_work_item_delegated(db: AsyncSession, event: DomainEvent) -> None:
    """Create an in-app notification when a work item is delegated."""
    payload = event.payload or {}
    delegate_id = payload.get("delegate_id")
    if not delegate_id:
        return

    import uuid
    notification = await notification_service.create_notification(
        db,
        user_id=uuid.UUID(delegate_id),
        title="Task delegated to you",
        message=payload.get("activity_name", "A task has been delegated to you."),
        notification_type="work_item.delegated",
        entity_type="work_item",
        entity_id=event.entity_id,
    )

    # Dispatch email notification via Celery
    from app.tasks.notification import send_notification_email
    send_notification_email.delay(str(notification.id))
