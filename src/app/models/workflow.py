import uuid

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import ActivityState, ActivityType, FlowType, ProcessState, TriggerType, WorkflowState, WorkItemState

# Re-export for convenient imports
__all__ = [
    "AliasSet", "AliasMapping",
    "ProcessTemplate", "ActivityTemplate", "FlowTemplate",
    "WorkflowInstance", "ActivityInstance", "WorkItem", "WorkItemComment",
    "ProcessVariable", "WorkflowPackage", "ExecutionToken",
]


class AliasSet(BaseModel):
    __tablename__ = "alias_sets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    mappings: Mapped[list["AliasMapping"]] = relationship(
        back_populates="alias_set", cascade="all, delete-orphan"
    )


class AliasMapping(BaseModel):
    __tablename__ = "alias_mappings"

    alias_set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("alias_sets.id"), nullable=False
    )
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)

    alias_set: Mapped["AliasSet"] = relationship(back_populates="mappings")


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
    alias_set_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("alias_sets.id"), nullable=True
    )

    activity_templates: Mapped[list["ActivityTemplate"]] = relationship(back_populates="process_template")
    flow_templates: Mapped[list["FlowTemplate"]] = relationship(back_populates="process_template")
    process_variables: Mapped[list["ProcessVariable"]] = relationship(back_populates="process_template")


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
    trigger_type: Mapped[TriggerType] = mapped_column(
        Enum(TriggerType, name="triggertype"),
        default=TriggerType.OR_JOIN,
        nullable=False,
    )
    method_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    routing_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default="conditional")
    performer_list: Mapped[dict | None] = mapped_column(JSON, nullable=True)

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
    display_label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    process_template: Mapped["ProcessTemplate"] = relationship(back_populates="flow_templates")
    source_activity: Mapped["ActivityTemplate"] = relationship(foreign_keys=[source_activity_id])
    target_activity: Mapped["ActivityTemplate"] = relationship(foreign_keys=[target_activity_id])


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
    alias_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    process_template: Mapped["ProcessTemplate"] = relationship(foreign_keys=[process_template_id])
    activity_instances: Mapped[list["ActivityInstance"]] = relationship(back_populates="workflow_instance", foreign_keys="[ActivityInstance.workflow_instance_id]")
    work_items: Mapped[list["WorkItem"]] = relationship(
        primaryjoin="WorkflowInstance.id == ActivityInstance.workflow_instance_id",
        secondary="activity_instances",
        secondaryjoin="ActivityInstance.id == WorkItem.activity_instance_id",
        viewonly=True,
    )
    process_variables: Mapped[list["ProcessVariable"]] = relationship(back_populates="workflow_instance", foreign_keys="[ProcessVariable.workflow_instance_id]")
    workflow_packages: Mapped[list["WorkflowPackage"]] = relationship(back_populates="workflow_instance")


class ActivityInstance(BaseModel):
    __tablename__ = "activity_instances"

    workflow_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("workflow_instances.id"), nullable=False
    )
    activity_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("activity_templates.id"), nullable=False
    )
    state: Mapped[ActivityState] = mapped_column(
        Enum(ActivityState, name="activitystate"),
        default=ActivityState.DORMANT,
        nullable=False,
    )
    started_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_performer_index: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)

    workflow_instance: Mapped["WorkflowInstance"] = relationship(back_populates="activity_instances", foreign_keys=[workflow_instance_id])
    activity_template: Mapped["ActivityTemplate"] = relationship(foreign_keys=[activity_template_id])
    work_items: Mapped[list["WorkItem"]] = relationship(back_populates="activity_instance")


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

    activity_instance: Mapped["ActivityInstance"] = relationship(back_populates="work_items", foreign_keys=[activity_instance_id])
    workflow_instance: Mapped["WorkflowInstance"] = relationship(
        primaryjoin="WorkItem.activity_instance_id == ActivityInstance.id",
        secondary="activity_instances",
        secondaryjoin="ActivityInstance.workflow_instance_id == WorkflowInstance.id",
        viewonly=True,
    )
    comments: Mapped[list["WorkItemComment"]] = relationship(back_populates="work_item")


class WorkItemComment(BaseModel):
    __tablename__ = "work_item_comments"

    work_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("work_items.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    work_item: Mapped["WorkItem"] = relationship(back_populates="comments")


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

    process_template: Mapped["ProcessTemplate"] = relationship(back_populates="process_variables")
    workflow_instance: Mapped["WorkflowInstance | None"] = relationship(back_populates="process_variables", foreign_keys=[workflow_instance_id])


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

    workflow_instance: Mapped["WorkflowInstance"] = relationship(back_populates="workflow_packages", foreign_keys=[workflow_instance_id])


class ExecutionToken(BaseModel):
    __tablename__ = "execution_tokens"

    workflow_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("workflow_instances.id"), nullable=False, index=True
    )
    flow_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("flow_templates.id"), nullable=False
    )
    source_activity_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("activity_instances.id"), nullable=False
    )
    target_activity_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("activity_templates.id"), nullable=False
    )
    is_consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
