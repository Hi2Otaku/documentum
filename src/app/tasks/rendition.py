"""Celery tasks for document rendition generation.

Generates PDF renditions via LibreOffice headless and thumbnail images
via Pillow. Both tasks update the Rendition record status in the database
and upload results to MinIO.
"""
import asyncio
import io
import logging
import os
import shutil
import subprocess
import tempfile
import uuid

from app.celery_app import celery_app

logger = logging.getLogger(__name__)

# Content types that LibreOffice can convert to PDF
CONVERTIBLE_TYPES = {
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/rtf",
    "text/plain",
    "text/html",
    "text/csv",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
}

# Content types that are already PDF
PDF_TYPES = {"application/pdf"}

# Content types that Pillow can process for thumbnails
IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/webp",
}

THUMBNAIL_SIZE = (256, 256)


def _find_libreoffice() -> str | None:
    """Find LibreOffice binary on the system."""
    for cmd in ["libreoffice", "soffice"]:
        path = shutil.which(cmd)
        if path:
            return path
    # Common install locations on Windows/Linux
    common_paths = [
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
        "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
    ]
    for p in common_paths:
        if os.path.isfile(p):
            return p
    return None


@celery_app.task(
    name="app.tasks.rendition.generate_pdf_rendition",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=300,
)
def generate_pdf_rendition(self, rendition_id: str, document_version_id: str, document_id: str):
    """Generate a PDF rendition for a document version.

    If the source is already PDF, copies it directly. If convertible
    (Office formats), uses LibreOffice headless. Otherwise marks as failed.
    """
    asyncio.run(_generate_pdf_async(rendition_id, document_version_id, document_id))


async def _generate_pdf_async(rendition_id: str, document_version_id: str, document_id: str):
    """Async implementation of PDF rendition generation."""
    from sqlalchemy import select

    from app.core.database import create_task_session_factory
    from app.core.minio_client import download_object, upload_object
    from app.models.enums import RenditionStatus
    from app.models.rendition import Rendition

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        # Load rendition record
        result = await session.execute(
            select(Rendition).where(Rendition.id == uuid.UUID(rendition_id))
        )
        rendition = result.scalar_one_or_none()
        if rendition is None:
            logger.error("Rendition %s not found", rendition_id)
            return

        rendition.status = RenditionStatus.PROCESSING
        await session.commit()

        try:
            # Load the document version to get content type and MinIO key
            from app.models.document import DocumentVersion

            ver_result = await session.execute(
                select(DocumentVersion).where(
                    DocumentVersion.id == uuid.UUID(document_version_id)
                )
            )
            version = ver_result.scalar_one_or_none()
            if version is None:
                raise ValueError(f"DocumentVersion {document_version_id} not found")

            source_content = await download_object(version.minio_object_key)
            content_type = version.content_type or "application/octet-stream"

            pdf_bytes: bytes | None = None

            if content_type in PDF_TYPES:
                # Already PDF, just copy
                pdf_bytes = source_content
            elif content_type in CONVERTIBLE_TYPES:
                # Convert via LibreOffice headless
                lo_path = _find_libreoffice()
                if lo_path is None:
                    raise RuntimeError(
                        "LibreOffice not found on system. Install LibreOffice for PDF conversion."
                    )
                pdf_bytes = await _convert_with_libreoffice(
                    lo_path, source_content, version.filename
                )
            else:
                raise ValueError(
                    f"Cannot generate PDF rendition for content type: {content_type}"
                )

            # Upload PDF to MinIO
            object_key = f"renditions/{document_id}/{document_version_id}/rendition.pdf"
            await upload_object(object_key, pdf_bytes, "application/pdf")

            rendition.status = RenditionStatus.READY
            rendition.minio_object_key = object_key
            rendition.content_type = "application/pdf"
            rendition.content_size = len(pdf_bytes)
            rendition.error_message = None
            await session.commit()

            logger.info(
                "PDF rendition %s ready for version %s (%d bytes)",
                rendition_id,
                document_version_id,
                len(pdf_bytes),
            )

        except Exception as exc:
            rendition.status = RenditionStatus.FAILED
            rendition.error_message = str(exc)[:2000]
            await session.commit()
            logger.error(
                "PDF rendition %s failed for version %s: %s",
                rendition_id,
                document_version_id,
                exc,
            )


async def _convert_with_libreoffice(lo_path: str, content: bytes, filename: str) -> bytes:
    """Convert a document to PDF using LibreOffice headless in a temp directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, filename)
        with open(input_path, "wb") as f:
            f.write(content)

        proc = await asyncio.to_thread(
            subprocess.run,
            [
                lo_path,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                tmpdir,
                input_path,
            ],
            capture_output=True,
            timeout=120,
        )

        if proc.returncode != 0:
            raise RuntimeError(
                f"LibreOffice conversion failed (exit {proc.returncode}): "
                f"{proc.stderr.decode('utf-8', errors='replace')[:500]}"
            )

        # Find the output PDF
        base_name = os.path.splitext(filename)[0]
        pdf_path = os.path.join(tmpdir, f"{base_name}.pdf")
        if not os.path.isfile(pdf_path):
            raise RuntimeError(
                f"LibreOffice did not produce expected output file: {base_name}.pdf"
            )

        with open(pdf_path, "rb") as f:
            return f.read()


@celery_app.task(
    name="app.tasks.rendition.generate_thumbnail",
    bind=True,
    max_retries=2,
    default_retry_delay=15,
    soft_time_limit=120,
)
def generate_thumbnail(self, rendition_id: str, document_version_id: str, document_id: str):
    """Generate a thumbnail image for a document version.

    Uses Pillow for image files. For non-image files, marks as failed
    with a descriptive message.
    """
    asyncio.run(_generate_thumbnail_async(rendition_id, document_version_id, document_id))


async def _generate_thumbnail_async(rendition_id: str, document_version_id: str, document_id: str):
    """Async implementation of thumbnail generation."""
    from sqlalchemy import select

    from app.core.database import create_task_session_factory
    from app.core.minio_client import download_object, upload_object
    from app.models.enums import RenditionStatus
    from app.models.rendition import Rendition

    session_factory = create_task_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Rendition).where(Rendition.id == uuid.UUID(rendition_id))
        )
        rendition = result.scalar_one_or_none()
        if rendition is None:
            logger.error("Rendition %s not found", rendition_id)
            return

        rendition.status = RenditionStatus.PROCESSING
        await session.commit()

        try:
            from app.models.document import DocumentVersion

            ver_result = await session.execute(
                select(DocumentVersion).where(
                    DocumentVersion.id == uuid.UUID(document_version_id)
                )
            )
            version = ver_result.scalar_one_or_none()
            if version is None:
                raise ValueError(f"DocumentVersion {document_version_id} not found")

            content_type = version.content_type or "application/octet-stream"

            if content_type not in IMAGE_TYPES:
                raise ValueError(
                    f"Cannot generate thumbnail for content type: {content_type}. "
                    f"Only image types are supported."
                )

            source_content = await download_object(version.minio_object_key)
            thumbnail_bytes = await asyncio.to_thread(
                _create_thumbnail, source_content
            )

            object_key = f"renditions/{document_id}/{document_version_id}/thumbnail.png"
            await upload_object(object_key, thumbnail_bytes, "image/png")

            rendition.status = RenditionStatus.READY
            rendition.minio_object_key = object_key
            rendition.content_type = "image/png"
            rendition.content_size = len(thumbnail_bytes)
            rendition.error_message = None
            await session.commit()

            logger.info(
                "Thumbnail rendition %s ready for version %s (%d bytes)",
                rendition_id,
                document_version_id,
                len(thumbnail_bytes),
            )

        except Exception as exc:
            rendition.status = RenditionStatus.FAILED
            rendition.error_message = str(exc)[:2000]
            await session.commit()
            logger.error(
                "Thumbnail rendition %s failed for version %s: %s",
                rendition_id,
                document_version_id,
                exc,
            )


def _create_thumbnail(image_bytes: bytes) -> bytes:
    """Create a PNG thumbnail from image bytes using Pillow."""
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "Pillow is not installed. Install it with: pip install Pillow"
        )

    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail(THUMBNAIL_SIZE)

    # Convert to RGB if necessary (e.g., RGBA, palette mode)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()
