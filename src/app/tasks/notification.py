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

    NOTE: WorkItem does not have due_date yet -- Phase 17 adds timer activities
    and deadline fields. This is a placeholder that ensures the beat task exists
    and runs without error.
    """
    logger.info("Checking for approaching deadlines...")
    logger.info("No deadline checking configured yet (Phase 17 will add due_date to WorkItem)")
