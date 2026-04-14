"""Pydantic schemas for saved search CRUD operations."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SavedSearchCreate(BaseModel):
    name: str = Field(..., max_length=255)
    query: str = Field(..., min_length=1, max_length=500)
    filters: dict = Field(default_factory=dict)
    is_smart_folder: bool = False
    display_order: int = 0


class SavedSearchUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    query: str | None = Field(None, min_length=1, max_length=500)
    filters: dict | None = None
    is_smart_folder: bool | None = None
    display_order: int | None = None


class SavedSearchResponse(BaseModel):
    id: uuid.UUID
    name: str
    query: str
    filters: dict
    is_smart_folder: bool
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
