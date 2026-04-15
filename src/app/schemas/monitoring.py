"""Pydantic schemas for system monitoring and health check responses."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    name: str
    status: Literal["healthy", "degraded", "unhealthy"]
    latency_ms: float | None = None
    details: str | None = None


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    components: list[ComponentHealth]
    checked_at: datetime


class WorkerInfo(BaseModel):
    hostname: str
    status: str
    active_tasks: int
    processed: int
    pid: int | None = None


class QueueMetrics(BaseModel):
    queue_name: str
    depth: int


class SystemMetrics(BaseModel):
    workers: list[WorkerInfo]
    queues: list[QueueMetrics]
    total_active_tasks: int
    total_scheduled_tasks: int


class AlertRuleCreate(BaseModel):
    name: str
    metric_name: str
    operator: str
    threshold: float
    enabled: bool = True
    notification_message: str | None = None


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    metric_name: str | None = None
    operator: str | None = None
    threshold: float | None = None
    enabled: bool | None = None
    notification_message: str | None = None


class AlertRuleResponse(BaseModel):
    id: uuid.UUID
    name: str
    metric_name: str
    operator: str
    threshold: float
    enabled: bool
    notification_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
