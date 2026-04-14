"""Celery tasks for document text extraction and search index updates.

Extracts text from PDF (pdfplumber), DOCX (python-docx), and plain text files,
then updates the search_vector tsvector column with weighted terms.
"""
import asyncio
import io
import logging
import uuid

from app.celery_app import celery_app

logger = logging.getLogger(__name__)

PDF_TYPES = {"application/pdf"}
DOCX_TYPES = {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
PLAIN_TEXT_TYPES = {"text/plain", "text/markdown", "text/csv"}
EXTRACTABLE_TYPES = PDF_TYPES | DOCX_TYPES | PLAIN_TEXT_TYPES
MAX_CONTENT_LENGTH = 1_000_000  # 1MB text limit


def extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    import pdfplumber

    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_docx_text(content: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def extract_plain_text(content: bytes) -> str:
    """Extract text from plain text bytes with encoding detection."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return content.decode("utf-8", errors="replace")


@celery_app.task(
    name="app.tasks.extraction.extract_document_text",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=300,
)
def extract_document_text(self, document_id: str, document_version_id: str):
    """Extract text from a document version and update the search index."""
    asyncio.run(_extract_text_async(document_id, document_version_id))


async def _extract_text_async(document_id: str, document_version_id: str):
    """Async implementation of text extraction and search vector update."""
    from sqlalchemy import func, select, update

    from app.core.database import create_task_session_factory
    from app.core.minio_client import download_object
    from app.models.document import Document, DocumentVersion
    from app.services.audit_service import create_audit_record

    doc_id = uuid.UUID(document_id)
    ver_id = uuid.UUID(document_version_id)

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        # Load version to get content_type and minio key
        result = await session.execute(
            select(DocumentVersion).where(DocumentVersion.id == ver_id)
        )
        version = result.scalar_one_or_none()
        if version is None:
            logger.error("DocumentVersion %s not found", document_version_id)
            return

        content_type = version.content_type or "application/octet-stream"

        # If not extractable, mark as not_applicable
        if content_type not in EXTRACTABLE_TYPES:
            await session.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(extraction_status="not_applicable")
            )
            await session.commit()
            logger.info(
                "Document %s: content type %s not extractable, marked not_applicable",
                document_id,
                content_type,
            )
            return

        try:
            # Download file from MinIO
            file_content = await download_object(version.minio_object_key)

            # Extract text based on content type
            if content_type in PDF_TYPES:
                extracted_text = extract_pdf_text(file_content)
            elif content_type in DOCX_TYPES:
                extracted_text = extract_docx_text(file_content)
            else:
                extracted_text = extract_plain_text(file_content)

            # Truncate to max length
            if len(extracted_text) > MAX_CONTENT_LENGTH:
                extracted_text = extracted_text[:MAX_CONTENT_LENGTH]

            # Update fulltext_content on the version
            version.fulltext_content = extracted_text
            await session.flush()

            # Update search_vector with weighted tsvector on the document
            search_vector = (
                func.setweight(
                    func.to_tsvector("english", func.coalesce(Document.title, "")), "A"
                )
                + func.setweight(
                    func.to_tsvector("english", func.coalesce(Document.author, "")), "B"
                )
                + func.setweight(
                    func.to_tsvector("english", func.coalesce(extracted_text, "")), "C"
                )
            )

            await session.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(search_vector=search_vector, extraction_status="completed")
            )
            await session.commit()

            logger.info(
                "Document %s: extracted %d chars, search index updated",
                document_id,
                len(extracted_text),
            )

        except Exception as exc:
            await session.rollback()

            # Mark as failed
            async with session_factory() as err_session:
                await err_session.execute(
                    update(Document)
                    .where(Document.id == doc_id)
                    .values(extraction_status="failed")
                )
                await create_audit_record(
                    err_session,
                    entity_type="document",
                    entity_id=str(doc_id),
                    action="extraction_failed",
                    user_id=None,
                    details=str(exc)[:2000],
                )
                await err_session.commit()

            logger.error(
                "Document %s extraction failed: %s", document_id, exc
            )


@celery_app.task(name="app.tasks.extraction.backfill_search_index")
def backfill_search_index():
    """Find all documents without a search_vector and dispatch extraction tasks."""
    asyncio.run(_backfill_async())


async def _backfill_async():
    """Async implementation of backfill."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.core.database import create_task_session_factory
    from app.models.document import Document

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Document)
            .options(selectinload(Document.versions))
            .where(
                Document.search_vector.is_(None),
                Document.is_deleted == False,  # noqa: E712
            )
        )
        documents = result.scalars().all()

        dispatched = 0
        for doc in documents:
            if not doc.versions:
                continue
            # Get latest version (highest major, then minor)
            latest = sorted(
                doc.versions,
                key=lambda v: (v.major_version, v.minor_version),
                reverse=True,
            )[0]
            extract_document_text.delay(str(doc.id), str(latest.id))
            dispatched += 1

        logger.info("Backfill: dispatched %d extraction tasks", dispatched)
