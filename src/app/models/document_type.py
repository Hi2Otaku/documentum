import uuid

from sqlalchemy import ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DocumentType(BaseModel):
    __tablename__ = "document_types"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    parent_type_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("document_types.id"), nullable=True
    )

    parent_type: Mapped["DocumentType | None"] = relationship(
        "DocumentType",
        remote_side="DocumentType.id",
        back_populates="children",
        lazy="selectin",
        foreign_keys=[parent_type_id],
    )
    children: Mapped[list["DocumentType"]] = relationship(
        "DocumentType",
        back_populates="parent_type",
        foreign_keys=[parent_type_id],
        viewonly=True,
    )
