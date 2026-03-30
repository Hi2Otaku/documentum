import uuid

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import ActivityType, FlowType, ProcessState, WorkflowState, WorkItemState


class ProcessTemplate(BaseModel):
    __tablename__ = "process_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    state: Mapped[ProcessState] = mapped_column(
        Enum(ProcessState, name="processstate"),
        default=ProcessState.DRAFT,
        nullable=False,
    )
    is_installed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    installed_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)

    activity_templates: Mapped[list["ActivityTemplate"]] = relationship(back_populates="process_template")


class ActivityTemplate(BaseModel):
    __tablename__ = "activity_templates"

    process_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("process_templates.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activitytype"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    performer_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    performer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(20), default="or_join", nullable=False)
    position_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_y: Mapped[float | None] = mapped_column(Float, nullable=True)

    process_template: Mapped["ProcessTemplate"] = relationship(back_populates="activity_templates")


class FlowTemplate(BaseModel):
    __tablename__ = "flow_templates"

    process_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("process_templates.id"), nullable=False
    )
    source_activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("activity_templates.id"), nullable=False
    )
    target_activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("activity_templates.id"), nullable=False
    )
    flow_type: Mapped[FlowType] = mapped_column(
        Enum(FlowType, name="flowtype"), default=FlowType.NORMAL, nullable=False
    )
    condition_expression: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkflowInstance(BaseModel):
    __tablename__ = "workflow_instances"

    process_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("process_templates.id"), nullable=False
    )
    state: Mapped[WorkflowState] = mapped_column(
        Enum(WorkflowState, name="workflowstate"), default=WorkflowState.DORMANT, nullable=False
    )
    started_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)
    supervisor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=True
    )


class ActivityInstance(BaseModel):
    __tablename__ = "activity_instances"

    workflow_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("workflow_instances.id"), nullable=False
    )
    activity_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("activity_templates.id"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(50), default="dormant", nullable=False)
    started_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkItem(BaseModel):
    __tablename__ = "work_items"

    activity_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("activity_instances.id"), nullable=False
    )
    performer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=True
    )
    state: Mapped[WorkItemState] = mapped_column(
        Enum(WorkItemState, name="workitemstate"), default=WorkItemState.AVAILABLE, nullable=False
    )
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    completed_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcessVariable(BaseModel):
    __tablename__ = "process_variables"

    process_template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("process_templates.id"), nullable=True
    )
    workflow_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("workflow_instances.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    variable_type: Mapped[str] = mapped_column(String(20), nullable=False)
    string_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    int_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bool_value: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    date_value: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowPackage(BaseModel):
    __tablename__ = "workflow_packages"

    workflow_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("workflow_instances.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    package_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activity_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("activity_instances.id"), nullable=True
    )
