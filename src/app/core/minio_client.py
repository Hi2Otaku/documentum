import asyncio
import io
import logging

from minio import Minio

from app.core.config import settings

logger = logging.getLogger(__name__)

minio_client = Minio(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)

DOCUMENTS_BUCKET = "documents"


async def ensure_documents_bucket() -> None:
    """Check if the documents bucket exists, create if not."""

    def _ensure() -> None:
        if not minio_client.bucket_exists(DOCUMENTS_BUCKET):
            minio_client.make_bucket(DOCUMENTS_BUCKET)
            logger.info("Created MinIO bucket '%s'", DOCUMENTS_BUCKET)
        else:
            logger.info("MinIO bucket '%s' already exists", DOCUMENTS_BUCKET)

    await asyncio.to_thread(_ensure)


async def upload_object(object_name: str, data: bytes, content_type: str) -> str:
    """Upload bytes to MinIO and return the object name."""

    def _upload() -> str:
        minio_client.put_object(
            DOCUMENTS_BUCKET,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return object_name

    return await asyncio.to_thread(_upload)


async def download_object(object_name: str) -> bytes:
    """Download an object from MinIO and return its bytes."""

    def _download() -> bytes:
        response = None
        try:
            response = minio_client.get_object(DOCUMENTS_BUCKET, object_name)
            return response.read()
        finally:
            if response is not None:
                response.close()
                response.release_conn()

    return await asyncio.to_thread(_download)


async def delete_object(object_name: str) -> None:
    """Delete an object from MinIO."""

    def _delete() -> None:
        minio_client.remove_object(DOCUMENTS_BUCKET, object_name)

    await asyncio.to_thread(_delete)
