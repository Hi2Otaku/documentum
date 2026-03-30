from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int


class EnvelopeResponse(BaseModel, Generic[T]):
    data: T | None = None
    meta: dict[str, Any] | PaginationMeta | None = None
    errors: list[dict[str, Any]] = []
