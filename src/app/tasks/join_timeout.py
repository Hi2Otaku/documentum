"""Celery task for polling timed-out join activities.

Runs on a 15-second beat schedule, scanning for DORMANT activities whose
join_timeout_started_at + join_timeout_hours has elapsed. When a timeout
is detected, the join is force-fired by consuming all tokens and activating
the activity, then advancing the workflow.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.join_timeout.check_join_timeouts")
def check_join_timeouts():
    """Periodic task: find timed-out join activities and force-fire them."""
    asyncio.run(_check_timeouts_async())


async def _check_timeouts_async():
    """Async implementation: query for timed-out joins and force-activate."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.core.database import create_task_session_factory
    from app.models.enums import ActivityState, ActivityType, TriggerType
    from app.models.workflow import (
        ActivityInstance,
        ActivityTemplate,
        ExecutionToken,
        ProcessTemplate,
        WorkflowInstance,
    )

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        now = datetime.now(timezone.utc)

        # Find DORMANT activity instances with a timeout clock that has expired
        stmt = (
            select(ActivityInstance)
            .join(
                ActivityTemplate,
                ActivityInstance.activity_template_id == ActivityTemplate.id,
            )
            .where(
                ActivityInstance.state == ActivityState.DORMANT,
                ActivityInstance.join_timeout_started_at.isnot(None),
                ActivityTemplate.trigger_type == TriggerType.TIMEOUT_JOIN,
                ActivityTemplate.join_timeout_hours.isnot(None),
            )
        )

        result = await session.execute(stmt)
        candidates = result.unique().scalars().all()

        for ai in candidates:
            # Load the template to check timeout
            at = await session.get(ActivityTemplate, ai.activity_template_id)
            if at is None or at.join_timeout_hours is None:
                continue

            # Calculate if timeout has elapsed
            from datetime import timedelta
            timeout_deadline = ai.join_timeout_started_at + timedelta(hours=at.join_timeout_hours)
            if now < timeout_deadline:
                continue

            logger.info(
                "Join timeout expired for activity instance %s (template: %s)",
                ai.id, at.name,
            )

            # Force-fire: consume all unconsumed tokens for this target
            token_result = await session.execute(
                select(ExecutionToken).where(
                    ExecutionToken.workflow_instance_id == ai.workflow_instance_id,
                    ExecutionToken.target_activity_template_id == ai.activity_template_id,
                    ExecutionToken.is_consumed == False,  # noqa: E712
                )
            )
            for t in token_result.scalars().all():
                t.is_consumed = True

            # Activate the activity
            ai.state = ActivityState.ACTIVE
            ai.started_at = now

            # Load workflow and template for advancement
            wf = await session.get(WorkflowInstance, ai.workflow_instance_id)
            if wf is None:
                continue

            template_result = await session.execute(
                select(ProcessTemplate)
                .where(ProcessTemplate.id == wf.process_template_id)
                .options(
                    selectinload(ProcessTemplate.activity_templates),
                    selectinload(ProcessTemplate.flow_templates),
                    selectinload(ProcessTemplate.process_variables),
                )
            )
            template = template_result.scalar_one()

            # For manual activities, work items will be created by the advance logic
            # For auto/end/start, the advance logic handles them
            # We mark ACTIVE and let the normal polling pick up work item creation
            # if needed, or we can directly advance for auto-completing types
            if at.activity_type in (ActivityType.START, ActivityType.END):
                ai.state = ActivityState.COMPLETE
                ai.completed_at = now

                # Build template_to_instance for advancement
                ai_result = await session.execute(
                    select(ActivityInstance).where(
                        ActivityInstance.workflow_instance_id == wf.id
                    )
                )
                all_instances = list(ai_result.scalars().all())
                template_to_instance = {
                    inst.activity_template_id: inst for inst in all_instances
                }

                from app.services.engine_service import _advance_from_activity

                await _advance_from_activity(
                    session, wf, ai, template, template_to_instance, "system",
                )

            await session.flush()

        await session.commit()
