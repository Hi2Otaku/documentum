import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Request schemas ---


class VirtualDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None


class VirtualDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None


class AddChildRequest(BaseModel):
    document_id: uuid.UUID
    sort_order: int | None = Field(
        default=None,
        description="Position in the child list. If omitted, appended at end.",
    )


class ReorderChildrenRequest(BaseModel):
    """Ordered list of child document IDs defining the new sort order."""

    document_ids: list[uuid.UUID] = Field(
        min_length=1,
        description="Document IDs in desired order",
    )


# --- Response schemas ---


class VirtualDocumentChildResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    sort_order: int
    document_title: str | None = None
    document_filename: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VirtualDocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    is_deleted: bool
    children: list[VirtualDocumentChildResponse] = []

    model_config = ConfigDict(from_attributes=True)


class VirtualDocumentListResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    owner_id: uuid.UUID
    child_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
