import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class FolderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    parent_id: uuid.UUID | None = None  # Move operation


class FolderCopyRequest(BaseModel):
    destination_parent_id: uuid.UUID | None = None


class FileDocumentRequest(BaseModel):
    document_id: uuid.UUID


class FolderPathSegment(BaseModel):
    id: uuid.UUID
    name: str


class FolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    parent_id: uuid.UUID | None
    is_cabinet: bool
    document_count: int = 0
    path: list[FolderPathSegment] = []
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    model_config = ConfigDict(from_attributes=True)


class FolderTreeNode(BaseModel):
    id: uuid.UUID
    name: str
    is_cabinet: bool
    document_count: int = 0
    children: list["FolderTreeNode"] = []
