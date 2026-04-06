import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import DispositionAction


class RetentionPolicy(BaseModel):
    __tablename__ = "retention_policies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    disposition_action: Mapped[str] = mapped_column(
        Enum(DispositionAction, name="dispositionaction"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    document_retentions: Mapped[list["DocumentRetention"]] = relationship(
        back_populates="retention_policy",
    )


class DocumentRetention(BaseModel):
    __tablename__ = "document_retentions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "retention_policy_id",
            name="uq_doc_retention_policy",
        ),
        Index("ix_doc_retentions_document_id", "document_id"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False
    )
    retention_policy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("retention_policies.id"), nullable=False
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    applied_by: Mapped[str] = mapped_column(String(255), nullable=False)

    document = relationship("Document")
    retention_policy: Mapped["RetentionPolicy"] = relationship(
        back_populates="document_retentions",
    )


class LegalHold(BaseModel):
    __tablename__ = "legal_holds"
    __table_args__ = (
        Index("ix_legal_holds_document_id", "document_id"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    placed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    released_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    document = relationship("Document")
