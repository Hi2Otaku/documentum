import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkQueueCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class WorkQueueUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class WorkQueueResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    member_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkQueueDetailResponse(WorkQueueResponse):
    members: list["QueueMemberResponse"] = []


class QueueMemberResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None

    model_config = ConfigDict(from_attributes=True)


class WorkQueueMemberAdd(BaseModel):
    user_id: uuid.UUID
