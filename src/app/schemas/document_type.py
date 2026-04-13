import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    metadata_schema: dict[str, Any] = Field(default_factory=dict)
    parent_type_id: uuid.UUID | None = None


class DocumentTypeUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    metadata_schema: dict[str, Any] | None = None
    parent_type_id: uuid.UUID | None = None


class DocumentTypeResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    metadata_schema: dict[str, Any]
    parent_type_id: uuid.UUID | None
    parent_type_name: str | None = None
    field_count: int = 0
    document_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
