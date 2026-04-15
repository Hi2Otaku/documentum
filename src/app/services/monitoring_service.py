"""Monitoring service -- health checks, metrics collection, Prometheus, and alert evaluation."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

import redis.asyncio as aioredis
from prometheus_client import CollectorRegistry, Gauge, generate_latest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import engine
from app.core.minio_client import minio_client
from app.models.monitoring import AlertRule
from app.schemas.monitoring import (
    ComponentHealth,
    HealthResponse,
    QueueMetrics,
    SystemMetrics,
    WorkerInfo,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


async def check_database_health() -> ComponentHealth:
    """Ping the database with SELECT 1 and measure latency."""
    start = time.monotonic()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="database", status="healthy", latency_ms=round(latency, 2))
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="database", status="unhealthy", latency_ms=round(latency, 2), details=str(exc)
        )


async def check_redis_health() -> ComponentHealth:
    """Ping Redis and measure latency."""
    start = time.monotonic()
    try:
        r = aioredis.from_url(settings.redis_url)
        try:
            await r.ping()
        finally:
            await r.aclose()
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="redis", status="healthy", latency_ms=round(latency, 2))
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="redis", status="unhealthy", latency_ms=round(latency, 2), details=str(exc)
        )


async def check_celery_health() -> ComponentHealth:
    """Ping Celery workers (sync inspect call run in thread)."""
    from app.celery_app import celery_app

    start = time.monotonic()
    try:
        result = await asyncio.to_thread(lambda: celery_app.control.inspect().ping())
        latency = (time.monotonic() - start) * 1000
        if result:
            worker_count = len(result)
            return ComponentHealth(
                name="celery",
                status="healthy",
                latency_ms=round(latency, 2),
                details=f"{worker_count} worker(s) responding",
            )
        return ComponentHealth(
            name="celery", status="unhealthy", latency_ms=round(latency, 2), details="No workers responding"
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="celery", status="unhealthy", latency_ms=round(latency, 2), details=str(exc)
        )


async def check_minio_health() -> ComponentHealth:
    """Check MinIO connectivity by verifying bucket existence."""
    start = time.monotonic()
    try:
        await asyncio.to_thread(lambda: minio_client.bucket_exists("documents"))
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(name="minio", status="healthy", latency_ms=round(latency, 2))
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            name="minio", status="unhealthy", latency_ms=round(latency, 2), details=str(exc)
        )


async def check_all_health() -> HealthResponse:
    """Run all component health checks and aggregate the overall status."""
    components = await asyncio.gather(
        check_database_health(),
        check_redis_health(),
        check_celery_health(),
        check_minio_health(),
    )
    components = list(components)

    statuses = [c.status for c in components]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        components=components,
        checked_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# System metrics (Celery workers, queues)
# ---------------------------------------------------------------------------


async def get_system_metrics() -> SystemMetrics:
    """Collect Celery worker stats and queue depths."""
    from app.celery_app import celery_app

    workers: list[WorkerInfo] = []
    total_active = 0
    total_scheduled = 0

    try:
        inspector = celery_app.control.inspect()
        active_data, stats_data, scheduled_data = await asyncio.gather(
            asyncio.to_thread(lambda: inspector.active()),
            asyncio.to_thread(lambda: inspector.stats()),
            asyncio.to_thread(lambda: inspector.scheduled()),
        )

        if stats_data:
            for hostname, stat in stats_data.items():
                active_count = len((active_data or {}).get(hostname, []))
                scheduled_count = len((scheduled_data or {}).get(hostname, []))
                total_active += active_count
                total_scheduled += scheduled_count
                workers.append(
                    WorkerInfo(
                        hostname=hostname,
                        status="online",
                        active_tasks=active_count,
                        processed=stat.get("total", {}).get("tasks.auto_activity.execute_auto_activity", 0)
                        if isinstance(stat.get("total"), dict)
                        else 0,
                        pid=stat.get("pid"),
                    )
                )
    except Exception as exc:
        logger.warning("Failed to collect Celery metrics: %s", exc)

    # Queue depths from Redis LLEN
    queues: list[QueueMetrics] = []
    queue_names = ["celery", "renditions", "extraction"]
    try:
        r = aioredis.from_url(settings.redis_url)
        try:
            for qname in queue_names:
                depth = await r.llen(qname)
                queues.append(QueueMetrics(queue_name=qname, depth=depth))
        finally:
            await r.aclose()
    except Exception as exc:
        logger.warning("Failed to get queue depths from Redis: %s", exc)

    return SystemMetrics(
        workers=workers,
        queues=queues,
        total_active_tasks=total_active,
        total_scheduled_tasks=total_scheduled,
    )


# ---------------------------------------------------------------------------
# Prometheus metrics endpoint
# ---------------------------------------------------------------------------


def generate_prometheus_metrics() -> str:
    """Generate Prometheus-format text with system gauges.

    Creates a fresh registry each call to avoid duplicate metric errors
    when called concurrently.
    """
    registry = CollectorRegistry()

    health_gauge = Gauge(
        "documentum_health_status",
        "Component health status (1=healthy, 0.5=degraded, 0=unhealthy)",
        ["component"],
        registry=registry,
    )
    queue_depth_gauge = Gauge(
        "documentum_celery_queue_depth",
        "Number of messages in Celery queue",
        ["queue"],
        registry=registry,
    )
    workers_gauge = Gauge(
        "documentum_celery_workers_active",
        "Number of active Celery workers",
        registry=registry,
    )
    tasks_gauge = Gauge(
        "documentum_celery_tasks_active",
        "Number of currently active Celery tasks",
        registry=registry,
    )

    # Collect health synchronously (lightweight for Prometheus scrape)
    try:
        import asyncio as _asyncio

        loop = _asyncio.new_event_loop()
        try:
            health = loop.run_until_complete(check_all_health())
            for comp in health.components:
                val = 1.0 if comp.status == "healthy" else (0.5 if comp.status == "degraded" else 0.0)
                health_gauge.labels(component=comp.name).set(val)
        finally:
            loop.close()
    except Exception:
        logger.warning("Failed to collect health for Prometheus", exc_info=True)

    # Collect queue metrics
    try:
        loop = _asyncio.new_event_loop()
        try:
            metrics = loop.run_until_complete(get_system_metrics())
            workers_gauge.set(len(metrics.workers))
            tasks_gauge.set(metrics.total_active_tasks)
            for q in metrics.queues:
                queue_depth_gauge.labels(queue=q.queue_name).set(q.depth)
        finally:
            loop.close()
    except Exception:
        logger.warning("Failed to collect metrics for Prometheus", exc_info=True)

    return generate_latest(registry).decode("utf-8")


# ---------------------------------------------------------------------------
# Alert rule evaluation
# ---------------------------------------------------------------------------

_OPERATOR_MAP = {
    "gt": lambda v, t: v > t,
    "lt": lambda v, t: v < t,
    "eq": lambda v, t: v == t,
    "gte": lambda v, t: v >= t,
    "lte": lambda v, t: v <= t,
}


async def evaluate_alert_rules(
    db: AsyncSession,
    health: HealthResponse,
    metrics: SystemMetrics,
) -> list[str]:
    """Load enabled alert rules and compare metric values against thresholds.

    Returns list of triggered rule names.
    """
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.enabled == True,  # noqa: E712
            AlertRule.is_deleted == False,  # noqa: E712
        )
    )
    rules = list(result.scalars().all())

    if not rules:
        return []

    # Build a map of metric_name -> current value
    metric_values: dict[str, float] = {}

    # Health component metrics (1=healthy, 0=unhealthy)
    for comp in health.components:
        key = f"{comp.name}_health_ok"
        metric_values[key] = 1.0 if comp.status == "healthy" else 0.0
        # Also store as the legacy names from the plan
        if comp.name == "database":
            metric_values["db_connection_ok"] = metric_values[key]
        elif comp.name == "redis":
            metric_values["redis_ping_ok"] = metric_values[key]
        elif comp.name == "minio":
            metric_values["minio_health_ok"] = metric_values[key]

    # Queue depth metrics
    for q in metrics.queues:
        metric_values[f"celery_queue_depth_{q.queue_name}"] = float(q.depth)
        # Generic "celery_queue_depth" is the sum
    metric_values["celery_queue_depth"] = float(
        sum(q.depth for q in metrics.queues)
    )

    # Worker count
    metric_values["celery_worker_count"] = float(len(metrics.workers))
    metric_values["celery_active_tasks"] = float(metrics.total_active_tasks)

    triggered: list[str] = []
    for rule in rules:
        value = metric_values.get(rule.metric_name)
        if value is None:
            continue
        op_fn = _OPERATOR_MAP.get(rule.operator)
        if op_fn and op_fn(value, rule.threshold):
            triggered.append(rule.name)

    return triggered
