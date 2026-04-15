import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class IdentityProvider(BaseModel):
    __tablename__ = "identity_providers"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "ldap", "saml", "oidc"
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ServiceToken(BaseModel):
    __tablename__ = "service_tokens"

    token_hash: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
