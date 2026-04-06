"""Tests for sub-workflow functionality (Phase 18).

SUBWF-01: Sub-workflow activity type and template linkage
SUBWF-02: Child workflow spawning (Plan 02)
SUBWF-03: Parent resume on child completion (Plan 02)
SUBWF-04: Variable mapping parent-to-child
SUBWF-05: Depth limit enforcement
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActivityType
from app.models.workflow import ActivityTemplate, ProcessTemplate, WorkflowInstance


@pytest.mark.asyncio
async def test_create_sub_workflow_activity(db_session: AsyncSession):
    """SUBWF-01: Create an activity template with type SUB_WORKFLOW and sub_template_id."""
    # Create a parent process template
    parent_template = ProcessTemplate(
        id=uuid.uuid4(),
        name="Parent Process",
        description="Parent workflow template",
    )
    db_session.add(parent_template)

    # Create a child process template (the sub-workflow target)
    child_template = ProcessTemplate(
        id=uuid.uuid4(),
        name="Child Process",
        description="Child sub-workflow template",
    )
    db_session.add(child_template)
    await db_session.flush()

    # Create a SUB_WORKFLOW activity that references the child template
    activity = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=parent_template.id,
        name="Run Sub-Workflow",
        activity_type=ActivityType.SUB_WORKFLOW,
        sub_template_id=child_template.id,
        variable_mapping={"parent_var": "child_var", "amount": "sub_amount"},
    )
    db_session.add(activity)
    await db_session.commit()

    # Verify persistence
    await db_session.refresh(activity)
    assert activity.activity_type == ActivityType.SUB_WORKFLOW
    assert activity.sub_template_id == child_template.id
    assert activity.variable_mapping == {"parent_var": "child_var", "amount": "sub_amount"}


@pytest.mark.asyncio
async def test_workflow_instance_parent_fields(db_session: AsyncSession):
    """Verify WorkflowInstance parent fields default correctly."""
    template = ProcessTemplate(
        id=uuid.uuid4(),
        name="Test Template",
    )
    db_session.add(template)
    await db_session.flush()

    instance = WorkflowInstance(
        id=uuid.uuid4(),
        process_template_id=template.id,
    )
    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)

    assert instance.parent_workflow_id is None
    assert instance.parent_activity_instance_id is None
    assert instance.nesting_depth == 0


@pytest.mark.asyncio
@pytest.mark.skip(reason="Implemented in Plan 02")
async def test_sub_workflow_spawns_child():
    """SUBWF-02: When a SUB_WORKFLOW activity executes, it spawns a child workflow instance."""
    pass


@pytest.mark.asyncio
@pytest.mark.skip(reason="Implemented in Plan 02")
async def test_parent_resumes_on_child_complete():
    """SUBWF-03: Parent workflow resumes when child workflow reaches FINISHED state."""
    pass


@pytest.mark.asyncio
@pytest.mark.skip(reason="Implemented in Plan 02")
async def test_variable_mapping_parent_to_child():
    """SUBWF-04: Variables are mapped from parent to child on spawn and back on completion."""
    pass


@pytest.mark.asyncio
@pytest.mark.skip(reason="Implemented in Plan 02")
async def test_depth_limit_rejected():
    """SUBWF-05: Spawning a sub-workflow beyond max_sub_workflow_depth raises an error."""
    pass


@pytest.mark.asyncio
@pytest.mark.skip(reason="Implemented in Plan 02")
async def test_child_failure_propagates_to_parent():
    """When a child workflow fails, the parent activity transitions to ERROR state."""
    pass
