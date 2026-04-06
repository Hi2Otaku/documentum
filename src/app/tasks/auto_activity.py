"""Celery tasks for the Workflow Agent: poll and execute auto activities.

The poll task runs on a 10-second beat schedule, scanning for ACTIVE AUTO
activities and dispatching individual execution tasks. Each execution task
runs the registered auto method, logs results, and advances the workflow
on success or marks ERROR after 3 retries with exponential backoff.
"""
import asyncio
import logging
import traceback
import uuid
from datetime import datetime, timezone

from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.auto_activity.poll_auto_activities")
def poll_auto_activities():
    """Periodic task: find ACTIVE AUTO activities and dispatch execution tasks."""
    asyncio.run(_poll_async())


async def _poll_async():
    """Async implementation of poll: query for active auto activities."""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from app.core.database import create_task_session_factory
    from app.models.enums import ActivityState, ActivityType
    from app.models.workflow import ActivityInstance, ActivityTemplate

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        stmt = (
            select(ActivityInstance)
            .join(
                ActivityTemplate,
                ActivityInstance.activity_template_id == ActivityTemplate.id,
            )
            .where(
                ActivityInstance.state == ActivityState.ACTIVE,
                ActivityTemplate.activity_type == ActivityType.AUTO,
            )
            .options(joinedload(ActivityInstance.activity_template))
        )

        # Use row-level locking on PostgreSQL to prevent duplicate dispatch
        dialect_name = session.bind.dialect.name if session.bind else "sqlite"
        if dialect_name != "sqlite":
            stmt = stmt.with_for_update(skip_locked=True)

        result = await session.execute(stmt)
        active_auto_activities = result.unique().scalars().all()

        for ai in active_auto_activities:
            logger.info(
                "Dispatching auto activity %s (method: %s)",
                ai.id,
                ai.activity_template.method_name if ai.activity_template else "unknown",
            )
            execute_auto_activity.delay(str(ai.id), str(ai.workflow_instance_id))

        await session.commit()


@celery_app.task(
    name="app.tasks.auto_activity.execute_auto_activity",
    bind=True,
    max_retries=3,
    soft_time_limit=60,
)
def execute_auto_activity(self, activity_instance_id: str, workflow_instance_id: str):
    """Execute a single auto activity: run method, log result, advance workflow."""
    asyncio.run(_execute_async(self, activity_instance_id, workflow_instance_id))


async def _execute_async(task, activity_instance_id: str, workflow_instance_id: str):
    """Async implementation of auto activity execution."""
    from sqlalchemy import func, select
    from sqlalchemy.orm import joinedload, selectinload

    from app.auto_methods import get_auto_method
    from app.auto_methods.context import ActivityContext
    from app.core.database import create_task_session_factory
    from app.models.enums import ActivityState, ActivityType
    from app.models.execution_log import AutoActivityLog
    from app.models.workflow import (
        ActivityInstance,
        ActivityTemplate,
        ProcessTemplate,
        ProcessVariable,
        WorkflowInstance,
        WorkflowPackage,
    )

    ai_id = uuid.UUID(activity_instance_id)
    wf_id = uuid.UUID(workflow_instance_id)

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        # Load activity instance with template
        result = await session.execute(
            select(ActivityInstance)
            .where(ActivityInstance.id == ai_id)
            .options(joinedload(ActivityInstance.activity_template))
        )
        activity_instance = result.unique().scalar_one_or_none()

        if activity_instance is None:
            logger.warning("Activity instance %s not found", ai_id)
            return

        # Guard: only process ACTIVE activities
        if activity_instance.state != ActivityState.ACTIVE:
            logger.debug(
                "Activity %s is %s, skipping",
                ai_id,
                activity_instance.state.value,
            )
            return

        activity_template = activity_instance.activity_template

        # Guard: only process AUTO activities
        if activity_template is None or activity_template.activity_type != ActivityType.AUTO:
            logger.warning("Activity %s is not AUTO type", ai_id)
            return

        # Look up the registered auto method
        method = get_auto_method(activity_template.method_name)
        if method is None:
            raise ValueError(
                f"Auto method '{activity_template.method_name}' not registered"
            )

        # Load workflow instance
        wf_result = await session.execute(
            select(WorkflowInstance).where(WorkflowInstance.id == wf_id)
        )
        workflow = wf_result.scalar_one_or_none()
        if workflow is None:
            raise ValueError(f"Workflow instance {wf_id} not found")

        # Load process variables
        pv_result = await session.execute(
            select(ProcessVariable).where(
                ProcessVariable.workflow_instance_id == wf_id,
                ProcessVariable.is_deleted == False,  # noqa: E712
            )
        )
        process_variables = list(pv_result.scalars().all())

        # Resolve variable values
        from app.services.engine_service import _resolve_variable_value

        variables = {pv.name: _resolve_variable_value(pv) for pv in process_variables}

        # Load document IDs from workflow packages
        pkg_result = await session.execute(
            select(WorkflowPackage.document_id).where(
                WorkflowPackage.workflow_instance_id == wf_id,
                WorkflowPackage.is_deleted == False,  # noqa: E712
            )
        )
        document_ids = [row[0] for row in pkg_result.all()]

        # Determine attempt number
        attempt_count_result = await session.execute(
            select(func.count(AutoActivityLog.id)).where(
                AutoActivityLog.activity_instance_id == ai_id
            )
        )
        attempt_number = (attempt_count_result.scalar() or 0) + 1

        # Create log entry
        now = datetime.now(timezone.utc)
        log_entry = AutoActivityLog(
            activity_instance_id=ai_id,
            method_name=activity_template.method_name,
            attempt_number=attempt_number,
            status="running",
            started_at=now,
        )
        session.add(log_entry)
        await session.flush()

        # Build activity context
        ctx = ActivityContext(
            db=session,
            workflow_instance=workflow,
            activity_instance=activity_instance,
            activity_template=activity_template,
            variables=variables,
            document_ids=document_ids,
            user_id="system",
        )

        try:
            # Execute the auto method
            result_data = await method(ctx)

            # Success: update log
            log_entry.status = "success"
            log_entry.completed_at = datetime.now(timezone.utc)
            log_entry.result_data = result_data

            # Load full template for advancement
            template_result = await session.execute(
                select(ProcessTemplate)
                .where(ProcessTemplate.id == workflow.process_template_id)
                .options(
                    selectinload(ProcessTemplate.activity_templates),
                    selectinload(ProcessTemplate.flow_templates),
                    selectinload(ProcessTemplate.process_variables),
                )
            )
            template = template_result.scalar_one()

            # Build template_to_instance mapping
            ai_result = await session.execute(
                select(ActivityInstance).where(
                    ActivityInstance.workflow_instance_id == wf_id
                )
            )
            all_instances = list(ai_result.scalars().all())
            template_to_instance = {
                inst.activity_template_id: inst for inst in all_instances
            }

            # Reload process variables for advancement
            pv_result2 = await session.execute(
                select(ProcessVariable).where(
                    ProcessVariable.workflow_instance_id == wf_id,
                    ProcessVariable.is_deleted == False,  # noqa: E712
                )
            )
            instance_variables = list(pv_result2.scalars().all())

            # Advance workflow from the completed auto activity
            from app.services.engine_service import _advance_from_activity

            await _advance_from_activity(
                session,
                workflow,
                activity_instance,
                template,
                template_to_instance,
                "system",
                instance_variables=instance_variables,
            )

            await session.commit()
            logger.info(
                "Auto activity %s completed successfully (method: %s)",
                ai_id,
                activity_template.method_name,
            )

        except SoftTimeLimitExceeded:
            # Timeout handling
            await session.rollback()

            async with session_factory() as err_session:
                log_entry_timeout = AutoActivityLog(
                    activity_instance_id=ai_id,
                    method_name=activity_template.method_name,
                    attempt_number=attempt_number,
                    status="timeout",
                    error_message="Task exceeded soft time limit of 60 seconds",
                    started_at=now,
                    completed_at=datetime.now(timezone.utc),
                )
                err_session.add(log_entry_timeout)

                if attempt_number >= 3:
                    ai_reload = await err_session.get(ActivityInstance, ai_id)
                    if ai_reload:
                        ai_reload.state = ActivityState.ERROR
                    await err_session.commit()
                else:
                    await err_session.commit()
                    backoff = 10 * (3 ** (attempt_number - 1))
                    raise task.retry(countdown=backoff)

        except Exception as e:
            # Error handling
            await session.rollback()

            async with session_factory() as err_session:
                log_entry_err = AutoActivityLog(
                    activity_instance_id=ai_id,
                    method_name=activity_template.method_name,
                    attempt_number=attempt_number,
                    status="error",
                    error_message=str(e),
                    error_traceback=traceback.format_exc(),
                    started_at=now,
                    completed_at=datetime.now(timezone.utc),
                )
                err_session.add(log_entry_err)

                if attempt_number >= 3:
                    # Max retries exceeded: mark activity as ERROR
                    ai_reload = await err_session.get(ActivityInstance, ai_id)
                    if ai_reload:
                        ai_reload.state = ActivityState.ERROR
                    await err_session.commit()
                    logger.error(
                        "Auto activity %s failed after %d attempts: %s",
                        ai_id,
                        attempt_number,
                        str(e),
                    )
                else:
                    await err_session.commit()
                    # Retry with exponential backoff: 10s, 30s, 90s
                    backoff = 10 * (3 ** (attempt_number - 1))
                    logger.warning(
                        "Auto activity %s failed (attempt %d), retrying in %ds: %s",
                        ai_id,
                        attempt_number,
                        backoff,
                        str(e),
                    )
                    try:
                        raise task.retry(exc=e, countdown=backoff)
                    except MaxRetriesExceededError:
                        async with session_factory() as max_session:
                            ai_reload2 = await max_session.get(ActivityInstance, ai_id)
                            if ai_reload2:
                                ai_reload2.state = ActivityState.ERROR
                            await max_session.commit()
                        logger.error(
                            "Auto activity %s max retries exceeded", ai_id
                        )
