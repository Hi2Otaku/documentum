"""Notification API endpoints -- REST + SSE stream."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory, get_db
from app.core.dependencies import get_current_user
from app.core.security import decode_access_token
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services import notification_service

logger = logging.getLogger(__name__)

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


@router.patch("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Mark all unread notifications as read for the current user."""
    count = await notification_service.mark_all_read(db, user_id=current_user.id)
    return {"ok": True, "updated_count": count}


@router.patch("/{notification_id}/read", status_code=status.HTTP_200_OK)
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


async def _validate_notification_sse_token(token: str) -> User:
    """Validate JWT token from query param for notification SSE endpoint.

    Unlike the dashboard SSE validator, this does NOT require is_superuser --
    notifications are for all authenticated users.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(
                User.id == uuid.UUID(user_id_str),
                User.is_deleted == False,  # noqa: E712
                User.is_active == True,  # noqa: E712
            )
        )
        user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def _notification_sse_generator(user_id: uuid.UUID):
    """Yield SSE events for a user's notifications via Redis pub/sub."""
    import redis.asyncio as aioredis

    # Send initial unread count
    async with async_session_factory() as session:
        count = await notification_service.get_unread_count(session, user_id=user_id)
    yield f"event: unread_count\ndata: {json.dumps({'count': count})}\n\n"

    # Subscribe to Redis notifications channel
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("notifications")

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                # Send heartbeat every 30 seconds
                yield ":heartbeat\n\n"
                continue

            if message is not None and message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                except (json.JSONDecodeError, TypeError):
                    continue

                # Only forward notifications for this user
                if str(data.get("user_id")) == str(user_id):
                    yield f"event: new_notification\ndata: {json.dumps(data)}\n\n"

                    # Also send updated unread count
                    async with async_session_factory() as session:
                        new_count = await notification_service.get_unread_count(
                            session, user_id=user_id
                        )
                    yield f"event: unread_count\ndata: {json.dumps({'count': new_count})}\n\n"
    finally:
        await pubsub.unsubscribe("notifications")
        await pubsub.aclose()
        await redis_client.aclose()


@router.get("/stream")
async def notification_stream(
    token: str = Query(...),
):
    """SSE stream for live notification updates. Auth via query param token."""
    user = await _validate_notification_sse_token(token)
    return StreamingResponse(
        _notification_sse_generator(user.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
