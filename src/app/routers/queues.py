"""Queue management endpoints (admin-only)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.queue import (
    WorkQueueCreate,
    WorkQueueDetailResponse,
    WorkQueueMemberAdd,
    WorkQueueResponse,
    WorkQueueUpdate,
)
from app.services import queue_service

router = APIRouter(prefix="/queues", tags=["queues"])


@router.post(
    "",
    response_model=EnvelopeResponse[WorkQueueResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_queue(
    data: WorkQueueCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Create a new work queue (admin only)."""
    try:
        queue = await queue_service.create_queue(db, data, str(current_user.id))
        return EnvelopeResponse(
            data=WorkQueueResponse(
                id=queue.id,
                name=queue.name,
                description=queue.description,
                is_active=queue.is_active,
                member_count=0,
                created_at=queue.created_at,
                updated_at=queue.updated_at,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=EnvelopeResponse[list[WorkQueueResponse]])
async def list_queues(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """List all work queues (admin only)."""
    queues, total_count = await queue_service.get_queues(db, skip, limit)
    return EnvelopeResponse(
        data=[
            WorkQueueResponse(
                id=q.id,
                name=q.name,
                description=q.description,
                is_active=q.is_active,
                member_count=len(q.members) if q.members else 0,
                created_at=q.created_at,
                updated_at=q.updated_at,
            )
            for q in queues
        ],
        meta={"total_count": total_count, "skip": skip, "limit": limit},
    )


@router.get("/{queue_id}", response_model=EnvelopeResponse[WorkQueueDetailResponse])
async def get_queue(
    queue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Get a single work queue with members (admin only)."""
    try:
        queue = await queue_service.get_queue(db, queue_id)
        from app.schemas.queue import QueueMemberResponse

        return EnvelopeResponse(
            data=WorkQueueDetailResponse(
                id=queue.id,
                name=queue.name,
                description=queue.description,
                is_active=queue.is_active,
                member_count=len(queue.members) if queue.members else 0,
                created_at=queue.created_at,
                updated_at=queue.updated_at,
                members=[
                    QueueMemberResponse(id=m.id, username=m.username, email=m.email)
                    for m in queue.members
                ],
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{queue_id}", response_model=EnvelopeResponse[WorkQueueResponse])
async def update_queue(
    queue_id: uuid.UUID,
    data: WorkQueueUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Update a work queue (admin only)."""
    try:
        queue = await queue_service.update_queue(db, queue_id, data, str(current_user.id))
        return EnvelopeResponse(
            data=WorkQueueResponse(
                id=queue.id,
                name=queue.name,
                description=queue.description,
                is_active=queue.is_active,
                member_count=len(queue.members) if queue.members else 0,
                created_at=queue.created_at,
                updated_at=queue.updated_at,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{queue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_queue(
    queue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Soft-delete a work queue (admin only)."""
    try:
        await queue_service.delete_queue(db, queue_id, str(current_user.id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{queue_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    queue_id: uuid.UUID,
    data: WorkQueueMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Add a user to a work queue (admin only)."""
    try:
        await queue_service.add_member(db, queue_id, data.user_id, str(current_user.id))
        return {"detail": "Member added"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{queue_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    queue_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Remove a user from a work queue (admin only)."""
    try:
        await queue_service.remove_member(db, queue_id, user_id, str(current_user.id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
