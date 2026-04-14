import uuid

from pydantic import BaseModel


class SearchResultResponse(BaseModel):
    id: uuid.UUID
    title: str
    author: str | None = None
    filename: str
    content_type: str
    lifecycle_state: str | None = None
    extraction_status: str
    document_type_name: str | None = None
    headline: str | None = None
    rank: float = 0.0

    model_config = {"from_attributes": True}
