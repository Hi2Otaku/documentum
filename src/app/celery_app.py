"""Celery application instance for the Documentum Workflow Agent.

Configured with Redis broker, JSON serialization, and a beat schedule
that polls for active auto activities every 10 seconds.
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "documentum",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.auto_activity", "app.tasks.metrics_aggregation", "app.tasks.rendition"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.rendition.*": {"queue": "renditions"},
    },
    beat_schedule={
        "poll-auto-activities": {
            "task": "app.tasks.auto_activity.poll_auto_activities",
            "schedule": 10.0,
        },
        "aggregate-dashboard-metrics": {
            "task": "app.tasks.metrics_aggregation.aggregate_dashboard_metrics",
            "schedule": 300.0,
        },
    },
)
