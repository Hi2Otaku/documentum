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
    alias_set_id: uuid.UUID | None = None


class ProcessTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    alias_set_id: uuid.UUID | None = None


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
    routing_type: str | None = None
    performer_list: list[str] | None = None
    sub_template_id: uuid.UUID | None = None
    variable_mapping: dict[str, str] | None = None
    event_type_filter: str | None = None
    event_filter_config: dict | None = None
    expected_duration_hours: float | None = None
    escalation_action: str | None = None
    warning_threshold_hours: float | None = None


class ActivityTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    performer_type: PerformerType | None = None
    performer_id: str | None = None
    trigger_type: TriggerType | None = None
    method_name: str | None = None
    position_x: float | None = None
    position_y: float | None = None
    routing_type: str | None = None
    performer_list: list[str] | None = None
    sub_template_id: uuid.UUID | None = None
    variable_mapping: dict[str, str] | None = None
    event_type_filter: str | None = None
    event_filter_config: dict | None = None
    expected_duration_hours: float | None = None
    escalation_action: str | None = None
    warning_threshold_hours: float | None = None


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
    routing_type: str | None = None
    performer_list: list | None = None
    sub_template_id: uuid.UUID | None = None
    variable_mapping: dict | None = None
    event_type_filter: str | None = None
    event_filter_config: dict | None = None
    expected_duration_hours: float | None = None
    escalation_action: str | None = None
    warning_threshold_hours: float | None = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


# --- FlowTemplate schemas ---


class FlowTemplateCreate(BaseModel):
    source_activity_id: uuid.UUID
    target_activity_id: uuid.UUID
    flow_type: FlowType = FlowType.NORMAL
    condition_expression: str | dict[str, Any] | None = None
    display_label: str | None = None

    @field_validator("condition_expression", mode="before")
    @classmethod
    def serialize_condition_expression(cls, v: Any) -> str | None:
        """Store condition expression as string. Accepts both AST expressions
        (e.g., 'amount > 1000') and JSON dict conditions (serialized to JSON string)."""
        if v is None:
            return None
        if isinstance(v, dict):
            return json.dumps(v)
        return str(v)


class FlowTemplateUpdate(BaseModel):
    flow_type: FlowType | None = None
    condition_expression: str | dict[str, Any] | None = None
    display_label: str | None = None

    @field_validator("condition_expression", mode="before")
    @classmethod
    def serialize_condition_expression(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, dict):
            return json.dumps(v)
        return str(v)


class FlowTemplateResponse(BaseModel):
    id: uuid.UUID
    process_template_id: uuid.UUID
    source_activity_id: uuid.UUID
    target_activity_id: uuid.UUID
    flow_type: FlowType
    condition_expression: str | dict[str, Any] | None
    display_label: str | None = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)

    @field_validator("condition_expression", mode="before")
    @classmethod
    def deserialize_condition_expression(cls, v: Any) -> str | dict[str, Any] | None:
        """Return condition expression as-is if string (AST expression),
        or deserialize from JSON string to dict if it looks like JSON."""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            return v
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
