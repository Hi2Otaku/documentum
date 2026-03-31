import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import LifecycleState


class Document(BaseModel):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(255), default="application/octet-stream", nullable=False
    )
    custom_properties: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    locked_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=True
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_major_version: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    current_minor_version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    lifecycle_state: Mapped[str | None] = mapped_column(
        Enum(LifecycleState, name="lifecyclestate"),
        default=LifecycleState.DRAFT,
        nullable=True,
    )

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document",
        order_by="DocumentVersion.created_at",
    )


class DocumentVersion(BaseModel):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "major_version", "minor_version",
            name="uq_document_version",
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False
    )
    major_version: Mapped[int] = mapped_column(Integer, nullable=False)
    minor_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_size: Mapped[int] = mapped_column(Integer, nullable=False)
    minio_object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(255), default="application/octet-stream", nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="versions")
