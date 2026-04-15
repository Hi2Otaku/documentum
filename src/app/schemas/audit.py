import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    entity_type: str
    entity_id: str
    action: str
    user_id: str | None
    before_state: dict | None
    after_state: dict | None
    details: str | None
    content_hash: str | None = None
    chain_hash: str | None = None
    chain_sequence: int | None = None

    model_config = ConfigDict(from_attributes=True)
