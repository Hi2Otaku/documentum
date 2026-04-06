import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


class DocumentUpload(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    author: str | None = None
    custom_properties: dict[str, Any] | None = None


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    author: str | None = None
    custom_properties: dict[str, Any] | None = None


class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    author: str | None
    filename: str
    content_type: str
    custom_properties: dict[str, Any]
    locked_by: uuid.UUID | None
    locked_at: datetime | None
    current_major_version: int
    current_minor_version: int
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    is_deleted: bool
    lifecycle_state: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def current_version(self) -> str:
        return f"{self.current_major_version}.{self.current_minor_version}"


class DocumentVersionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    major_version: int
    minor_version: int
    content_hash: str
    content_size: int
    filename: str
    content_type: str
    comment: str | None
    is_signed: bool = False
    created_at: datetime
    created_by: str | None

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def version_label(self) -> str:
        return f"{self.major_version}.{self.minor_version}"


class CheckinRequest(BaseModel):
    comment: str | None = None


class DocumentListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    title: str | None = None
    author: str | None = None
