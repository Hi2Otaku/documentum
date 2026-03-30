from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
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
