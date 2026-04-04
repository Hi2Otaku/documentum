"""BAM dashboard endpoints — real-time workflow metrics."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.dashboard import (
    BottleneckActivity,
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
