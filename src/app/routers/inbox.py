"""User inbox endpoints for work item management."""
import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.common import EnvelopeResponse, PaginationMeta
from app.schemas.inbox import (
    AcquireResponse,
    CommentCreateRequest,
    CommentResponse,
    CompleteFromInboxRequest,
    InboxItemDetailResponse,
    InboxItemResponse,
    RejectFromInboxRequest,
)
from app.services import inbox_service

router = APIRouter(prefix="/inbox", tags=["inbox"])


# ---------------------------------------------------------------------------
# a) List inbox items
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=EnvelopeResponse[list[InboxItemResponse]],
)
async def list_inbox(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    state: str | None = Query(None),
    priority: int | None = Query(None),
    template_name: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's inbox work items with filters and pagination."""
    items, total_count = await inbox_service.get_inbox_items(
        db,
        str(current_user.id),
        skip,
        limit,
        state,
        priority,
        template_name,
        sort_by,
        sort_order,
    )
    return EnvelopeResponse(
        data=[InboxItemResponse.model_validate(item) for item in items],
        meta=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_count=total_count,
            total_pages=math.ceil(total_count / limit) if limit > 0 else 0,
        ),
    )


# ---------------------------------------------------------------------------
# b) Get inbox item detail
# ---------------------------------------------------------------------------


@router.get(
    "/{work_item_id}",
    response_model=EnvelopeResponse[InboxItemDetailResponse],
)
async def get_inbox_item(
    work_item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single work item with full detail and comments."""
    try:
        item = await inbox_service.get_inbox_item_detail(
            db, work_item_id, str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(
        data=InboxItemDetailResponse.model_validate(item)
    )


# ---------------------------------------------------------------------------
# c) Acquire work item
# ---------------------------------------------------------------------------


@router.post(
    "/{work_item_id}/acquire",
    response_model=EnvelopeResponse[AcquireResponse],
)
async def acquire_work_item(
    work_item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acquire an available work item."""
    try:
        wi = await inbox_service.acquire_work_item(
            db, work_item_id, str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(
        data=AcquireResponse.model_validate(wi)
    )


# ---------------------------------------------------------------------------
# d) Release work item
# ---------------------------------------------------------------------------


@router.post(
    "/{work_item_id}/release",
    response_model=EnvelopeResponse[AcquireResponse],
)
async def release_work_item(
    work_item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Release an acquired work item back to available."""
    try:
        wi = await inbox_service.release_work_item(
            db, work_item_id, str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(
        data=AcquireResponse.model_validate(wi)
    )


# ---------------------------------------------------------------------------
# e) Complete work item
# ---------------------------------------------------------------------------


@router.post(
    "/{work_item_id}/complete",
    response_model=EnvelopeResponse[AcquireResponse],
)
async def complete_work_item(
    work_item_id: uuid.UUID,
    request: CompleteFromInboxRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete an acquired work item and advance the workflow."""
    try:
        wi = await inbox_service.complete_inbox_item(
            db, work_item_id, str(current_user.id), request.output_variables
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(
        data=AcquireResponse.model_validate(wi)
    )


# ---------------------------------------------------------------------------
# f) Reject work item
# ---------------------------------------------------------------------------


@router.post(
    "/{work_item_id}/reject",
    response_model=EnvelopeResponse[AcquireResponse],
)
async def reject_work_item(
    work_item_id: uuid.UUID,
    request: RejectFromInboxRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject an acquired work item."""
    try:
        wi = await inbox_service.reject_inbox_item(
            db, work_item_id, str(current_user.id), request.reason
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(
        data=AcquireResponse.model_validate(wi)
    )


# ---------------------------------------------------------------------------
# g) List comments
# ---------------------------------------------------------------------------


@router.get(
    "/{work_item_id}/comments",
    response_model=EnvelopeResponse[list[CommentResponse]],
)
async def list_comments(
    work_item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all comments for a work item."""
    comments = await inbox_service.get_comments(db, work_item_id)
    return EnvelopeResponse(
        data=[CommentResponse.model_validate(c) for c in comments]
    )


# ---------------------------------------------------------------------------
# h) Add comment
# ---------------------------------------------------------------------------


@router.post(
    "/{work_item_id}/comments",
    response_model=EnvelopeResponse[CommentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    work_item_id: uuid.UUID,
    request: CommentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a comment to a work item."""
    try:
        comment = await inbox_service.add_comment(
            db, work_item_id, str(current_user.id), request.content
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return EnvelopeResponse(
        data=CommentResponse.model_validate(comment)
    )
