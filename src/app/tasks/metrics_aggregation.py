"""Periodic Celery task to pre-aggregate dashboard chart data."""
import asyncio
import logging
from datetime import datetime, timezone

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.metrics_aggregation.aggregate_dashboard_metrics")
def aggregate_dashboard_metrics():
    """Pre-aggregate bottleneck, workload, and SLA data into metrics_summary table."""
    asyncio.run(_aggregate_async())


async def _aggregate_async():
    from sqlalchemy import delete

    from app.core.database import async_session_factory
    from app.models.metrics import MetricsSummary
    from app.services.dashboard_service import (
        get_bottleneck_activities,
        get_sla_data,
        get_user_workload,
    )

    async with async_session_factory() as session:
        now = datetime.now(timezone.utc)

        # Clear old summaries
        await session.execute(delete(MetricsSummary))

        # Bottleneck data
        bottlenecks = await get_bottleneck_activities(session)
        for b in bottlenecks:
            session.add(MetricsSummary(
                metric_type="bottleneck",
                template_id=None,
                dimension_key=str(b.activity_template_id),
                dimension_label=b.activity_name,
                numeric_value=b.avg_duration_seconds,
                count_value=b.total_instances,
                computed_at=now,
            ))

        # Workload data
        workload = await get_user_workload(session)
        for w in workload:
            session.add(MetricsSummary(
                metric_type="workload",
                template_id=None,
                dimension_key=str(w.user_id),
                dimension_label=w.username,
                numeric_value=float(w.total_pending),
                count_value=w.available_count + w.acquired_count,
                computed_at=now,
            ))

        # SLA data
        sla = await get_sla_data(session)
        for s in sla:
            session.add(MetricsSummary(
                metric_type="sla",
                template_id=None,
                dimension_key=s.activity_name,
                dimension_label=s.activity_name,
                numeric_value=s.compliance_percent,
                count_value=s.on_time + s.overdue,
                computed_at=now,
            ))

        await session.commit()
        logger.info(
            "Aggregated dashboard metrics: %d bottlenecks, %d workload, %d sla",
            len(bottlenecks), len(workload), len(sla),
        )
