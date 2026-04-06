"""Domain event bus -- emit, persist, and dispatch events.

Usage:
    from app.services.event_bus import event_bus

    await event_bus.emit(
        db=session,
        event_type="workflow.started",
        entity_type="workflow_instance",
        entity_id=instance.id,
        actor_id=current_user.id,
        payload={"template_name": template.name},
    )

Handlers are registered with @event_bus.on("event.type") and called
synchronously (in-process) after the event is persisted.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Any, Callable, Coroutine

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import DomainEvent

logger = logging.getLogger(__name__)

# Type alias for async event handlers
EventHandler = Callable[[AsyncSession, DomainEvent], Coroutine[Any, Any, None]]


class EventBus:
    """In-process async event bus with persistent storage."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event_type: str) -> Callable[[EventHandler], EventHandler]:
        """Decorator to register an async handler for an event type."""
        def decorator(fn: EventHandler) -> EventHandler:
            self._handlers[event_type].append(fn)
            return fn
        return decorator

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Imperatively subscribe a handler to an event type."""
        self._handlers[event_type].append(handler)

    async def emit(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> DomainEvent:
        """Persist a domain event and dispatch to registered handlers."""
        event = DomainEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            payload=payload,
        )
        db.add(event)
        await db.flush()  # ensure event.id is available for handlers

        # Dispatch to registered handlers
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(db, event)
            except Exception:
                logger.exception(
                    "Event handler %s failed for event %s",
                    handler.__name__,
                    event_type,
                )

        return event


# Singleton event bus instance
event_bus = EventBus()
