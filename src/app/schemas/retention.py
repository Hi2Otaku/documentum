import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Retention Policy schemas ---

class RetentionPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    retention_period_days: int = Field(gt=0)
    disposition_action: str = Field(pattern="^(archive|delete)$")


class RetentionPolicyUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    retention_period_days: int | None = Field(default=None, gt=0)
    disposition_action: str | None = Field(default=None, pattern="^(archive|delete)$")


class RetentionPolicyResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    retention_period_days: int
    disposition_action: str
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    model_config = ConfigDict(from_attributes=True)


# --- Document Retention schemas ---

class DocumentRetentionAssign(BaseModel):
    policy_id: uuid.UUID


class DocumentRetentionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    policy_id: uuid.UUID
    applied_at: datetime
    expires_at: datetime
    created_at: datetime
    created_by: str | None
    policy_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Legal Hold schemas ---

class LegalHoldCreate(BaseModel):
    reason: str = Field(min_length=1)


class LegalHoldResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    reason: str
    placed_by: uuid.UUID
    placed_at: datetime
    released_at: datetime | None
    created_at: datetime
    created_by: str | None

    model_config = ConfigDict(from_attributes=True)


# --- Retention Status ---

class RetentionStatusResponse(BaseModel):
    document_id: uuid.UUID
    is_retained: bool
    is_held: bool
    is_deletable: bool
    deletion_blocked_reason: str | None = None
    active_retentions: list[DocumentRetentionResponse] = []
    active_holds: list[LegalHoldResponse] = []
