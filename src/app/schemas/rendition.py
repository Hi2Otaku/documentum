import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RenditionResponse(BaseModel):
    id: uuid.UUID
    document_version_id: uuid.UUID
    rendition_type: str
    status: str
    minio_object_key: str | None
    content_type: str | None
    content_size: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
