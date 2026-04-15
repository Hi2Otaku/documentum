import hashlib
import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.identity_provider import ServiceToken
from app.models.user import User
from app.services.audit_service import create_audit_record


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> User | None:
    """Authenticate a user by username and password.

    Returns the User if credentials are valid, None otherwise.
    """
    result = await db.execute(
        select(User).where(
            User.username == username,
            User.is_deleted == False,  # noqa: E712
            User.is_active == True,  # noqa: E712
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def login(db: AsyncSession, username: str, password: str) -> str:
    """Authenticate user and return a JWT access token.

    Raises HTTPException 401 if credentials are invalid.
    """
    user = await authenticate_user(db, username, password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )

    await create_audit_record(
        db,
        entity_type="user",
        entity_id=str(user.id),
        action="login",
        user_id=str(user.id),
    )

    return access_token


async def create_service_token(
    db: AsyncSession, name: str, user_id: uuid.UUID
) -> tuple[ServiceToken, str]:
    """Create a service token for API/worker authentication.

    Returns (ServiceToken model, raw_token). The raw token is only
    available at creation time.
    """
    raw_token = settings.service_token_prefix + secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    svc_token = ServiceToken(
        token_hash=token_hash,
        name=name,
        user_id=user_id,
    )
    db.add(svc_token)
    await db.commit()
    await db.refresh(svc_token)
    return svc_token, raw_token


async def list_service_tokens(db: AsyncSession) -> list[ServiceToken]:
    """Return all non-deleted service tokens."""
    result = await db.execute(
        select(ServiceToken).where(
            ServiceToken.is_deleted == False  # noqa: E712
        )
    )
    return list(result.scalars().all())


async def revoke_service_token(db: AsyncSession, token_id: uuid.UUID) -> None:
    """Revoke a service token by setting is_active=False."""
    result = await db.execute(
        select(ServiceToken).where(ServiceToken.id == token_id)
    )
    svc_token = result.scalar_one_or_none()
    if svc_token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service token not found",
        )
    svc_token.is_active = False
    await db.commit()
