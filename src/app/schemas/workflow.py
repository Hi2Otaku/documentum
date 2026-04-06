import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import ActivityState, WorkflowState, WorkItemState


class WorkflowStartRequest(BaseModel):
    template_id: uuid.UUID
    document_ids: list[uuid.UUID] = []
    performer_overrides: dict[str, str] = {}  # activity_template_id str -> user_id str
    initial_variables: dict[str, Any] = {}
    alias_set_id: uuid.UUID | None = None


class CompleteWorkItemRequest(BaseModel):
    output_variables: dict[str, Any] = {}
    selected_path: str | None = None
    next_performer_id: str | None = None


class UpdateVariableRequest(BaseModel):
    value: Any


class ActivityInstanceResponse(BaseModel):
    id: uuid.UUID
    workflow_instance_id: uuid.UUID
    activity_template_id: uuid.UUID
    state: ActivityState
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WorkItemResponse(BaseModel):
    id: uuid.UUID
    activity_instance_id: uuid.UUID
    performer_id: uuid.UUID | None = None
    state: WorkItemState
    instructions: str | None = None
    due_date: datetime | None = None
    priority: int
    completed_at: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProcessVariableResponse(BaseModel):
    id: uuid.UUID
    name: str
    variable_type: str
    string_value: str | None = None
    int_value: int | None = None
    bool_value: bool | None = None
    date_value: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class WorkflowInstanceResponse(BaseModel):
    id: uuid.UUID
    process_template_id: uuid.UUID
    state: WorkflowState
    started_at: datetime | None = None
    completed_at: datetime | None = None
    supervisor_id: uuid.UUID | None = None
    parent_workflow_id: uuid.UUID | None = None
    nesting_depth: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AutoActivityLogResponse(BaseModel):
    id: uuid.UUID
    activity_instance_id: uuid.UUID
    method_name: str
    attempt_number: int
    status: str
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class ActivityRetryResponse(BaseModel):
    activity_instance_id: uuid.UUID
    status: str  # "requeued" or "skipped"
    message: str


class WorkflowActionResponse(BaseModel):
    id: uuid.UUID
    state: WorkflowState
    message: str
    model_config = ConfigDict(from_attributes=True)


class WorkflowAdminListResponse(BaseModel):
    id: uuid.UUID
    process_template_id: uuid.UUID
    state: WorkflowState
    started_at: datetime | None = None
    completed_at: datetime | None = None
    supervisor_id: uuid.UUID | None = None
    parent_workflow_id: uuid.UUID | None = None
    nesting_depth: int = 0
    template_name: str | None = None
    started_by_username: str | None = None
    active_activity_name: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)



class WorkflowDetailResponse(BaseModel):
    id: uuid.UUID
    process_template_id: uuid.UUID
    state: WorkflowState
    started_at: datetime | None = None
    completed_at: datetime | None = None
    supervisor_id: uuid.UUID | None = None
    parent_workflow_id: uuid.UUID | None = None
    nesting_depth: int = 0
    activity_instances: list[ActivityInstanceResponse] = []
    work_items: list[WorkItemResponse] = []
    process_variables: list[ProcessVariableResponse] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
