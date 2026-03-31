import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.enums import PermissionLevel


class ACLEntryCreate(BaseModel):
    document_id: uuid.UUID
    principal_id: uuid.UUID
    principal_type: Literal["user", "group"]
    permission_level: PermissionLevel


class ACLEntryResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    principal_id: uuid.UUID
    principal_type: str
    permission_level: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionCheckResponse(BaseModel):
    has_permission: bool
    granted_level: PermissionLevel | None = None
