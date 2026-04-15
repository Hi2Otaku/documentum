"""SQL-based analytics service for process mining and bottleneck detection.

Queries ActivityInstance and WorkflowInstance tables to discover execution paths,
compute cycle times, and identify bottleneck activities. Results are cached in
Redis with a 600-second TTL.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    ProcessTemplate,
    WorkflowInstance,
)

logger = logging.getLogger(__name__)


async def get_execution_paths(
    db: AsyncSession,
    template_id: uuid.UUID | None = None,
    limit: int = 20,
) -> list[dict]:
    """Discover execution paths by collecting ordered activity sequences per workflow.

    For each completed workflow instance, collect the ordered sequence of activity
    names (ORDER BY started_at). Group by the path string (comma-joined), count
    frequency, and average total duration. Return top N paths by frequency.
    """
    # Build base query for completed workflow instances
    wf_query = select(WorkflowInstance.id).where(
        WorkflowInstance.completed_at.isnot(None),
        WorkflowInstance.is_deleted == False,  # noqa: E712
    )
    if template_id:
        wf_query = wf_query.where(WorkflowInstance.process_template_id == template_id)

    wf_result = await db.execute(wf_query)
    wf_ids = [row[0] for row in wf_result.all()]

    if not wf_ids:
        return []

    # For each workflow, collect ordered activity names and compute duration
    path_counts: dict[str, dict] = {}

    for wf_id in wf_ids:
        ai_query = (
            select(
                ActivityInstance.started_at,
                ActivityInstance.completed_at,
                ActivityTemplate.name,
            )
            .join(ActivityTemplate, ActivityInstance.activity_template_id == ActivityTemplate.id)
            .where(
                ActivityInstance.workflow_instance_id == wf_id,
                ActivityInstance.is_deleted == False,  # noqa: E712
            )
            .order_by(ActivityInstance.started_at)
        )
        ai_result = await db.execute(ai_query)
        rows = ai_result.all()

        if not rows:
            continue

        activity_names = [row[2] for row in rows if row[2]]
        path_key = ",".join(activity_names)

        # Compute total duration from first started_at to last completed_at
        started_times = [row[0] for row in rows if row[0] is not None]
        completed_times = [row[1] for row in rows if row[1] is not None]

        total_duration = None
        if started_times and completed_times:
            first_start = min(started_times)
            last_complete = max(completed_times)
            total_duration = (last_complete - first_start).total_seconds()

        if path_key not in path_counts:
            path_counts[path_key] = {
                "path": activity_names,
                "frequency": 0,
                "durations": [],
            }
        path_counts[path_key]["frequency"] += 1
        if total_duration is not None:
            path_counts[path_key]["durations"].append(total_duration)

    # Sort by frequency, take top N
    sorted_paths = sorted(path_counts.values(), key=lambda x: x["frequency"], reverse=True)[:limit]

    results = []
    for p in sorted_paths:
        durations = p["durations"]
        avg_dur = sum(durations) / len(durations) if durations else None
        results.append({
            "path": p["path"],
            "frequency": p["frequency"],
            "avg_total_duration_seconds": avg_dur,
        })

    return results


async def get_cycle_times(
    db: AsyncSession,
    template_id: uuid.UUID | None = None,
    group_by: str = "activity",
) -> list[dict]:
    """Compute cycle time statistics grouped by activity or template.

    For activity grouping: compute duration per completed ActivityInstance.
    For template grouping: compute duration per completed WorkflowInstance.
    Returns AVG, MIN, MAX, and median approximation (AVG as median for SQLite).
    """
    if group_by == "template":
        return await _cycle_times_by_template(db, template_id)
    return await _cycle_times_by_activity(db, template_id)


async def _cycle_times_by_activity(
    db: AsyncSession,
    template_id: uuid.UUID | None = None,
) -> list[dict]:
    """Cycle times grouped by activity name."""
    query = (
        select(
            ActivityTemplate.name.label("activity_name"),
            ActivityInstance.started_at,
            ActivityInstance.completed_at,
        )
        .join(ActivityTemplate, ActivityInstance.activity_template_id == ActivityTemplate.id)
        .where(
            ActivityInstance.completed_at.isnot(None),
            ActivityInstance.started_at.isnot(None),
            ActivityInstance.is_deleted == False,  # noqa: E712
        )
    )
    if template_id:
        query = query.join(
            WorkflowInstance, ActivityInstance.workflow_instance_id == WorkflowInstance.id
        ).where(WorkflowInstance.process_template_id == template_id)

    result = await db.execute(query)
    rows = result.all()

    # Group durations by activity name
    activity_durations: dict[str, list[float]] = {}
    for row in rows:
        name = row[0]
        duration = (row[2] - row[1]).total_seconds()
        if name not in activity_durations:
            activity_durations[name] = []
        activity_durations[name].append(duration)

    results = []
    for name, durations in activity_durations.items():
        durations.sort()
        n = len(durations)
        avg_s = sum(durations) / n
        min_s = durations[0]
        max_s = durations[-1]
        # Median: middle value for odd, average of two middle for even
        if n % 2 == 1:
            median_s = durations[n // 2]
        else:
            median_s = (durations[n // 2 - 1] + durations[n // 2]) / 2

        results.append({
            "activity_name": name,
            "template_name": None,
            "template_id": None,
            "avg_seconds": round(avg_s, 2),
            "median_seconds": round(median_s, 2),
            "min_seconds": round(min_s, 2),
            "max_seconds": round(max_s, 2),
            "sample_count": n,
        })

    return sorted(results, key=lambda x: x["sample_count"], reverse=True)


async def _cycle_times_by_template(
    db: AsyncSession,
    template_id: uuid.UUID | None = None,
) -> list[dict]:
    """Cycle times grouped by process template."""
    query = (
        select(
            ProcessTemplate.name.label("template_name"),
            ProcessTemplate.id.label("template_id"),
            WorkflowInstance.started_at,
            WorkflowInstance.completed_at,
        )
        .join(ProcessTemplate, WorkflowInstance.process_template_id == ProcessTemplate.id)
        .where(
            WorkflowInstance.completed_at.isnot(None),
            WorkflowInstance.started_at.isnot(None),
            WorkflowInstance.is_deleted == False,  # noqa: E712
        )
    )
    if template_id:
        query = query.where(WorkflowInstance.process_template_id == template_id)

    result = await db.execute(query)
    rows = result.all()

    # Group durations by template
    template_durations: dict[str, dict] = {}
    for row in rows:
        tname = row[0]
        tid = str(row[1])
        duration = (row[3] - row[2]).total_seconds()
        if tname not in template_durations:
            template_durations[tname] = {"id": tid, "durations": []}
        template_durations[tname]["durations"].append(duration)

    results = []
    for tname, data in template_durations.items():
        durations = sorted(data["durations"])
        n = len(durations)
        avg_s = sum(durations) / n
        min_s = durations[0]
        max_s = durations[-1]
        if n % 2 == 1:
            median_s = durations[n // 2]
        else:
            median_s = (durations[n // 2 - 1] + durations[n // 2]) / 2

        results.append({
            "activity_name": None,
            "template_name": tname,
            "template_id": data["id"],
            "avg_seconds": round(avg_s, 2),
            "median_seconds": round(median_s, 2),
            "min_seconds": round(min_s, 2),
            "max_seconds": round(max_s, 2),
            "sample_count": n,
        })

    return sorted(results, key=lambda x: x["sample_count"], reverse=True)


async def get_bottlenecks(
    db: AsyncSession,
    template_id: uuid.UUID | None = None,
    limit: int = 10,
) -> list[dict]:
    """Identify bottleneck activities by average duration and time consumption.

    Returns activities ranked by average duration DESC, with percentage of total
    workflow time consumed.
    """
    query = (
        select(
            ActivityTemplate.name.label("activity_name"),
            ProcessTemplate.name.label("template_name"),
            ActivityInstance.started_at,
            ActivityInstance.completed_at,
        )
        .join(ActivityTemplate, ActivityInstance.activity_template_id == ActivityTemplate.id)
        .join(WorkflowInstance, ActivityInstance.workflow_instance_id == WorkflowInstance.id)
        .join(ProcessTemplate, WorkflowInstance.process_template_id == ProcessTemplate.id)
        .where(
            ActivityInstance.completed_at.isnot(None),
            ActivityInstance.started_at.isnot(None),
            ActivityInstance.is_deleted == False,  # noqa: E712
        )
    )
    if template_id:
        query = query.where(WorkflowInstance.process_template_id == template_id)

    result = await db.execute(query)
    rows = result.all()

    if not rows:
        return []

    # Aggregate by activity name + template name
    activity_stats: dict[tuple[str, str], dict] = {}
    total_time = 0.0

    for row in rows:
        a_name = row[0]
        t_name = row[1]
        duration = (row[3] - row[2]).total_seconds()
        total_time += duration

        key = (a_name, t_name)
        if key not in activity_stats:
            activity_stats[key] = {"durations": [], "count": 0}
        activity_stats[key]["durations"].append(duration)
        activity_stats[key]["count"] += 1

    results = []
    for (a_name, t_name), stats in activity_stats.items():
        avg_dur = sum(stats["durations"]) / len(stats["durations"])
        total_activity_time = sum(stats["durations"])
        pct = (total_activity_time / total_time * 100) if total_time > 0 else 0

        results.append({
            "activity_name": a_name,
            "template_name": t_name,
            "avg_duration_seconds": round(avg_dur, 2),
            "total_executions": stats["count"],
            "pct_of_total_time": round(pct, 2),
        })

    # Sort by avg duration descending
    results.sort(key=lambda x: x["avg_duration_seconds"], reverse=True)
    return results[:limit]


async def get_analytics_summary(db: AsyncSession) -> dict:
    """Return high-level analytics summary."""
    # Total and completed instances
    total_q = select(func.count(WorkflowInstance.id)).where(
        WorkflowInstance.is_deleted == False,  # noqa: E712
    )
    total_result = await db.execute(total_q)
    total_instances = total_result.scalar() or 0

    completed_q = select(func.count(WorkflowInstance.id)).where(
        WorkflowInstance.completed_at.isnot(None),
        WorkflowInstance.is_deleted == False,  # noqa: E712
    )
    completed_result = await db.execute(completed_q)
    completed_instances = completed_result.scalar() or 0

    # Average completion time
    avg_completion: float | None = None
    if completed_instances > 0:
        # Fetch completed workflows and compute avg in Python (SQLite compat)
        comp_q = select(
            WorkflowInstance.started_at,
            WorkflowInstance.completed_at,
        ).where(
            WorkflowInstance.completed_at.isnot(None),
            WorkflowInstance.started_at.isnot(None),
            WorkflowInstance.is_deleted == False,  # noqa: E712
        )
        comp_result = await db.execute(comp_q)
        comp_rows = comp_result.all()
        if comp_rows:
            durations = [(r[1] - r[0]).total_seconds() for r in comp_rows]
            avg_completion = round(sum(durations) / len(durations), 2)

    # Paths discovered (unique activity sequences)
    paths = await get_execution_paths(db, limit=1000)
    paths_discovered = len(paths)

    # Check Redis for last_refreshed timestamp
    last_refreshed = None
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        r = aioredis.from_url(settings.redis_url)
        try:
            ts = await r.get("analytics:last_refreshed")
            if ts:
                last_refreshed = ts.decode() if isinstance(ts, bytes) else str(ts)
        finally:
            await r.aclose()
    except Exception:
        logger.debug("Could not read analytics:last_refreshed from Redis")

    return {
        "total_instances": total_instances,
        "completed_instances": completed_instances,
        "avg_completion_seconds": avg_completion,
        "paths_discovered": paths_discovered,
        "last_refreshed": last_refreshed,
    }


async def refresh_analytics_cache(db: AsyncSession) -> None:
    """Refresh all analytics data and store in Redis with 600s TTL."""
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings

        paths = await get_execution_paths(db)
        cycle_times_activity = await get_cycle_times(db, group_by="activity")
        cycle_times_template = await get_cycle_times(db, group_by="template")
        bottlenecks = await get_bottlenecks(db)
        summary = await get_analytics_summary(db)

        r = aioredis.from_url(settings.redis_url)
        try:
            pipe = r.pipeline()
            pipe.set("analytics:paths", json.dumps(paths), ex=600)
            pipe.set("analytics:cycle_times:activity", json.dumps(cycle_times_activity), ex=600)
            pipe.set("analytics:cycle_times:template", json.dumps(cycle_times_template), ex=600)
            pipe.set("analytics:bottlenecks", json.dumps(bottlenecks), ex=600)
            pipe.set("analytics:summary", json.dumps(summary), ex=600)
            pipe.set(
                "analytics:last_refreshed",
                datetime.now(timezone.utc).isoformat(),
                ex=600,
            )
            await pipe.execute()
        finally:
            await r.aclose()

        logger.info("Analytics cache refreshed successfully")
    except Exception:
        logger.exception("Failed to refresh analytics cache")
        raise
