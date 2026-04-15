import uuid
from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ServiceTokenCreate(BaseModel):
    name: str
    user_id: uuid.UUID


class ServiceTokenResponse(BaseModel):
    id: uuid.UUID
    name: str
    user_id: uuid.UUID
    token: str  # Raw token, only returned on creation
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceTokenListItem(BaseModel):
    id: uuid.UUID
    name: str
    user_id: uuid.UUID
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
