"""Analytics API endpoints -- execution paths, cycle times, bottlenecks, and cache refresh."""
from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummary,
    BottleneckActivity,
    CycleTimeStats,
    ExecutionPath,
)
from app.schemas.common import EnvelopeResponse
from app.services.analytics_service import (
    get_analytics_summary,
    get_bottlenecks,
    get_cycle_times,
    get_execution_paths,
    refresh_analytics_cache,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _try_redis_cache(key: str) -> list | dict | None:
    """Try reading a cached value from Redis. Returns None on miss or error."""
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings

        r = aioredis.from_url(settings.redis_url)
        try:
            raw = await r.get(key)
            if raw:
                return json.loads(raw)
        finally:
            await r.aclose()
    except Exception:
        logger.debug("Redis cache miss for key=%s", key)
    return None


# ---------------------------------------------------------------------------
# Endpoints (admin only)
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=EnvelopeResponse[AnalyticsSummary])
async def analytics_summary(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_admin),
):
    """High-level analytics summary: total instances, completion rate, paths discovered."""
    data = await get_analytics_summary(db)
    return EnvelopeResponse(data=data)


@router.get("/paths", response_model=EnvelopeResponse[list[ExecutionPath]])
async def analytics_paths(
    template_id: uuid.UUID | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_admin),
):
    """Discover execution paths with frequency and average duration."""
    # Try cache first
    cache_key = f"analytics:paths:{template_id}" if template_id else "analytics:paths"
    cached = await _try_redis_cache(cache_key)
    if cached is not None:
        return EnvelopeResponse(data=cached[:limit])

    data = await get_execution_paths(db, template_id=template_id, limit=limit)
    return EnvelopeResponse(data=data)


@router.get("/cycle-times", response_model=EnvelopeResponse[list[CycleTimeStats]])
async def analytics_cycle_times(
    template_id: uuid.UUID | None = Query(None),
    group_by: str = Query("activity"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_admin),
):
    """Cycle time statistics grouped by activity or template."""
    if group_by not in ("activity", "template"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_by must be 'activity' or 'template'",
        )

    cache_key = f"analytics:cycle_times:{group_by}"
    cached = await _try_redis_cache(cache_key)
    if cached is not None:
        return EnvelopeResponse(data=cached)

    data = await get_cycle_times(db, template_id=template_id, group_by=group_by)
    return EnvelopeResponse(data=data)


@router.get("/bottlenecks", response_model=EnvelopeResponse[list[BottleneckActivity]])
async def analytics_bottlenecks(
    template_id: uuid.UUID | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_admin),
):
    """Bottleneck activities ranked by average duration and time consumption."""
    cached = await _try_redis_cache("analytics:bottlenecks")
    if cached is not None:
        return EnvelopeResponse(data=cached[:limit])

    data = await get_bottlenecks(db, template_id=template_id, limit=limit)
    return EnvelopeResponse(data=data)


@router.post("/refresh", response_model=EnvelopeResponse[dict])
async def analytics_refresh(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_admin),
):
    """Trigger immediate analytics cache refresh."""
    await refresh_analytics_cache(db)
    return EnvelopeResponse(data={"status": "refreshed"})
