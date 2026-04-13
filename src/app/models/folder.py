import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel


# Association table: documents filed into folders (many-to-many)
document_folders = Table(
    "document_folders",
    Base.metadata,
    Column("document_id", Uuid(), ForeignKey("documents.id"), primary_key=True),
    Column("folder_id", Uuid(), ForeignKey("folders.id"), primary_key=True),
    Column(
        "filed_at",
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    ),
    Column("filed_by", String(255), nullable=True),
)


class Folder(BaseModel):
    """A cabinet (root folder) or subfolder in the document hierarchy."""

    __tablename__ = "folders"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("folders.id"), nullable=True
    )
    is_cabinet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Self-referential relationship
    parent: Mapped["Folder | None"] = relationship(
        "Folder",
        remote_side="Folder.id",
        back_populates="children",
        lazy="selectin",
        foreign_keys=[parent_id],
    )
    children: Mapped[list["Folder"]] = relationship(
        "Folder",
        back_populates="parent",
        foreign_keys=[parent_id],
        viewonly=True,
    )

    # Documents filed in this folder (many-to-many via document_folders)
    documents: Mapped[list["Document"]] = relationship(  # type: ignore[name-defined]
        "Document",
        secondary=document_folders,
        viewonly=True,
    )
