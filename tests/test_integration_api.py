"""Integration tests for external system REST API access (INTG-02, INTG-03).

Verifies that existing REST endpoints work for external system integration:
- INTG-02: External systems can start workflows via POST /api/v1/workflows/
- INTG-03: External systems can complete/reject work items via inbox endpoints

All operations use JWT authentication, proving external systems can interact
with the workflow engine using standard REST API + token auth.
"""
import pytest
from httpx import AsyncClient

from app.models.user import User


# ---------------------------------------------------------------------------
# INTG-02: External system starts a workflow
# ---------------------------------------------------------------------------


async def test_external_system_starts_workflow(
    async_client: AsyncClient,
    admin_token: str,
    installed_template: dict,
):
    """INTG-02: External system authenticates with JWT and starts a workflow instance."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": installed_template["template_id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["state"] == "running"
    assert data["process_template_id"] == installed_template["template_id"]
    assert data["id"] is not None


async def test_external_system_starts_workflow_with_variables(
    async_client: AsyncClient,
    admin_token: str,
    admin_user,
):
    """INTG-02: External system starts workflow with initial_variables and documents.

    Creates a template with a process variable, installs it, then starts with
    initial_variables to override the default value.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create template with a process variable
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "External Vars Workflow", "description": "With variables"},
        headers=headers,
    )
    assert resp.status_code == 201
    template_id = resp.json()["data"]["id"]

    # Add activities
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "Start", "activity_type": "start"},
        headers=headers,
    )
    start_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Review",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    manual_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    # Flows
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": manual_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": manual_id, "target_activity_id": end_id},
        headers=headers,
    )

    # Add a process variable
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/variables",
        json={"name": "contract_id", "variable_type": "string", "default_value": "NONE"},
        headers=headers,
    )
    assert resp.status_code == 201

    # Validate and install
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    assert resp.status_code == 200
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )
    assert resp.status_code == 200

    # External system starts workflow with initial_variables
    resp = await async_client.post(
        "/api/v1/workflows",
        json={
            "template_id": template_id,
            "initial_variables": {"contract_id": "EXT-2026-001"},
        },
        headers=headers,
    )
    assert resp.status_code == 201
    workflow_id = resp.json()["data"]["id"]

    # Verify variable was overridden
    resp = await async_client.get(
        f"/api/v1/workflows/{workflow_id}/variables",
        headers=headers,
    )
    assert resp.status_code == 200
    variables = resp.json()["data"]
    contract_var = next((v for v in variables if v["name"] == "contract_id"), None)
    assert contract_var is not None, "contract_id variable should exist"
    assert contract_var["string_value"] == "EXT-2026-001"


# ---------------------------------------------------------------------------
# INTG-03: External system completes/rejects work items
# ---------------------------------------------------------------------------


async def test_external_system_completes_work_item(
    async_client: AsyncClient,
    admin_token: str,
    installed_template: dict,
):
    """INTG-03: External system completes a work item, advancing the workflow."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Start workflow (START -> MANUAL -> END)
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": installed_template["template_id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    workflow_id = resp.json()["data"]["id"]

    # Get work item from inbox
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) >= 1, "Expected at least one work item in inbox"
    work_item_id = items[0]["id"]

    # Acquire the work item
    resp = await async_client.post(
        f"/api/v1/inbox/{work_item_id}/acquire",
        headers=headers,
    )
    assert resp.status_code == 200

    # Complete the work item via REST API (simulating external system)
    resp = await async_client.post(
        f"/api/v1/inbox/{work_item_id}/complete",
        json={"output_variables": {"external_approval": "approved"}},
        headers=headers,
    )
    assert resp.status_code == 200

    # Verify workflow advanced to FINISHED (MANUAL -> END)
    resp = await async_client.get(
        f"/api/v1/workflows/{workflow_id}", headers=headers
    )
    assert resp.status_code == 200
    wf_data = resp.json()["data"]
    assert wf_data["state"] == "finished", (
        f"Expected workflow to be finished after completing the only manual activity, "
        f"got {wf_data['state']}"
    )


async def test_external_system_rejects_work_item(
    async_client: AsyncClient,
    admin_token: str,
    installed_template: dict,
):
    """INTG-03: External system rejects a work item via REST API.

    Uses the installed_template (START -> MANUAL -> END) which has no reject flow.
    Verifies that the reject endpoint returns an appropriate error when no reject
    flow is configured, confirming the API handles rejection requests correctly.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": installed_template["template_id"]},
        headers=headers,
    )
    assert resp.status_code == 201

    # Get work item from inbox
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) >= 1
    work_item_id = items[0]["id"]

    # Acquire the work item first
    resp = await async_client.post(
        f"/api/v1/inbox/{work_item_id}/acquire",
        headers=headers,
    )
    assert resp.status_code == 200

    # Reject -- should fail with 400 because no reject flow is defined (D-03)
    # This still proves the endpoint is accessible to external systems via REST API
    resp = await async_client.post(
        f"/api/v1/inbox/{work_item_id}/reject",
        json={"reason": "External system rejected this item"},
        headers=headers,
    )
    # The API correctly rejects when no reject flow exists
    assert resp.status_code == 400
    assert "reject" in resp.json()["detail"].lower() or "No reject flow" in resp.json()["detail"]
