"""BAM dashboard service — workflow metrics, bottleneck detection, user workload."""
import logging
import uuid as _uuid

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActivityState, WorkflowState, WorkItemState
from app.models.user import User
from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    ProcessTemplate,
    WorkflowInstance,
    WorkItem,
)
from app.schemas.dashboard import (
    BottleneckActivity,
    DashboardBottleneck,
    DashboardMetrics,
    DashboardWorkload,
    KpiMetrics,
    SlaCompliance,
    TemplateMetric,
    UserWorkload,
    WorkflowCountByState,
    WorkflowSummary,
)

logger = logging.getLogger(__name__)


async def get_workflow_summary(db: AsyncSession) -> WorkflowSummary:
    """Return total workflow count by state and average completion time."""
    # Count by state
    stmt = (
        select(WorkflowInstance.state, func.count())
        .where(WorkflowInstance.is_deleted == False)  # noqa: E712
        .group_by(WorkflowInstance.state)
    )
    result = await db.execute(stmt)
    rows = result.all()

    by_state = [WorkflowCountByState(state=row[0].value, count=row[1]) for row in rows]
    total = sum(item.count for item in by_state)

    # Average completion time for finished workflows
    avg_stmt = select(
        func.avg(
            func.extract('epoch', WorkflowInstance.completed_at)
            - func.extract('epoch', WorkflowInstance.started_at)
        )  # Already in seconds
    ).where(
        WorkflowInstance.state == WorkflowState.FINISHED,
        WorkflowInstance.completed_at.isnot(None),
        WorkflowInstance.started_at.isnot(None),
        WorkflowInstance.is_deleted == False,  # noqa: E712
    )
    avg_result = await db.execute(avg_stmt)
    avg_seconds = avg_result.scalar()

    return WorkflowSummary(
        total=total,
        by_state=by_state,
        avg_completion_seconds=float(avg_seconds) if avg_seconds is not None else None,
    )


async def get_bottleneck_activities(
    db: AsyncSession, limit: int = 10
) -> list[BottleneckActivity]:
    """Identify activities with the longest average duration."""
    # Average duration for completed activity instances
    avg_duration = func.avg(
        func.extract('epoch', ActivityInstance.completed_at)
        - func.extract('epoch', ActivityInstance.started_at)
    )

    # Count currently active instances
    active_count = func.sum(
        case(
            (ActivityInstance.state == ActivityState.ACTIVE, 1),
            else_=0,
        )
    )

    stmt = (
        select(
            ActivityInstance.activity_template_id,
            ActivityTemplate.name,
            ProcessTemplate.name.label("template_name"),
            avg_duration.label("avg_duration_seconds"),
            func.count().label("total_instances"),
            active_count.label("currently_active"),
        )
        .join(
            ActivityTemplate,
            ActivityInstance.activity_template_id == ActivityTemplate.id,
        )
        .join(
            ProcessTemplate,
            ActivityTemplate.process_template_id == ProcessTemplate.id,
        )
        .where(
            ActivityInstance.is_deleted == False,  # noqa: E712
            ActivityInstance.started_at.isnot(None),
        )
        .group_by(
            ActivityInstance.activity_template_id,
            ActivityTemplate.name,
            ProcessTemplate.name,
        )
        .order_by(avg_duration.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        BottleneckActivity(
            activity_template_id=row[0],
            activity_name=row[1],
            template_name=row[2],
            avg_duration_seconds=float(row[3]) if row[3] is not None else 0.0,
            total_instances=row[4],
            currently_active=row[5] or 0,
        )
        for row in rows
    ]


async def get_user_workload(db: AsyncSession) -> list[UserWorkload]:
    """Return pending work item counts per user."""
    available_count = func.sum(
        case(
            (WorkItem.state == WorkItemState.AVAILABLE, 1),
            else_=0,
        )
    )
    acquired_count = func.sum(
        case(
            (WorkItem.state == WorkItemState.ACQUIRED, 1),
            else_=0,
        )
    )

    stmt = (
        select(
            WorkItem.performer_id,
            User.username,
            available_count.label("available_count"),
            acquired_count.label("acquired_count"),
        )
        .join(User, WorkItem.performer_id == User.id)
        .where(
            WorkItem.is_deleted == False,  # noqa: E712
            WorkItem.state.in_([WorkItemState.AVAILABLE, WorkItemState.ACQUIRED]),
        )
        .group_by(WorkItem.performer_id, User.username)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        UserWorkload(
            user_id=row[0],
            username=row[1],
            available_count=row[2] or 0,
            acquired_count=row[3] or 0,
            total_pending=(row[2] or 0) + (row[3] or 0),
        )
        for row in rows
    ]


async def get_template_metrics(db: AsyncSession) -> list[TemplateMetric]:
    """Return instance count and state breakdown per template."""
    running_count = func.sum(
        case((WorkflowInstance.state == WorkflowState.RUNNING, 1), else_=0)
    )
    finished_count = func.sum(
        case((WorkflowInstance.state == WorkflowState.FINISHED, 1), else_=0)
    )
    failed_count = func.sum(
        case((WorkflowInstance.state == WorkflowState.FAILED, 1), else_=0)
    )
    avg_completion = func.avg(
        case(
            (
                WorkflowInstance.state == WorkflowState.FINISHED,
                func.extract('epoch', WorkflowInstance.completed_at)
                - func.extract('epoch', WorkflowInstance.started_at),
            ),
            else_=None,
        )
    )

    stmt = (
        select(
            ProcessTemplate.id,
            ProcessTemplate.name,
            func.count().label("total_instances"),
            running_count.label("running"),
            finished_count.label("finished"),
            failed_count.label("failed"),
            avg_completion.label("avg_completion_seconds"),
        )
        .join(
            WorkflowInstance,
            WorkflowInstance.process_template_id == ProcessTemplate.id,
        )
        .where(
            WorkflowInstance.is_deleted == False,  # noqa: E712
            ProcessTemplate.is_deleted == False,  # noqa: E712
        )
        .group_by(ProcessTemplate.id, ProcessTemplate.name)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        TemplateMetric(
            template_id=row[0],
            template_name=row[1],
            total_instances=row[2],
            running=row[3] or 0,
            finished=row[4] or 0,
            failed=row[5] or 0,
            avg_completion_seconds=float(row[6]) if row[6] is not None else None,
        )
        for row in rows
    ]


async def get_sla_data(
    db: AsyncSession, template_id: _uuid.UUID | None = None
) -> list[SlaCompliance]:
    """Compute SLA compliance per activity using expected_duration_hours.

    Only includes activities where ActivityTemplate.expected_duration_hours IS NOT NULL
    and only COMPLETED work items.
    """
    # Duration in hours: epoch difference / 3600
    duration_hours = (
        func.extract('epoch', WorkItem.completed_at)
        - func.extract('epoch', WorkItem.created_at)
    ) / 3600

    on_time_count = func.sum(
        case(
            (duration_hours <= ActivityTemplate.expected_duration_hours, 1),
            else_=0,
        )
    )
    overdue_count = func.sum(
        case(
            (duration_hours > ActivityTemplate.expected_duration_hours, 1),
            else_=0,
        )
    )

    stmt = (
        select(
            ActivityTemplate.name.label("activity_name"),
            on_time_count.label("on_time"),
            overdue_count.label("overdue"),
        )
        .select_from(WorkItem)
        .join(ActivityInstance, WorkItem.activity_instance_id == ActivityInstance.id)
        .join(ActivityTemplate, ActivityInstance.activity_template_id == ActivityTemplate.id)
        .where(
            WorkItem.state == WorkItemState.COMPLETE,
            WorkItem.completed_at.isnot(None),
            WorkItem.is_deleted == False,  # noqa: E712
            ActivityTemplate.expected_duration_hours.isnot(None),
        )
        .group_by(ActivityTemplate.name)
    )

    if template_id is not None:
        stmt = stmt.join(
            WorkflowInstance,
            ActivityInstance.workflow_instance_id == WorkflowInstance.id,
        ).where(WorkflowInstance.process_template_id == template_id)

    result = await db.execute(stmt)
    rows = result.all()

    sla_list: list[SlaCompliance] = []
    for row in rows:
        on_time = row[1] or 0
        overdue = row[2] or 0
        total = on_time + overdue
        pct = (on_time / total * 100) if total > 0 else 0.0
        sla_list.append(
            SlaCompliance(
                activity_name=row[0],
                on_time=on_time,
                overdue=overdue,
                compliance_percent=round(pct, 2),
            )
        )
    return sla_list


async def get_kpi_metrics(
    db: AsyncSession, template_id: _uuid.UUID | None = None
) -> KpiMetrics:
    """Return KPI metrics matching the frontend KpiMetrics interface."""
    running_count = func.sum(
        case((WorkflowInstance.state == WorkflowState.RUNNING, 1), else_=0)
    )
    halted_count = func.sum(
        case((WorkflowInstance.state == WorkflowState.HALTED, 1), else_=0)
    )
    finished_count = func.sum(
        case((WorkflowInstance.state == WorkflowState.FINISHED, 1), else_=0)
    )
    failed_count = func.sum(
        case((WorkflowInstance.state == WorkflowState.FAILED, 1), else_=0)
    )

    stmt = (
        select(
            running_count.label("running"),
            halted_count.label("halted"),
            finished_count.label("finished"),
            failed_count.label("failed"),
        )
        .where(WorkflowInstance.is_deleted == False)  # noqa: E712
    )
    if template_id is not None:
        stmt = stmt.where(WorkflowInstance.process_template_id == template_id)

    result = await db.execute(stmt)
    row = result.one()

    # Average completion hours for finished workflows
    avg_stmt = select(
        func.avg(
            (
                func.extract('epoch', WorkflowInstance.completed_at)
                - func.extract('epoch', WorkflowInstance.started_at)
            )
            / 3600  # seconds -> hours
        )
    ).where(
        WorkflowInstance.state == WorkflowState.FINISHED,
        WorkflowInstance.completed_at.isnot(None),
        WorkflowInstance.started_at.isnot(None),
        WorkflowInstance.is_deleted == False,  # noqa: E712
    )
    if template_id is not None:
        avg_stmt = avg_stmt.where(WorkflowInstance.process_template_id == template_id)

    avg_result = await db.execute(avg_stmt)
    avg_hours = avg_result.scalar()

    return KpiMetrics(
        running=row[0] or 0,
        halted=row[1] or 0,
        finished=row[2] or 0,
        failed=row[3] or 0,
        avg_completion_hours=round(float(avg_hours), 2) if avg_hours is not None else 0.0,
    )


async def get_all_metrics(
    db: AsyncSession, template_id: _uuid.UUID | None = None
) -> DashboardMetrics:
    """Return unified dashboard metrics combining KPIs, bottlenecks, workload, and SLA."""
    kpi = await get_kpi_metrics(db, template_id)
    bottlenecks = await get_bottleneck_activities(db)
    workload_raw = await get_user_workload(db)
    sla = await get_sla_data(db, template_id)

    # Reshape bottlenecks: convert avg_duration_seconds -> avg_duration_hours
    bottleneck_list = [
        DashboardBottleneck(
            activity_name=b.activity_name,
            avg_duration_hours=round(b.avg_duration_seconds / 3600, 2),
            template_name=b.template_name,
        )
        for b in bottlenecks
    ]

    # Get completed counts per user for workload reshaping
    completed_counts: dict[_uuid.UUID, int] = {}
    completed_stmt = (
        select(
            WorkItem.performer_id,
            func.count().label("completed"),
        )
        .where(
            WorkItem.is_deleted == False,  # noqa: E712
            WorkItem.state == WorkItemState.COMPLETE,
            WorkItem.performer_id.isnot(None),
        )
        .group_by(WorkItem.performer_id)
    )
    completed_result = await db.execute(completed_stmt)
    for crow in completed_result.all():
        completed_counts[crow[0]] = crow[1]

    # Reshape workload: available+acquired -> assigned, total_pending -> pending
    workload_list = [
        DashboardWorkload(
            user_id=w.user_id,
            username=w.username,
            assigned=w.available_count + w.acquired_count,
            completed=completed_counts.get(w.user_id, 0),
            pending=w.total_pending,
        )
        for w in workload_raw
    ]

    return DashboardMetrics(
        kpi=kpi,
        bottleneck_activities=bottleneck_list,
        workload=workload_list,
        sla_compliance=sla,
    )
