import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ActivityType, FlowType, PerformerType, ProcessState, TriggerType


# --- ProcessTemplate schemas ---


class ProcessTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProcessTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ProcessTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    version: int
    state: ProcessState
    is_installed: bool
    installed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


# --- ActivityTemplate schemas ---


class ActivityTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    activity_type: ActivityType
    description: str | None = None
    performer_type: PerformerType | None = None
    performer_id: str | None = None
    trigger_type: TriggerType = TriggerType.OR_JOIN
    method_name: str | None = None
    position_x: float | None = None
    position_y: float | None = None


class ActivityTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    performer_type: PerformerType | None = None
    performer_id: str | None = None
    trigger_type: TriggerType | None = None
    method_name: str | None = None
    position_x: float | None = None
    position_y: float | None = None


class ActivityTemplateResponse(BaseModel):
    id: uuid.UUID
    process_template_id: uuid.UUID
    name: str
    activity_type: ActivityType
    description: str | None
    performer_type: str | None
    performer_id: str | None
    trigger_type: TriggerType
    method_name: str | None
    position_x: float | None
    position_y: float | None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


# --- FlowTemplate schemas ---


class FlowTemplateCreate(BaseModel):
    source_activity_id: uuid.UUID
    target_activity_id: uuid.UUID
    flow_type: FlowType = FlowType.NORMAL
    condition_expression: dict[str, Any] | None = None


class FlowTemplateUpdate(BaseModel):
    flow_type: FlowType | None = None
    condition_expression: dict[str, Any] | None = None


class FlowTemplateResponse(BaseModel):
    id: uuid.UUID
    process_template_id: uuid.UUID
    source_activity_id: uuid.UUID
    target_activity_id: uuid.UUID
    flow_type: FlowType
    condition_expression: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)

    @field_validator("condition_expression", mode="before")
    @classmethod
    def deserialize_condition_expression(cls, v: Any) -> dict[str, Any] | None:
        if v is None:
            return None
        if isinstance(v, str):
            return json.loads(v)
        return v


# --- ProcessVariable schemas ---


class ProcessVariableCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    variable_type: str = Field(pattern=r"^(string|int|boolean|date)$")
    default_string_value: str | None = None
    default_int_value: int | None = None
    default_bool_value: bool | None = None
    default_date_value: datetime | None = None


class ProcessVariableUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    variable_type: str | None = Field(default=None, pattern=r"^(string|int|boolean|date)$")
    default_string_value: str | None = None
    default_int_value: int | None = None
    default_bool_value: bool | None = None
    default_date_value: datetime | None = None


class ProcessVariableResponse(BaseModel):
    id: uuid.UUID
    process_template_id: uuid.UUID | None
    workflow_instance_id: uuid.UUID | None
    name: str
    variable_type: str
    string_value: str | None
    int_value: int | None
    bool_value: bool | None
    date_value: datetime | None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


# --- Validation schemas ---


class ValidationErrorDetail(BaseModel):
    code: str
    message: str
    entity_type: str
    entity_id: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationErrorDetail] = []


# --- Detail response (nested) ---


class ProcessTemplateDetailResponse(ProcessTemplateResponse):
    """Full template with nested activities, flows, and variables."""

    activities: list[ActivityTemplateResponse] = []
    flows: list[FlowTemplateResponse] = []
    variables: list[ProcessVariableResponse] = []
