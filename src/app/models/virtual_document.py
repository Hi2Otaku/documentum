import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class VirtualDocument(BaseModel):
    """A compound document that assembles multiple child documents in order."""

    __tablename__ = "virtual_documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=False
    )

    children: Mapped[list["VirtualDocumentChild"]] = relationship(
        back_populates="virtual_document",
        order_by="VirtualDocumentChild.sort_order",
        cascade="all, delete-orphan",
    )

    owner: Mapped["User"] = relationship(  # noqa: F821
        foreign_keys=[owner_id], lazy="selectin"
    )


class VirtualDocumentChild(BaseModel):
    """Links a child document to a virtual document with ordering."""

    __tablename__ = "virtual_document_children"
    __table_args__ = (
        UniqueConstraint(
            "virtual_document_id",
            "document_id",
            name="uq_vdoc_child_document",
        ),
        UniqueConstraint(
            "virtual_document_id",
            "sort_order",
            name="uq_vdoc_child_sort_order",
        ),
    )

    virtual_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("virtual_documents.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    virtual_document: Mapped["VirtualDocument"] = relationship(
        back_populates="children"
    )
    document: Mapped["Document"] = relationship(  # noqa: F821
        foreign_keys=[document_id], lazy="selectin"
    )
