import math
import uuid

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin, get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.user import RoleCreate, RoleResponse, UserResponse
from app.services import user_service

router = APIRouter(prefix="/roles", tags=["roles"])


class RoleAssignment(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID


@router.post(
    "/",
    response_model=EnvelopeResponse[RoleResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Create a new role (admin only)."""
    role = await user_service.create_role(db, data, str(current_user.id))
    return EnvelopeResponse(data=RoleResponse.model_validate(role))


@router.get("/", response_model=EnvelopeResponse[list[RoleResponse]])
async def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List roles with pagination (authenticated)."""
    roles, total_count = await user_service.list_roles(db, page, page_size)
    return EnvelopeResponse(
        data=[RoleResponse.model_validate(r) for r in roles],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=math.ceil(total_count / page_size) if page_size > 0 else 0,
        ),
    )


@router.post("/assign", response_model=EnvelopeResponse[UserResponse])
async def assign_role(
    data: RoleAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Assign a role to a user (admin only)."""
    user = await user_service.assign_role_to_user(
        db, data.user_id, data.role_id, str(current_user.id)
    )
    return EnvelopeResponse(data=UserResponse.model_validate(user))
