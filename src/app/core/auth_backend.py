"""Pluggable auth backend registry (Strategy pattern).

Decouples get_current_user from hardcoded JWT validation so SAML/OIDC/LDAP
backends can be added without changing the dependency.
"""

import hashlib
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.models.user import User


class AuthBackend(ABC):
    """Abstract base for authentication backends."""

    @abstractmethod
    async def validate_token(self, token: str, db: AsyncSession) -> User | None:
        """Validate a token and return the associated User, or None."""
        ...


class LocalAuthBackend(AuthBackend):
    """Validates standard JWT access tokens (local username/password login)."""

    async def validate_token(self, token: str, db: AsyncSession) -> User | None:
        try:
            payload = decode_access_token(token)
            user_id_str: str | None = payload.get("sub")
            if user_id_str is None:
                return None
        except jwt.PyJWTError:
            return None

        result = await db.execute(
            select(User).where(
                User.id == uuid.UUID(user_id_str),
                User.is_deleted == False,  # noqa: E712
                User.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()


class ServiceTokenBackend(AuthBackend):
    """Validates service tokens (for Celery workers, Workflow Agent, etc.)."""

    async def validate_token(self, token: str, db: AsyncSession) -> User | None:
        from app.core.config import settings
        from app.models.identity_provider import ServiceToken

        # Service tokens are prefixed to distinguish from JWTs
        if not token.startswith(settings.service_token_prefix):
            return None

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        result = await db.execute(
            select(ServiceToken).where(
                ServiceToken.token_hash == token_hash,
                ServiceToken.is_active == True,  # noqa: E712
                ServiceToken.is_deleted == False,  # noqa: E712
            )
        )
        svc_token = result.scalar_one_or_none()
        if svc_token is None:
            return None

        # Check expiry
        if svc_token.expires_at is not None and svc_token.expires_at < datetime.now(timezone.utc):
            return None

        # Update last_used_at
        await db.execute(
            update(ServiceToken)
            .where(ServiceToken.id == svc_token.id)
            .values(last_used_at=datetime.now(timezone.utc))
        )

        # Look up the associated user
        user_result = await db.execute(
            select(User).where(
                User.id == svc_token.user_id,
                User.is_deleted == False,  # noqa: E712
                User.is_active == True,  # noqa: E712
            )
        )
        return user_result.scalar_one_or_none()


class AuthBackendRegistry:
    """Iterates registered backends in order until one validates the token."""

    def __init__(self, backends: list[AuthBackend]) -> None:
        self._backends = backends

    async def validate_token(self, token: str, db: AsyncSession) -> User | None:
        for backend in self._backends:
            user = await backend.validate_token(token, db)
            if user is not None:
                return user
        return None

    def register(self, backend: AuthBackend) -> None:
        """Add a backend to the end of the chain."""
        self._backends.append(backend)


# Module-level singleton: LocalAuth first, then ServiceToken
auth_backend_registry = AuthBackendRegistry([
    LocalAuthBackend(),
    ServiceTokenBackend(),
])
