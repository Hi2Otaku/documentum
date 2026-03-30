from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def create_audit_record(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    user_id: str | None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    details: str | None = None,
) -> AuditLog:
    """Create an audit log record in the current transaction.

    Does NOT commit -- the request-level transaction handles atomicity.
    """
    record = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        before_state=before_state,
        after_state=after_state,
        details=details,
    )
    db.add(record)
    return record
