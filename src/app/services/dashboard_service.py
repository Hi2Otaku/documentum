"""BAM dashboard service — workflow metrics, bottleneck detection, user workload."""
import logging

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
            func.julianday(WorkflowInstance.completed_at)
            - func.julianday(WorkflowInstance.started_at)
        )
        * 86400  # Convert days to seconds
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
    avg_duration = (
        func.avg(
            func.julianday(ActivityInstance.completed_at)
            - func.julianday(ActivityInstance.started_at)
        )
        * 86400
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
    avg_completion = (
        func.avg(
            case(
                (
                    WorkflowInstance.state == WorkflowState.FINISHED,
                    (
                        func.julianday(WorkflowInstance.completed_at)
                        - func.julianday(WorkflowInstance.started_at)
                    )
                    * 86400,
                ),
                else_=None,
            )
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
