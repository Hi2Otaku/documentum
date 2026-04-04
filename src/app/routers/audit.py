"""Audit trail query endpoints."""
import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.schemas.common import EnvelopeResponse, PaginationMeta

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=EnvelopeResponse[list[AuditLogResponse]])
async def query_audit(
    user_id: str | None = Query(None),
    workflow_id: str | None = Query(None),
    document_id: str | None = Query(None),
    action_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Query audit trail with filters. Admin only."""
    conditions = []
    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    if workflow_id:
        conditions.append(AuditLog.entity_id == workflow_id)
    if document_id:
        conditions.append(AuditLog.entity_id == document_id)
    if action_type:
        conditions.append(AuditLog.action == action_type)
    if date_from:
        conditions.append(AuditLog.timestamp >= date_from)
    if date_to:
        conditions.append(AuditLog.timestamp <= date_to)

    base_query = select(AuditLog).where(*conditions) if conditions else select(AuditLog)
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar_one()

    result = await db.execute(
        base_query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
    )
    records = list(result.scalars().all())

    return EnvelopeResponse(
        data=[AuditLogResponse.model_validate(r) for r in records],
        meta=PaginationMeta(
            page=(skip // limit) + 1,
            page_size=limit,
            total_count=total_count,
            total_pages=math.ceil(total_count / limit) if limit > 0 else 0,
        ),
    )
