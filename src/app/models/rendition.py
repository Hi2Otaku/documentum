import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import RenditionStatus, RenditionType


class Rendition(BaseModel):
    __tablename__ = "renditions"

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("document_versions.id"), nullable=False, index=True
    )
    rendition_type: Mapped[str] = mapped_column(
        Enum(RenditionType, name="renditiontype", create_type=False), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(RenditionStatus, name="renditionstatus", create_type=False),
        default=RenditionStatus.PENDING,
        nullable=False,
    )
    minio_object_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    content_type: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    content_size: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    document_version: Mapped["DocumentVersion"] = relationship(  # noqa: F821
        back_populates="renditions"
    )
