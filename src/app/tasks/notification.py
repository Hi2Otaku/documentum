"""Celery tasks for notification delivery: email sending and deadline checking."""
import asyncio
import logging
from pathlib import Path

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.notification.send_notification_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_notification_email(self, notification_id: str):
    """Send an email for a notification. Retries up to 3 times on failure."""
    asyncio.run(_send_email_async(self, notification_id))


async def _send_email_async(task, notification_id: str):
    """Async implementation of email sending."""
    import uuid

    from app.core.config import settings
    from app.core.database import create_task_session_factory

    if not settings.smtp_host:
        logger.warning("SMTP not configured, skipping email for notification %s", notification_id)
        return

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        from sqlalchemy import select

        from app.models.notification import Notification
        from app.models.user import User

        # Fetch notification
        result = await session.execute(
            select(Notification).where(Notification.id == uuid.UUID(notification_id))
        )
        notification = result.scalar_one_or_none()
        if notification is None:
            logger.warning("Notification %s not found, skipping email", notification_id)
            return

        # Fetch user
        user_result = await session.execute(
            select(User).where(User.id == notification.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            logger.warning("User for notification %s not found", notification_id)
            return

        if not getattr(user, "email", None):
            logger.warning(
                "User %s has no email address, skipping email for notification %s",
                user.username,
                notification_id,
            )
            return

        # Determine template name based on notification type
        template_map = {
            "task_assigned": "task_assigned.html",
            "task_delegated": "task_assigned.html",
            "deadline_approaching": "deadline_approaching.html",
        }
        notification_type = notification.notification_type.lower()
        template_name = template_map.get(notification_type)
        if template_name is None:
            logger.debug(
                "No email template for notification type '%s', skipping",
                notification.notification_type,
            )
            return

        try:
            from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

            conf = ConnectionConfig(
                MAIL_USERNAME=settings.smtp_username,
                MAIL_PASSWORD=settings.smtp_password,
                MAIL_FROM=settings.smtp_from_email,
                MAIL_PORT=settings.smtp_port,
                MAIL_SERVER=settings.smtp_host,
                MAIL_STARTTLS=True,
                MAIL_SSL_TLS=False,
                USE_CREDENTIALS=bool(settings.smtp_username),
                VALIDATE_CERTS=False,
                TEMPLATE_FOLDER=Path(__file__).parent.parent / "templates" / "email",
            )

            message = MessageSchema(
                subject=notification.title,
                recipients=[user.email],
                template_body={
                    "title": notification.title,
                    "message": notification.message or "",
                    "username": user.username,
                },
                subtype=MessageType.html,
            )

            fm = FastMail(conf)
            await fm.send_message(message, template_name=template_name)
            logger.info(
                "Email sent for notification %s to %s", notification_id, user.email
            )
        except Exception as exc:
            logger.error(
                "Failed to send email for notification %s: %s",
                notification_id,
                exc,
            )
            raise task.retry(exc=exc)


@celery_app.task(name="app.tasks.notification.check_approaching_deadlines")
def check_approaching_deadlines():
    """Periodic task: check for work items approaching their deadlines."""
    asyncio.run(_check_deadlines_async())


async def _check_deadlines_async():
    """Async implementation of deadline checking.

    Finds work items approaching their deadline (warning) and overdue items
    (escalation). Runs every 5 minutes via Celery Beat.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from app.core.database import create_task_session_factory
    from app.models.enums import WorkItemState
    from app.models.workflow import (
        ActivityInstance,
        ActivityTemplate,
        WorkflowInstance,
        WorkItem,
    )
    from app.services.notification_service import create_notification

    logger.info("Checking for approaching deadlines...")
    now = datetime.now(timezone.utc)

    session_factory = create_task_session_factory()
    async with session_factory() as db:
        # ---- APPROACHING DEADLINE WARNINGS ----
        # Work items that are active, have a due_date in the future, and
        # haven't received a warning yet.
        approaching_q = (
            select(WorkItem, ActivityTemplate)
            .join(ActivityInstance, WorkItem.activity_instance_id == ActivityInstance.id)
            .join(ActivityTemplate, ActivityInstance.activity_template_id == ActivityTemplate.id)
            .where(
                WorkItem.state.in_([
                    WorkItemState.AVAILABLE,
                    WorkItemState.ACQUIRED,
                    WorkItemState.DELEGATED,
                ]),
                WorkItem.is_deleted == False,  # noqa: E712
                WorkItem.deadline_warning_sent == False,  # noqa: E712
                WorkItem.due_date.isnot(None),
                WorkItem.due_date > now,  # Not yet overdue
            )
        )
        result = await db.execute(approaching_q)
        approaching_rows = result.all()

        warned_count = 0
        for work_item, activity_template in approaching_rows:
            # Compute warning threshold
            threshold_hours = activity_template.warning_threshold_hours
            if threshold_hours is None and activity_template.expected_duration_hours is not None:
                threshold_hours = activity_template.expected_duration_hours * 0.25
            if threshold_hours is None:
                continue  # No threshold computable

            warning_boundary = work_item.due_date - timedelta(hours=threshold_hours)
            if now >= warning_boundary:
                # Within warning window
                if work_item.performer_id:
                    await create_notification(
                        db,
                        user_id=work_item.performer_id,
                        title="Deadline approaching",
                        message=(
                            f"Work item for '{activity_template.name}' is due at "
                            f"{work_item.due_date.strftime('%Y-%m-%d %H:%M UTC')}"
                        ),
                        notification_type="deadline_approaching",
                        entity_type="work_item",
                        entity_id=work_item.id,
                    )
                work_item.deadline_warning_sent = True
                warned_count += 1

        # ---- OVERDUE ESCALATION ----
        overdue_q = (
            select(WorkItem, ActivityTemplate)
            .join(ActivityInstance, WorkItem.activity_instance_id == ActivityInstance.id)
            .join(ActivityTemplate, ActivityInstance.activity_template_id == ActivityTemplate.id)
            .where(
                WorkItem.state.in_([
                    WorkItemState.AVAILABLE,
                    WorkItemState.ACQUIRED,
                    WorkItemState.DELEGATED,
                ]),
                WorkItem.is_deleted == False,  # noqa: E712
                WorkItem.is_escalated == False,  # noqa: E712
                WorkItem.due_date.isnot(None),
                WorkItem.due_date <= now,  # Overdue
            )
        )
        overdue_result = await db.execute(overdue_q)
        overdue_rows = overdue_result.all()

        escalated_count = 0
        for work_item, activity_template in overdue_rows:
            await _escalate_work_item(db, work_item, activity_template)
            escalated_count += 1

        await db.commit()
        logger.info(
            "Deadline check complete: %d warnings sent, %d items escalated",
            warned_count,
            escalated_count,
        )


async def _escalate_work_item(db, work_item, activity_template) -> None:
    """Apply the configured escalation action to an overdue work item."""
    from sqlalchemy import select

    from app.models.workflow import (
        ActivityInstance,
        WorkflowInstance,
    )
    from app.services.notification_service import create_notification

    action = activity_template.escalation_action

    if action == "priority_bump":
        work_item.priority = max(1, work_item.priority - 2)
    elif action == "reassign":
        # Reassign to workflow instance supervisor
        wf_result = await db.execute(
            select(WorkflowInstance)
            .join(
                ActivityInstance,
                WorkflowInstance.id == ActivityInstance.workflow_instance_id,
            )
            .where(ActivityInstance.id == work_item.activity_instance_id)
        )
        wf = wf_result.scalar_one_or_none()
        if wf and wf.supervisor_id:
            work_item.performer_id = wf.supervisor_id
        else:
            logger.warning(
                "No supervisor for reassignment on work item %s, falling back to notify",
                work_item.id,
            )
    # For "notify" action or fallback: just notification, no state change

    work_item.is_escalated = True

    if work_item.performer_id:
        await create_notification(
            db,
            user_id=work_item.performer_id,
            title="Work item overdue - escalated",
            message=(
                f"Work item for '{activity_template.name}' is overdue and has been "
                f"escalated ({action or 'notify'})"
            ),
            notification_type="deadline_escalated",
            entity_type="work_item",
            entity_id=work_item.id,
        )
