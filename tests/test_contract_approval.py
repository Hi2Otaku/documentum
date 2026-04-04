"""Integration tests for contract approval E2E workflow.

EXAMPLE-01: 7-step contract approval template with correct activity types
EXAMPLE-02: All routing types demonstrated (sequential, parallel, conditional, reject)
EXAMPLE-03: Full E2E execution producing FINISHED workflow with audit trail
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token, hash_password
from app.models.enums import (
    ActivityState,
    ActivityType,
    FlowType,
    WorkflowState,
    WorkItemState,
)
from app.models.user import User
from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    FlowTemplate,
    WorkflowInstance,
    WorkItem,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_users(db_session: AsyncSession) -> dict[str, User]:
    """Create 4 test users for contract approval workflow."""
    users = {}
    for uname in ["drafter", "lawyer", "accountant", "director"]:
        user = User(
            id=uuid.uuid4(),
            username=uname,
            hashed_password=hash_password(f"{uname}pass"),
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        users[uname] = user
    await db_session.commit()
    for u in users.values():
        await db_session.refresh(u)
    return users


@pytest.fixture
async def user_tokens(test_users: dict[str, User]) -> dict[str, str]:
    """Create JWT tokens for test users."""
    return {
        name: create_access_token({"sub": str(user.id), "username": user.username})
        for name, user in test_users.items()
    }


@pytest.fixture
async def contract_approval_template(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User,
    test_users: dict[str, User],
) -> dict:
    """Create the full 7-step contract approval template and install it.

    Returns dict with template_id, activity IDs (by name), and user IDs.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create template
    resp = await async_client.post(
        "/api/v1/templates/",
        json={
            "name": "Contract Approval",
            "description": "7-step contract approval E2E test",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    template_id = resp.json()["data"]["id"]

    # Add 8 activities
    activities: dict[str, str] = {}
    activity_defs = [
        {"name": "Initiate", "activity_type": "start"},
        {
            "name": "Draft Contract",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(test_users["drafter"].id),
        },
        {
            "name": "Legal Review",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(test_users["lawyer"].id),
        },
        {
            "name": "Financial Review",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(test_users["accountant"].id),
        },
        {
            "name": "Director Approval",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(test_users["director"].id),
            "routing_type": "performer_chosen",
            "trigger_type": "and_join",
        },
        {
            "name": "Digital Signing",
            "activity_type": "auto",
            "method_name": "send_email",
        },
        {
            "name": "Archival",
            "activity_type": "auto",
            "method_name": "change_lifecycle_state",
        },
        {"name": "End", "activity_type": "end"},
    ]
    for adef in activity_defs:
        resp = await async_client.post(
            f"/api/v1/templates/{template_id}/activities",
            json=adef,
            headers=headers,
        )
        assert resp.status_code == 201, f"Failed to create activity {adef['name']}: {resp.text}"
        activities[adef["name"]] = resp.json()["data"]["id"]

    # Add process variables
    for vdef in [
        {"name": "signed", "variable_type": "boolean", "bool_value": False},
        {"name": "approval_decision", "variable_type": "string", "string_value": ""},
    ]:
        resp = await async_client.post(
            f"/api/v1/templates/{template_id}/variables",
            json=vdef,
            headers=headers,
        )
        assert resp.status_code == 201

    # Add flows
    flow_defs = [
        # Sequential: Initiate -> Draft Contract
        (activities["Initiate"], activities["Draft Contract"], "normal", None),
        # Parallel split: Draft -> Legal + Financial
        (activities["Draft Contract"], activities["Legal Review"], "normal", None),
        (activities["Draft Contract"], activities["Financial Review"], "normal", None),
        # Parallel join: Legal + Financial -> Director Approval
        (activities["Legal Review"], activities["Director Approval"], "normal", None),
        (activities["Financial Review"], activities["Director Approval"], "normal", None),
        # Conditional: Director Approval -> Digital Signing (Approve)
        (activities["Director Approval"], activities["Digital Signing"], "normal", "Approve"),
        # Reject: Director Approval -> Draft Contract
        (activities["Director Approval"], activities["Draft Contract"], "reject", "Reject"),
        # Sequential: Digital Signing -> Archival -> End
        (activities["Digital Signing"], activities["Archival"], "normal", None),
        (activities["Archival"], activities["End"], "normal", None),
    ]
    for src, tgt, ftype, label in flow_defs:
        flow_data: dict = {
            "source_activity_id": src,
            "target_activity_id": tgt,
            "flow_type": ftype,
        }
        if label:
            flow_data["display_label"] = label
        resp = await async_client.post(
            f"/api/v1/templates/{template_id}/flows",
            json=flow_data,
            headers=headers,
        )
        assert resp.status_code == 201, f"Failed to create flow {src}->{tgt}: {resp.text}"

    # Validate and install
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    assert resp.status_code == 200
    validation = resp.json()["data"]
    assert validation["valid"], f"Template validation failed: {validation.get('errors', [])}"

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )
    assert resp.status_code == 200

    return {
        "template_id": template_id,
        "activities": activities,
        "users": {name: str(user.id) for name, user in test_users.items()},
    }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


async def _get_work_items_for_user(
    db: AsyncSession, user_id: str, workflow_id: str | None = None
) -> list[WorkItem]:
    """Get available work items for a user."""
    conditions = [
        WorkItem.performer_id == uuid.UUID(user_id),
        WorkItem.state == WorkItemState.AVAILABLE,
        WorkItem.is_deleted == False,  # noqa: E712
    ]
    if workflow_id:
        # Join through activity instance to filter by workflow
        stmt = (
            select(WorkItem)
            .join(ActivityInstance)
            .where(
                *conditions,
                ActivityInstance.workflow_instance_id == uuid.UUID(workflow_id),
            )
        )
    else:
        stmt = select(WorkItem).where(*conditions)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _complete_work_item_direct(
    db: AsyncSession,
    async_client: AsyncClient,
    admin_token: str,
    workflow_id: str,
    work_item_id: str,
    user_id: str,
    output_variables: dict | None = None,
    selected_path: str | None = None,
) -> None:
    """Complete a work item via the workflow API (engine_service direct route)."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    body: dict = {}
    if output_variables:
        body["output_variables"] = output_variables
    if selected_path:
        body["selected_path"] = selected_path
    resp = await async_client.post(
        f"/api/v1/workflows/{workflow_id}/work-items/{work_item_id}/complete",
        json=body,
        headers=headers,
    )
    assert resp.status_code == 200, f"Complete work item failed: {resp.text}"


async def _advance_auto_activity(
    db: AsyncSession,
    workflow_id: str,
    activity_template_id: str,
    user_id: str,
) -> None:
    """Manually advance an auto activity (simulates Workflow Agent).

    In production, Celery workers pick up auto activities.
    In tests, we directly call the engine service advancement.
    """
    from app.services import engine_service

    # Find the activity instance
    result = await db.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == uuid.UUID(workflow_id),
            ActivityInstance.activity_template_id == uuid.UUID(activity_template_id),
        )
    )
    ai = result.scalar_one()
    assert ai.state == ActivityState.ACTIVE, f"Auto activity not active: {ai.state}"

    # Load workflow and template for advancement
    wf_result = await db.execute(
        select(WorkflowInstance).where(WorkflowInstance.id == uuid.UUID(workflow_id))
    )
    workflow = wf_result.scalar_one()

    from app.models.workflow import ProcessTemplate, ProcessVariable
    template_result = await db.execute(
        select(ProcessTemplate)
        .options(
            selectinload(ProcessTemplate.activity_templates),
            selectinload(ProcessTemplate.flow_templates),
            selectinload(ProcessTemplate.process_variables),
        )
        .where(ProcessTemplate.id == workflow.process_template_id)
    )
    template = template_result.scalar_one()

    # Rebuild template_to_instance mapping
    ai_result = await db.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == uuid.UUID(workflow_id)
        )
    )
    all_instances = list(ai_result.scalars().all())
    template_to_instance = {inst.activity_template_id: inst for inst in all_instances}

    # Load current variables
    pv_result = await db.execute(
        select(ProcessVariable).where(
            ProcessVariable.workflow_instance_id == uuid.UUID(workflow_id),
            ProcessVariable.is_deleted == False,  # noqa: E712
        )
    )
    current_variables = list(pv_result.scalars().all())

    # Advance
    await engine_service._advance_from_activity(
        db,
        workflow,
        ai,
        template,
        template_to_instance,
        user_id,
        instance_variables=current_variables,
    )
    await db.flush()


# ---------------------------------------------------------------------------
# EXAMPLE-01: Contract approval template creation
# ---------------------------------------------------------------------------


async def test_contract_approval_template_creation(
    async_client: AsyncClient,
    admin_token: str,
    contract_approval_template: dict,
):
    """EXAMPLE-01: Verify 7-step contract approval template has correct structure.

    Template must have 8 activities: 1 start, 4 manual, 2 auto, 1 end.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id = contract_approval_template["template_id"]

    # Get template detail
    resp = await async_client.get(
        f"/api/v1/templates/{template_id}", headers=headers
    )
    assert resp.status_code == 200
    detail = resp.json()["data"]

    # Verify installed (active state)
    assert detail["state"] == "active"
    assert detail["is_installed"] is True

    # Verify 8 activities
    activities = detail["activities"]
    assert len(activities) == 8, f"Expected 8 activities, got {len(activities)}"

    # Count by type
    type_counts: dict[str, int] = {}
    for a in activities:
        atype = a["activity_type"]
        type_counts[atype] = type_counts.get(atype, 0) + 1

    assert type_counts.get("start", 0) == 1, f"Expected 1 start, got {type_counts}"
    assert type_counts.get("manual", 0) == 4, f"Expected 4 manual, got {type_counts}"
    assert type_counts.get("auto", 0) == 2, f"Expected 2 auto, got {type_counts}"
    assert type_counts.get("end", 0) == 1, f"Expected 1 end, got {type_counts}"

    # Verify activity names
    activity_names = {a["name"] for a in activities}
    expected_names = {
        "Initiate", "Draft Contract", "Legal Review", "Financial Review",
        "Director Approval", "Digital Signing", "Archival", "End",
    }
    assert activity_names == expected_names


# ---------------------------------------------------------------------------
# EXAMPLE-02: Routing types verification
# ---------------------------------------------------------------------------


async def test_contract_approval_routing_types(
    async_client: AsyncClient,
    admin_token: str,
    contract_approval_template: dict,
):
    """EXAMPLE-02: Verify all routing types are demonstrated.

    - Sequential: Initiate -> Draft Contract
    - Parallel split: Draft Contract -> Legal Review AND Financial Review
    - Parallel join: Legal + Financial -> Director Approval (AND_JOIN)
    - Conditional: Director Approval -> Digital Signing (performer_chosen with "Approve" label)
    - Reject: Director Approval -> Draft Contract (reject flow with "Reject" label)
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id = contract_approval_template["template_id"]
    activities = contract_approval_template["activities"]

    # Get template detail for flows
    resp = await async_client.get(
        f"/api/v1/templates/{template_id}", headers=headers
    )
    assert resp.status_code == 200
    detail = resp.json()["data"]
    flows = detail["flows"]

    # Count flow types
    normal_flows = [f for f in flows if f["flow_type"] == "normal"]
    reject_flows = [f for f in flows if f["flow_type"] == "reject"]
    assert len(normal_flows) == 8, f"Expected 8 normal flows, got {len(normal_flows)}"
    assert len(reject_flows) == 1, f"Expected 1 reject flow, got {len(reject_flows)}"

    # Verify parallel split: Draft Contract has 2 outgoing normal flows
    draft_outgoing = [
        f for f in normal_flows
        if f["source_activity_id"] == activities["Draft Contract"]
    ]
    assert len(draft_outgoing) == 2, f"Expected 2 outgoing from Draft, got {len(draft_outgoing)}"
    draft_targets = {f["target_activity_id"] for f in draft_outgoing}
    assert activities["Legal Review"] in draft_targets
    assert activities["Financial Review"] in draft_targets

    # Verify parallel join: Director Approval has 2 incoming normal flows
    director_incoming = [
        f for f in normal_flows
        if f["target_activity_id"] == activities["Director Approval"]
    ]
    assert len(director_incoming) == 2, f"Expected 2 incoming to Director, got {len(director_incoming)}"

    # Verify Director Approval has AND_JOIN trigger
    director_activity = None
    for a in detail["activities"]:
        if a["name"] == "Director Approval":
            director_activity = a
            break
    assert director_activity is not None
    assert director_activity.get("trigger_type") == "and_join"

    # Verify conditional/performer_chosen: Director -> Digital Signing with "Approve" label
    approve_flows = [
        f for f in normal_flows
        if f["source_activity_id"] == activities["Director Approval"]
        and f["target_activity_id"] == activities["Digital Signing"]
    ]
    assert len(approve_flows) == 1
    assert approve_flows[0].get("display_label") == "Approve"

    # Verify reject: Director Approval -> Draft Contract
    assert len(reject_flows) == 1
    assert reject_flows[0]["source_activity_id"] == activities["Director Approval"]
    assert reject_flows[0]["target_activity_id"] == activities["Draft Contract"]
    assert reject_flows[0].get("display_label") == "Reject"


# ---------------------------------------------------------------------------
# EXAMPLE-03: E2E execution
# ---------------------------------------------------------------------------


async def test_contract_approval_e2e_execution(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User,
    contract_approval_template: dict,
    db_session: AsyncSession,
):
    """EXAMPLE-03: Full E2E execution produces FINISHED workflow with audit trail.

    1. Start workflow
    2. Complete Draft Contract -> verify Legal Review + Financial Review both ACTIVE
    3. Complete Legal Review -> verify Director Approval NOT yet active
    4. Complete Financial Review -> verify Director Approval now ACTIVE
    5. Complete Director Approval with selected_path="Approve"
    6. Manually advance auto activities (Digital Signing, Archival)
    7. Verify workflow is FINISHED
    8. Verify audit trail entries exist
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    template_id = contract_approval_template["template_id"]
    activities = contract_approval_template["activities"]
    user_ids = contract_approval_template["users"]

    # 1. Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    assert resp.status_code == 201
    workflow_id = resp.json()["data"]["id"]
    assert resp.json()["data"]["state"] == "running"

    # After start: Initiate auto-completes, Draft Contract should be ACTIVE
    # Drafter should have a work item
    drafter_items = await _get_work_items_for_user(
        db_session, user_ids["drafter"], workflow_id
    )
    assert len(drafter_items) >= 1, "Drafter should have a work item after start"

    # 2. Complete Draft Contract
    await _complete_work_item_direct(
        db_session, async_client, admin_token, workflow_id,
        str(drafter_items[0].id), user_ids["drafter"],
    )

    # Verify parallel split: Legal Review AND Financial Review both ACTIVE
    legal_ai = await db_session.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == uuid.UUID(workflow_id),
            ActivityInstance.activity_template_id == uuid.UUID(activities["Legal Review"]),
        )
    )
    legal_instance = legal_ai.scalar_one()
    assert legal_instance.state == ActivityState.ACTIVE

    financial_ai = await db_session.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == uuid.UUID(workflow_id),
            ActivityInstance.activity_template_id == uuid.UUID(activities["Financial Review"]),
        )
    )
    financial_instance = financial_ai.scalar_one()
    assert financial_instance.state == ActivityState.ACTIVE

    # 3. Complete Legal Review (lawyer)
    lawyer_items = await _get_work_items_for_user(
        db_session, user_ids["lawyer"], workflow_id
    )
    assert len(lawyer_items) >= 1
    await _complete_work_item_direct(
        db_session, async_client, admin_token, workflow_id,
        str(lawyer_items[0].id), user_ids["lawyer"],
    )

    # Verify Director Approval NOT yet active (AND-join waiting for Financial Review)
    director_ai = await db_session.execute(
        select(ActivityInstance).where(
            ActivityInstance.workflow_instance_id == uuid.UUID(workflow_id),
            ActivityInstance.activity_template_id == uuid.UUID(activities["Director Approval"]),
        )
    )
    director_instance = director_ai.scalar_one()
    assert director_instance.state == ActivityState.DORMANT, \
        f"Director should be DORMANT (AND-join), got {director_instance.state}"

    # 4. Complete Financial Review (accountant)
    accountant_items = await _get_work_items_for_user(
        db_session, user_ids["accountant"], workflow_id
    )
    assert len(accountant_items) >= 1
    await _complete_work_item_direct(
        db_session, async_client, admin_token, workflow_id,
        str(accountant_items[0].id), user_ids["accountant"],
    )

    # Verify Director Approval is now ACTIVE (AND-join satisfied)
    await db_session.refresh(director_instance)
    assert director_instance.state == ActivityState.ACTIVE, \
        f"Director should be ACTIVE after both reviews, got {director_instance.state}"

    # 5. Complete Director Approval with Approve path
    director_items = await _get_work_items_for_user(
        db_session, user_ids["director"], workflow_id
    )
    assert len(director_items) >= 1
    await _complete_work_item_direct(
        db_session, async_client, admin_token, workflow_id,
        str(director_items[0].id), user_ids["director"],
        selected_path="Approve",
    )

    # 6. Manually advance auto activities (no Celery worker in tests)
    # Digital Signing
    await _advance_auto_activity(
        db_session, workflow_id, activities["Digital Signing"], str(admin_user.id)
    )
    # Archival
    await _advance_auto_activity(
        db_session, workflow_id, activities["Archival"], str(admin_user.id)
    )

    # 7. Verify workflow is FINISHED
    wf_result = await db_session.execute(
        select(WorkflowInstance).where(
            WorkflowInstance.id == uuid.UUID(workflow_id)
        )
    )
    workflow = wf_result.scalar_one()
    assert workflow.state == WorkflowState.FINISHED, \
        f"Expected FINISHED, got {workflow.state}"

    # 8. Verify audit trail
    resp = await async_client.get("/api/v1/audit", headers=headers)
    assert resp.status_code == 200
    audit_data = resp.json()["data"]
    # Should have at least 5 entries: workflow_started + 4 work_item_completed
    assert len(audit_data) >= 5, \
        f"Expected at least 5 audit entries, got {len(audit_data)}"
