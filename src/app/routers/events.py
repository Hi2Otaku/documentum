"""Domain event admin endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.event import DomainEventResponse
from app.services import event_bus

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=EnvelopeResponse[list[DomainEventResponse]])
async def list_events(
    event_type: str | None = Query(None),
    entity_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """List domain events (admin only). Supports filtering by type and entity."""
    events = await event_bus.get_events(
        db, event_type=event_type, entity_id=entity_id, limit=limit, offset=offset
    )
    return EnvelopeResponse(
        data=[DomainEventResponse.model_validate(e) for e in events]
    )
