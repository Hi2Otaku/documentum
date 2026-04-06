"""Domain event model for the persistent event bus."""
import uuid

from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON

from app.models.base import Base

from datetime import datetime, timezone


class DomainEvent(Base):
    """Persistent domain event for the event bus.

    Unlike BaseModel, this uses a minimal schema -- events are append-only
    and never soft-deleted or updated.
    """
    __tablename__ = "domain_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
    )
    entity_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), nullable=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), nullable=True,
    )
    payload: Mapped[dict | None] = mapped_column(
        JSON(), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
