import math
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin, get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=EnvelopeResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Create a new user (admin only)."""
    user = await user_service.create_user(db, data, str(current_user.id))
    return EnvelopeResponse(data=UserResponse.model_validate(user))


@router.get("/", response_model=EnvelopeResponse[list[UserResponse]])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List users with pagination (authenticated)."""
    users, total_count = await user_service.list_users(db, page, page_size)
    return EnvelopeResponse(
        data=[UserResponse.model_validate(u) for u in users],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=math.ceil(total_count / page_size) if page_size > 0 else 0,
        ),
    )


@router.get("/{user_id}", response_model=EnvelopeResponse[UserResponse])
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single user by ID (authenticated)."""
    user = await user_service.get_user(db, user_id)
    return EnvelopeResponse(data=UserResponse.model_validate(user))


@router.put("/{user_id}", response_model=EnvelopeResponse[UserResponse])
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Update a user (admin only)."""
    user = await user_service.update_user(db, user_id, data, str(current_user.id))
    return EnvelopeResponse(data=UserResponse.model_validate(user))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Soft delete a user (admin only)."""
    await user_service.delete_user(db, user_id, str(current_user.id))
