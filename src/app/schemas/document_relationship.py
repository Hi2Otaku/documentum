"""Pydantic schemas for document relationships."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RelationshipCreate(BaseModel):
    target_document_id: uuid.UUID
    relationship_type: str = Field(
        ..., pattern="^(supersedes|references|is_part_of|related_to)$"
    )
    description: str | None = None


class RelationshipResponse(BaseModel):
    id: uuid.UUID
    source_document_id: uuid.UUID
    target_document_id: uuid.UUID
    relationship_type: str
    description: str | None
    created_at: datetime
    created_by: str | None
    source_document_title: str | None = None
    target_document_title: str | None = None

    model_config = ConfigDict(from_attributes=True)
