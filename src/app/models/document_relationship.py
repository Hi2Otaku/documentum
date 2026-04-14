"""DocumentRelationship model — typed directional links between documents."""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class RelationshipType(str, enum.Enum):
    SUPERSEDES = "supersedes"
    REFERENCES = "references"
    IS_PART_OF = "is_part_of"
    RELATED_TO = "related_to"


class DocumentRelationship(BaseModel):
    __tablename__ = "document_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id",
            "target_document_id",
            "relationship_type",
            name="uq_document_relationship",
        ),
    )

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False, index=True
    )
    target_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        Enum(RelationshipType, name="relationshiptype"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_document = relationship(
        "Document",
        foreign_keys=[source_document_id],
        lazy="selectin",
    )
    target_document = relationship(
        "Document",
        foreign_keys=[target_document_id],
        lazy="selectin",
    )
