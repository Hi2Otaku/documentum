import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DispositionAction(str, __import__("enum").Enum):
    ARCHIVE = "archive"
    DELETE = "delete"


class RetentionPolicy(BaseModel):
    __tablename__ = "retention_policies"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    disposition_action: Mapped[str] = mapped_column(
        Enum(DispositionAction, name="dispositionaction"),
        nullable=False,
    )

    assignments: Mapped[list["DocumentRetention"]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
    )


class DocumentRetention(BaseModel):
    __tablename__ = "document_retentions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("retention_policies.id"), nullable=False
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    policy: Mapped["RetentionPolicy"] = relationship(back_populates="assignments")


class LegalHold(BaseModel):
    __tablename__ = "legal_holds"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    placed_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=False
    )
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
