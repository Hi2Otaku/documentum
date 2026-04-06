"""Pydantic schemas for domain events."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DomainEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
