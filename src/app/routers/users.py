import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin, get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.user import AvailabilityUpdate, UserCreate, UserResponse, UserUpdate
from app.services import user_service
from app.services.audit_service import create_audit_record

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


@router.put("/me/availability", response_model=EnvelopeResponse[UserResponse])
async def update_availability(
    data: AvailabilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle user availability and set delegate per D-01."""
    if not data.is_available and data.delegate_id is None:
        raise HTTPException(status_code=400, detail="Must specify delegate_id when marking unavailable")
    if data.delegate_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delegate to yourself")
    if data.delegate_id:
        delegate = await db.get(User, data.delegate_id)
        if delegate is None or delegate.is_deleted:
            raise HTTPException(status_code=400, detail="Delegate user not found")
    current_user.is_available = data.is_available
    current_user.delegate_id = data.delegate_id if not data.is_available else None
    await create_audit_record(
        db,
        entity_type="user",
        entity_id=str(current_user.id),
        action="availability_changed",
        user_id=str(current_user.id),
        after_state={
            "is_available": data.is_available,
            "delegate_id": str(data.delegate_id) if data.delegate_id else None,
        },
    )
    await db.flush()
    return EnvelopeResponse(data=UserResponse.model_validate(current_user))
