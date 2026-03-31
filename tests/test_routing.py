"""Integration tests for conditional routing modes (EXEC-08, EXEC-09, EXEC-10).

Tests three routing types: performer-chosen, conditional (expression-based),
and broadcast. Each test creates a full template inline via HTTP, installs it,
starts a workflow, and verifies the routing outcome.
"""
import pytest
from httpx import AsyncClient

from app.models.user import User


# ---------------------------------------------------------------------------
# Helper: create a routing template with configurable routing_type
# ---------------------------------------------------------------------------


async def _create_routing_template(
    client: AsyncClient,
    headers: dict,
    admin_user_id: str,
    routing_type: str,
    *,
    add_conditions: bool = False,
    add_variable: bool = False,
) -> dict:
    """Create and install a template: Start -> Manual(routing_type) -> EndA / EndB.

    Returns dict with template_id, manual_id, end_a_id, end_b_id, flow_a_id, flow_b_id.
    """
    # Create template
    resp = await client.post(
        "/api/v1/templates/",
        json={"name": f"{routing_type.title()} Routing Test", "description": "Routing test"},
        headers=headers,
    )
    assert resp.status_code == 201, f"Create template failed: {resp.json()}"
    template_id = resp.json()["data"]["id"]

    # Start activity
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "Start", "activity_type": "start"},
        headers=headers,
    )
    start_id = resp.json()["data"]["id"]

    # Manual activity with routing_type
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Decision",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": admin_user_id,
            "routing_type": routing_type,
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Create Decision activity failed: {resp.json()}"
    manual_id = resp.json()["data"]["id"]

    # End activity A
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End A", "activity_type": "end"},
        headers=headers,
    )
    end_a_id = resp.json()["data"]["id"]

    # End activity B
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End B", "activity_type": "end"},
        headers=headers,
    )
    end_b_id = resp.json()["data"]["id"]

    # Flows: Start -> Decision
    await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": manual_id},
        headers=headers,
    )

    # Flow A: Decision -> End A
    flow_a_payload: dict = {
        "source_activity_id": manual_id,
        "target_activity_id": end_a_id,
        "display_label": "path_a",
    }
    if add_conditions:
        flow_a_payload["condition_expression"] = "approved == True"
    resp = await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json=flow_a_payload,
        headers=headers,
    )
    flow_a_id = resp.json()["data"]["id"]

    # Flow B: Decision -> End B
    flow_b_payload: dict = {
        "source_activity_id": manual_id,
        "target_activity_id": end_b_id,
        "display_label": "path_b",
    }
    if add_conditions:
        flow_b_payload["condition_expression"] = "approved == False"
    resp = await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json=flow_b_payload,
        headers=headers,
    )
    flow_b_id = resp.json()["data"]["id"]

    # Optionally add a variable
    if add_variable:
        await client.post(
            f"/api/v1/templates/{template_id}/variables",
            json={"name": "approved", "variable_type": "boolean", "default_bool_value": True},
            headers=headers,
        )

    # Validate and install
    resp = await client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    assert resp.status_code == 200, f"Validate failed: {resp.json()}"
    resp = await client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )
    assert resp.status_code == 200, f"Install failed: {resp.json()}"

    return {
        "template_id": template_id,
        "start_id": start_id,
        "manual_id": manual_id,
        "end_a_id": end_a_id,
        "end_b_id": end_b_id,
        "flow_a_id": flow_a_id,
        "flow_b_id": flow_b_id,
    }


# ---------------------------------------------------------------------------
# EXEC-08: Performer-chosen routing
# ---------------------------------------------------------------------------


async def test_performer_chosen_routing(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """EXEC-08: Performer-chosen routing fires only the selected path."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_routing_template(
        async_client, headers, str(admin_user.id), "performer_chosen"
    )

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": tmpl["template_id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # Get available work item
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    wi_id = available[0]["id"]

    # Complete with selected_path="path_a"
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_id}/complete",
        json={"selected_path": "path_a"},
        headers=headers,
    )
    assert resp.status_code == 200, f"Complete failed: {resp.json()}"

    # Verify workflow finished (End A should have completed)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    assert resp.json()["data"]["state"] == "finished"


async def test_performer_chosen_missing_path_errors(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """EXEC-08 negative: completing performer-chosen activity without selected_path returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_routing_template(
        async_client, headers, str(admin_user.id), "performer_chosen"
    )

    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": tmpl["template_id"]},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    wi_id = available[0]["id"]

    # Complete without selected_path -> should fail
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "selected_path" in resp.json()["detail"].lower()


async def test_performer_chosen_invalid_path_errors(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """EXEC-08 negative: completing with invalid selected_path returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_routing_template(
        async_client, headers, str(admin_user.id), "performer_chosen"
    )

    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": tmpl["template_id"]},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    wi_id = available[0]["id"]

    # Complete with nonexistent path
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_id}/complete",
        json={"selected_path": "nonexistent"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "No flow with label" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# EXEC-09: Conditional routing (expression-based)
# ---------------------------------------------------------------------------


async def test_conditional_routing(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """EXEC-09: Conditional routing evaluates expressions to determine path."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_routing_template(
        async_client,
        headers,
        str(admin_user.id),
        "conditional",
        add_conditions=True,
        add_variable=True,
    )

    # Start workflow -- approved defaults to True, so path_a (approved == True) fires
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": tmpl["template_id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # Get work item and complete
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    wi_id = available[0]["id"]

    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Workflow should finish (End A completed, End B never activated)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    assert resp.json()["data"]["state"] == "finished"


# ---------------------------------------------------------------------------
# EXEC-10: Broadcast routing (all flows fire)
# ---------------------------------------------------------------------------


async def test_broadcast_routing(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """EXEC-10: Broadcast routing fires all outgoing flows unconditionally."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_routing_template(
        async_client, headers, str(admin_user.id), "broadcast"
    )

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": tmpl["template_id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # Get work item and complete
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    wi_id = available[0]["id"]

    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Workflow should finish -- both End A and End B completed
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    data = resp.json()["data"]
    assert data["state"] == "finished"
    # Both end activities should be in complete state
    complete_activities = [a for a in data["activity_instances"] if a["state"] == "complete"]
    # Should have: Start (auto-complete) + Decision (completed) + End A + End B = 4
    assert len(complete_activities) >= 4, (
        f"Expected at least 4 complete activities (start+decision+2 ends), got {len(complete_activities)}"
    )
