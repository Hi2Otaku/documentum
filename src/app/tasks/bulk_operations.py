"""Celery task for executing bulk document operations.

Processes each document individually, recording success/failure per item.
Supports bulk update, delete, and lifecycle transitions.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.bulk_operations.execute_bulk_job",
    bind=True,
    max_retries=1,
)
def execute_bulk_job(self, job_id: str):
    """Execute a bulk job asynchronously via Celery."""
    try:
        asyncio.run(_execute_async(job_id))
    except Exception as exc:
        logger.error("Bulk job %s failed: %s", job_id, exc)
        raise self.retry(exc=exc)


async def _execute_async(job_id: str):
    """Async implementation of bulk job execution."""
    from sqlalchemy import select

    from app.core.database import create_task_session_factory
    from app.models.bulk_job import BulkJob
    from app.models.enums import LifecycleState
    from app.services import document_service, lifecycle_service
    from app.services.retention_service import check_document_deletable
    from app.services.audit_service import create_audit_record

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        # Load the job
        result = await session.execute(
            select(BulkJob).where(BulkJob.id == uuid.UUID(job_id))
        )
        job = result.scalar_one_or_none()
        if job is None:
            logger.warning("Bulk job %s not found, skipping", job_id)
            return

        # Mark as running
        job.status = "running"
        await session.flush()

        results = []
        success_count = 0
        failure_count = 0

        for doc_id in job.document_ids:
            try:
                if job.job_type == "update":
                    metadata = job.parameters.get("metadata", {}) if job.parameters else {}
                    await document_service.update_document_metadata(
                        session,
                        uuid.UUID(doc_id),
                        title=metadata.get("title"),
                        author=metadata.get("author"),
                        custom_properties=metadata.get("custom_properties"),
                        user_id=job.created_by,
                    )

                elif job.job_type == "delete":
                    # Check retention before soft-deleting
                    await check_document_deletable(session, uuid.UUID(doc_id))
                    doc = await document_service.get_document(session, uuid.UUID(doc_id))
                    doc.is_deleted = True
                    await session.flush()
                    await create_audit_record(
                        session,
                        entity_type="document",
                        entity_id=doc_id,
                        action="bulk_delete",
                        user_id=job.created_by,
                    )

                elif job.job_type == "lifecycle":
                    target_state = LifecycleState(job.parameters["target_state"])
                    await lifecycle_service.transition_lifecycle_state(
                        session,
                        uuid.UUID(doc_id),
                        target_state,
                        job.created_by,
                    )

                results.append({"document_id": doc_id, "status": "success"})
                success_count += 1

            except Exception as e:
                results.append({
                    "document_id": doc_id,
                    "status": "error",
                    "error": str(e),
                })
                failure_count += 1
                logger.warning(
                    "Bulk job %s: item %s failed: %s", job_id, doc_id, e
                )

        # Finalize job
        job.results = results
        job.success_count = success_count
        job.failure_count = failure_count
        job.completed_at = datetime.now(timezone.utc)
        job.status = "failed" if failure_count == job.total_count else "completed"

        await session.commit()
        logger.info(
            "Bulk job %s finished: %d success, %d failed",
            job_id, success_count, failure_count,
        )
