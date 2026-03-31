import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import LifecycleState


class LifecycleTransitionRequest(BaseModel):
    target_state: LifecycleState


class LifecycleTransitionResponse(BaseModel):
    id: uuid.UUID
    lifecycle_state: str | None
    title: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
