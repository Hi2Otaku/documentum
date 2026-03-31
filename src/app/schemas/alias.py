"""Pydantic schemas for alias set management."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AliasMappingCreate(BaseModel):
    alias_name: str = Field(min_length=1, max_length=255)
    target_type: str = Field(pattern=r"^(user|group)$")
    target_id: uuid.UUID


class AliasMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alias_set_id: uuid.UUID
    alias_name: str
    target_type: str
    target_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class AliasSetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    mappings: list[AliasMappingCreate] = []


class AliasSetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class AliasSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class AliasSetDetailResponse(AliasSetResponse):
    mappings: list[AliasMappingResponse] = []
