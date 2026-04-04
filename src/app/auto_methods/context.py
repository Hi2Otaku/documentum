"""ActivityContext for auto method execution.

Provides read/write access to process variables, documents, and
the database session for auto methods to interact with workflow state.
"""
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import ActivityInstance, ActivityTemplate, ProcessVariable, WorkflowInstance


@dataclass
class ActivityContext:
    """Context passed to every auto method during execution.

    Attributes:
        db: Async database session for queries and updates.
        workflow_instance: The running workflow instance.
        activity_instance: The current activity instance being executed.
        activity_template: The template defining this activity.
        variables: Snapshot of process variables (name -> resolved value).
        document_ids: Document IDs from workflow packages.
        user_id: The user identity for this execution (default "system").
    """
    db: AsyncSession
    workflow_instance: WorkflowInstance
    activity_instance: ActivityInstance
    activity_template: ActivityTemplate
    variables: dict[str, Any] = field(default_factory=dict)
    document_ids: list[uuid.UUID] = field(default_factory=list)
    user_id: str = "system"

    async def get_variable(self, name: str) -> Any:
        """Read a process variable by name from the in-memory snapshot."""
        return self.variables.get(name)

    async def set_variable(self, name: str, value: Any) -> None:
        """Update a process variable in memory and persist to the database.

        Queries the ProcessVariable row by workflow_instance_id and name,
        then sets the appropriate typed column based on variable_type.
        """
        # Update in-memory snapshot
        self.variables[name] = value

        # Persist to database
        result = await self.db.execute(
            select(ProcessVariable).where(
                ProcessVariable.workflow_instance_id == self.workflow_instance.id,
                ProcessVariable.name == name,
                ProcessVariable.is_deleted == False,  # noqa: E712
            )
        )
        pv = result.scalar_one_or_none()

        if pv is None:
            # Create new variable with string type as default
            pv = ProcessVariable(
                workflow_instance_id=self.workflow_instance.id,
                name=name,
                variable_type="string",
                string_value=str(value) if value is not None else None,
            )
            self.db.add(pv)
        else:
            # Set value based on variable_type
            _set_variable_value(pv, value)

        await self.db.flush()


def _set_variable_value(pv: ProcessVariable, value: Any) -> None:
    """Set the appropriate typed column on a ProcessVariable based on its variable_type."""
    if pv.variable_type == "string":
        pv.string_value = str(value) if value is not None else None
    elif pv.variable_type == "int":
        pv.int_value = int(value) if value is not None else None
    elif pv.variable_type == "bool":
        pv.bool_value = bool(value) if value is not None else None
    elif pv.variable_type == "date":
        pv.date_value = value
    else:
        # Fallback: store as string
        pv.string_value = str(value) if value is not None else None
