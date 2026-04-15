"""Celery task for computing SHA-256 hash chains on audit log records.

Each audit record gets:
- content_hash: SHA-256 of its canonical JSON content
- chain_hash: SHA-256 incorporating the previous record's chain_hash
- chain_sequence: monotonically increasing counter for ordering
"""
import asyncio
import hashlib
import json
import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.audit_chain.compute_audit_chain_hash",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def compute_audit_chain_hash(self, audit_record_id: str):
    """Compute content_hash and chain_hash for an audit record asynchronously."""
    try:
        asyncio.run(_compute_hash_async(audit_record_id))
    except Exception as exc:
        logger.error("Failed to compute audit chain hash for %s: %s", audit_record_id, exc)
        raise self.retry(exc=exc)


async def _compute_hash_async(audit_record_id: str):
    """Async implementation of hash chain computation."""
    import uuid

    from sqlalchemy import select, func, desc

    from app.core.database import create_task_session_factory
    from app.models.audit import AuditLog

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        # Load the audit record
        result = await session.execute(
            select(AuditLog).where(AuditLog.id == uuid.UUID(audit_record_id))
        )
        record = result.scalar_one_or_none()
        if record is None:
            logger.warning("Audit record %s not found, skipping hash", audit_record_id)
            return

        # Compute content_hash from canonical JSON
        canonical_data = {
            "id": str(record.id),
            "timestamp": record.timestamp.isoformat() if record.timestamp else None,
            "entity_type": record.entity_type,
            "entity_id": record.entity_id,
            "action": record.action,
            "user_id": record.user_id,
            "before_state": record.before_state,
            "after_state": record.after_state,
            "details": record.details,
        }
        canonical_json = json.dumps(canonical_data, sort_keys=True, default=str)
        content_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        # Find previous chain record with SELECT FOR UPDATE to prevent races
        prev_result = await session.execute(
            select(AuditLog)
            .where(AuditLog.chain_sequence.isnot(None))
            .order_by(desc(AuditLog.chain_sequence))
            .limit(1)
            .with_for_update()
        )
        prev_record = prev_result.scalar_one_or_none()

        if prev_record is not None:
            previous_chain_hash = prev_record.chain_hash
            chain_sequence = prev_record.chain_sequence + 1
        else:
            previous_chain_hash = "GENESIS"
            chain_sequence = 1

        # Compute chain_hash linking to predecessor
        chain_input = f"{content_hash}:{previous_chain_hash}"
        chain_hash = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()

        # Update the record
        record.content_hash = content_hash
        record.chain_hash = chain_hash
        record.chain_sequence = chain_sequence

        await session.commit()
        logger.info(
            "Audit chain hash computed for record %s: seq=%d",
            audit_record_id,
            chain_sequence,
        )
