"""Built-in auto methods for automated workflow activities.

Provides four standard auto methods:
- send_email: Send email notifications (dev mode logs, prod mode uses SMTP)
- change_lifecycle_state: Transition document lifecycle states
- modify_acl: Add or remove ACL entries on documents
- call_external_api: POST to external REST APIs
"""
import asyncio
import json
import logging
from typing import Any

from app.auto_methods import auto_method
from app.auto_methods.context import ActivityContext

logger = logging.getLogger(__name__)


@auto_method("send_email")
async def send_email(ctx: ActivityContext) -> dict[str, Any] | None:
    """Send an email notification using process variables.

    Reads email_to, email_subject, email_body from process variables.
    In dev mode (smtp_host empty), logs the email and returns dev result.
    In prod mode, sends via SMTP (sync, wrapped in asyncio.to_thread).
    """
    email_to = await ctx.get_variable("email_to")
    email_subject = await ctx.get_variable("email_subject")
    email_body = await ctx.get_variable("email_body")

    from app.core.config import settings

    if not settings.smtp_host:
        # Dev mode: log and return
        logger.info(
            "Dev mode email: to=%s, subject=%s, body=%s",
            email_to, email_subject, email_body,
        )
        return {"mode": "dev", "to": email_to, "subject": email_subject, "body": email_body}

    # Production mode: send via SMTP
    import smtplib
    from email.mime.text import MIMEText

    def _send():
        msg = MIMEText(email_body or "")
        msg["Subject"] = email_subject or ""
        msg["From"] = settings.smtp_from_email
        msg["To"] = email_to or ""
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_username:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)

    await asyncio.to_thread(_send)
    return {"sent": True, "to": email_to}


@auto_method("change_lifecycle_state")
async def change_lifecycle_state(ctx: ActivityContext) -> dict[str, Any] | None:
    """Transition lifecycle state for all documents in the workflow package.

    Reads target_lifecycle_state from process variables.
    Calls lifecycle_service.transition_lifecycle_state for each document.
    """
    target_state_str = await ctx.get_variable("target_lifecycle_state")
    if not target_state_str:
        raise ValueError("Process variable 'target_lifecycle_state' is required")

    from app.models.enums import LifecycleState
    from app.services.lifecycle_service import transition_lifecycle_state

    target_state = LifecycleState(target_state_str)
    transitions = []

    for doc_id in ctx.document_ids:
        await transition_lifecycle_state(ctx.db, doc_id, target_state, ctx.user_id)
        transitions.append({"document_id": str(doc_id), "new_state": target_state_str})

    return {"transitions": transitions}


@auto_method("modify_acl")
async def modify_acl(ctx: ActivityContext) -> dict[str, Any] | None:
    """Add or remove ACL entries on workflow documents.

    Reads acl_action ("add" or "remove"), acl_user_id, acl_permission
    from process variables.
    """
    acl_action = await ctx.get_variable("acl_action")
    acl_user_id = await ctx.get_variable("acl_user_id")
    acl_permission = await ctx.get_variable("acl_permission")

    if not acl_action or not acl_user_id or not acl_permission:
        raise ValueError("Process variables 'acl_action', 'acl_user_id', 'acl_permission' are required")

    from app.models.enums import PermissionLevel
    from app.services.acl_service import create_acl_entry, remove_acl_entry

    import uuid as uuid_mod
    target_user_id = uuid_mod.UUID(acl_user_id) if isinstance(acl_user_id, str) else acl_user_id
    permission = PermissionLevel(acl_permission)
    count = 0

    for doc_id in ctx.document_ids:
        if acl_action == "add":
            await create_acl_entry(ctx.db, doc_id, target_user_id, "user", permission, ctx.user_id)
        elif acl_action == "remove":
            await remove_acl_entry(ctx.db, doc_id, target_user_id, permission)
        else:
            raise ValueError(f"Invalid acl_action: {acl_action}. Must be 'add' or 'remove'.")
        count += 1

    return {"modified": count}


@auto_method("call_external_api")
async def call_external_api(ctx: ActivityContext) -> dict[str, Any] | None:
    """POST to an external REST API endpoint.

    Reads api_url and optional api_payload_template from process variables.
    Sends workflow context as JSON payload. Stores response in process variables.
    """
    import httpx

    api_url = await ctx.get_variable("api_url")
    if not api_url:
        raise ValueError("Process variable 'api_url' is required")

    api_payload_template = await ctx.get_variable("api_payload_template")
    timeout_val = await ctx.get_variable("api_timeout")
    timeout = int(timeout_val) if timeout_val else 30

    # Build payload
    payload: dict[str, Any] = {
        "workflow_id": str(ctx.workflow_instance.id),
        "activity_id": str(ctx.activity_instance.id),
        "variables": {k: str(v) if v is not None else None for k, v in ctx.variables.items()},
    }

    # Merge with payload template if provided
    if api_payload_template:
        try:
            template_data = json.loads(api_payload_template) if isinstance(api_payload_template, str) else api_payload_template
            payload.update(template_data)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse api_payload_template, using default payload")

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(api_url, json=payload)

    # Store response in process variables
    await ctx.set_variable("api_response_status", str(response.status_code))
    await ctx.set_variable("api_response_body", response.text)

    return {"status": response.status_code, "url": api_url}
