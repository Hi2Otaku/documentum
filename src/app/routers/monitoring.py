"""Monitoring API endpoints -- health, metrics, alert rules, and Prometheus."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_admin
from app.models.monitoring import AlertRule
from app.models.user import User
from app.schemas.common import EnvelopeResponse
from app.schemas.monitoring import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
    HealthResponse,
    SystemMetrics,
)
from app.services.monitoring_service import (
    check_all_health,
    generate_prometheus_metrics,
    get_system_metrics,
)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Separate router for the root-level /metrics Prometheus endpoint
prometheus_router = APIRouter(tags=["prometheus"])


# ---------------------------------------------------------------------------
# Health & metrics (admin only)
# ---------------------------------------------------------------------------


@router.get("/health", response_model=EnvelopeResponse[HealthResponse])
async def monitoring_health(
    _admin: User = Depends(get_current_active_admin),
):
    """Deep health check of all system components (DB, Redis, Celery, MinIO)."""
    health = await check_all_health()
    return EnvelopeResponse(data=health)


@router.get("/metrics", response_model=EnvelopeResponse[SystemMetrics])
async def monitoring_metrics(
    _admin: User = Depends(get_current_active_admin),
):
    """Celery worker stats, queue depths, active/scheduled task counts."""
    metrics = await get_system_metrics()
    return EnvelopeResponse(data=metrics)


# ---------------------------------------------------------------------------
# Alert rules CRUD (admin only)
# ---------------------------------------------------------------------------


@router.get("/alerts", response_model=EnvelopeResponse[list[AlertRuleResponse]])
async def list_alert_rules(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_admin),
):
    """List all alert rules."""
    result = await db.execute(
        select(AlertRule).where(AlertRule.is_deleted == False).order_by(AlertRule.created_at.desc())  # noqa: E712
    )
    rules = list(result.scalars().all())
    return EnvelopeResponse(data=[AlertRuleResponse.model_validate(r) for r in rules])


@router.post("/alerts", response_model=EnvelopeResponse[AlertRuleResponse], status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    body: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_admin),
):
    """Create a new alert rule."""
    rule = AlertRule(
        name=body.name,
        metric_name=body.metric_name,
        operator=body.operator,
        threshold=body.threshold,
        enabled=body.enabled,
        notification_message=body.notification_message,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return EnvelopeResponse(data=AlertRuleResponse.model_validate(rule))


@router.put("/alerts/{rule_id}", response_model=EnvelopeResponse[AlertRuleResponse])
async def update_alert_rule(
    rule_id: uuid.UUID,
    body: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_admin),
):
    """Update an existing alert rule."""
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id, AlertRule.is_deleted == False)  # noqa: E712
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    await db.flush()
    await db.refresh(rule)
    return EnvelopeResponse(data=AlertRuleResponse.model_validate(rule))


@router.delete("/alerts/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_admin),
):
    """Soft-delete an alert rule."""
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id, AlertRule.is_deleted == False)  # noqa: E712
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    rule.is_deleted = True
    await db.flush()


# ---------------------------------------------------------------------------
# Prometheus /metrics (unauthenticated -- for scraper)
# ---------------------------------------------------------------------------


@prometheus_router.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint (text/plain format)."""
    text = generate_prometheus_metrics()
    return Response(
        content=text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
