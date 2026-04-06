import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import DispositionAction


class RetentionPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    retention_period_days: int = Field(ge=1)
    disposition_action: DispositionAction


class RetentionPolicyUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    retention_period_days: int | None = Field(default=None, ge=1)
    disposition_action: DispositionAction | None = None
    is_active: bool | None = None


class RetentionPolicyResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    retention_period_days: int
    disposition_action: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    model_config = ConfigDict(from_attributes=True)


class AssignRetentionRequest(BaseModel):
    retention_policy_id: uuid.UUID


class DocumentRetentionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    retention_policy_id: uuid.UUID
    policy_name: str
    applied_at: datetime
    expires_at: datetime
    applied_by: str

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires < now


class LegalHoldCreate(BaseModel):
    reason: str = Field(min_length=1)


class LegalHoldResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    reason: str
    placed_by: str
    placed_at: datetime
    released_at: datetime | None
    released_by: str | None

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_active(self) -> bool:
        return self.released_at is None
