import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8)
    email: str | None = None
    is_superuser: bool = False


class UserUpdate(BaseModel):
    email: str | None = None
    is_active: bool | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None


class GroupResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupMembershipUpdate(BaseModel):
    user_ids: list[uuid.UUID]


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
