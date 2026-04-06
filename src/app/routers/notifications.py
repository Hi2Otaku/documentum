"""Notification API endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_read: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    """List notifications for the current user (newest first)."""
    items, total = await notification_service.list_notifications(
        db, user_id=current_user.id, page=page, page_size=page_size, is_read=is_read
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadCountResponse:
    """Return the number of unread notifications for the current user."""
    count = await notification_service.get_unread_count(db, user_id=current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.put("/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_notification_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Mark a single notification as read."""
    updated = await notification_service.mark_read(
        db, notification_id=notification_id, user_id=current_user.id
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"ok": True}


@router.put("/mark-all-read", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Mark all unread notifications as read for the current user."""
    count = await notification_service.mark_all_read(db, user_id=current_user.id)
    return {"ok": True, "updated": count}
