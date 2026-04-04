"""BAM dashboard endpoints — real-time workflow metrics."""
import asyncio
import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db
from app.core.dependencies import get_current_active_admin
from app.core.security import decode_access_token
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.dashboard import (
    BottleneckActivity,
    DashboardMetrics,
    TemplateMetric,
    UserWorkload,
    WorkflowSummary,
)
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=EnvelopeResponse[WorkflowSummary],
)
async def workflow_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Get workflow counts by state and average completion time."""
    summary = await dashboard_service.get_workflow_summary(db)
    return EnvelopeResponse(data=summary)


@router.get(
    "/bottlenecks",
    response_model=EnvelopeResponse[list[BottleneckActivity]],
)
async def bottleneck_activities(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Identify activities with the longest average duration."""
    bottlenecks = await dashboard_service.get_bottleneck_activities(db, limit=limit)
    return EnvelopeResponse(data=bottlenecks)


@router.get(
    "/workload",
    response_model=EnvelopeResponse[list[UserWorkload]],
)
async def user_workload(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Get pending work item counts per user."""
    workload = await dashboard_service.get_user_workload(db)
    return EnvelopeResponse(data=workload)


@router.get(
    "/templates",
    response_model=EnvelopeResponse[list[TemplateMetric]],
)
async def template_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Get instance counts and state breakdown per template."""
    metrics = await dashboard_service.get_template_metrics(db)
    return EnvelopeResponse(data=metrics)


@router.get("/metrics", response_model=EnvelopeResponse[DashboardMetrics])
async def dashboard_metrics(
    template_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Unified dashboard metrics combining KPIs, bottlenecks, workload, and SLA."""
    metrics = await dashboard_service.get_all_metrics(db, template_id)
    return EnvelopeResponse(data=metrics)


async def _validate_sse_token(token: str) -> User:
    """Validate JWT token from query param for SSE endpoint."""
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
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return user


async def _sse_generator(template_id: uuid.UUID | None, user: User):
    """Yield SSE events with KPI data every 5 seconds."""
    while True:
        async with async_session_factory() as session:
            kpi = await dashboard_service.get_kpi_metrics(session, template_id)
        data = kpi.model_dump_json()
        yield f"event: kpi_update\ndata: {data}\n\n"
        await asyncio.sleep(5)


@router.get("/stream")
async def dashboard_stream(
    token: str = Query(...),
    template_id: uuid.UUID | None = Query(None),
):
    """SSE stream for live KPI updates. Auth via query param token."""
    user = await _validate_sse_token(token)
    return StreamingResponse(
        _sse_generator(template_id, user),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
