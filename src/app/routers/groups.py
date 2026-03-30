import math
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin, get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.user import GroupCreate, GroupMembershipUpdate, GroupResponse
from app.services import user_service

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post(
    "/",
    response_model=EnvelopeResponse[GroupResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Create a new group (admin only)."""
    group = await user_service.create_group(db, data, str(current_user.id))
    return EnvelopeResponse(data=GroupResponse.model_validate(group))


@router.get("/", response_model=EnvelopeResponse[list[GroupResponse]])
async def list_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List groups with pagination (authenticated)."""
    groups, total_count = await user_service.list_groups(db, page, page_size)
    return EnvelopeResponse(
        data=[GroupResponse.model_validate(g) for g in groups],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=math.ceil(total_count / page_size) if page_size > 0 else 0,
        ),
    )


@router.post(
    "/{group_id}/members",
    response_model=EnvelopeResponse[GroupResponse],
)
async def add_members_to_group(
    group_id: uuid.UUID,
    data: GroupMembershipUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Add users to a group (admin only)."""
    group = await user_service.add_users_to_group(
        db, group_id, data.user_ids, str(current_user.id)
    )
    return EnvelopeResponse(data=GroupResponse.model_validate(group))
