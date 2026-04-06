"""Notification model for in-app notifications."""
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    notification_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    entity_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), nullable=True,
    )
