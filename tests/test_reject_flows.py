"""Integration tests for reject flow traversal (EXEC-11).

Tests that rejection follows REJECT flow edges, resets target activities,
creates new work items, and preserves process variables.
"""
import pytest
from httpx import AsyncClient

from app.models.user import User


# ---------------------------------------------------------------------------
# Helper: create a template with a reject flow
# ---------------------------------------------------------------------------


async def _create_reject_template(
    client: AsyncClient,
    headers: dict,
    performer_id: str,
) -> dict:
    """Create and install: Start -> Activity_A -> Activity_B -> End, with REJECT flow B -> A.

    Returns dict with template_id and activity IDs.
    """
    # Create template
    resp = await client.post(
        "/api/v1/templates/",
        json={"name": "Reject Flow Test", "description": "Reject flow test"},
        headers=headers,
    )
    assert resp.status_code == 201
    template_id = resp.json()["data"]["id"]

    # Start
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "Start", "activity_type": "start"},
        headers=headers,
    )
    start_id = resp.json()["data"]["id"]

    # Activity A (manual)
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Activity A",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": performer_id,
        },
        headers=headers,
    )
    activity_a_id = resp.json()["data"]["id"]

    # Activity B (manual)
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Activity B",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": performer_id,
        },
        headers=headers,
    )
    activity_b_id = resp.json()["data"]["id"]

    # End
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    # Normal flows: Start -> A -> B -> End
    await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": activity_a_id},
        headers=headers,
    )
    await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": activity_a_id, "target_activity_id": activity_b_id},
        headers=headers,
    )
    await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": activity_b_id, "target_activity_id": end_id},
        headers=headers,
    )

    # REJECT flow: B -> A
    await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={
            "source_activity_id": activity_b_id,
            "target_activity_id": activity_a_id,
            "flow_type": "reject",
        },
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
        "activity_a_id": activity_a_id,
        "activity_b_id": activity_b_id,
        "end_id": end_id,
    }


# ---------------------------------------------------------------------------
# EXEC-11: Reject traverses reject flow
# ---------------------------------------------------------------------------


async def test_reject_traverses_reject_flow(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """EXEC-11: Rejecting Activity B follows REJECT flow back to Activity A.

    Activity A resets to ACTIVE, new work item created, workflow stays RUNNING.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_reject_template(
        async_client, headers, str(admin_user.id)
    )

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": tmpl["template_id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # Activity A should be active with work item
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    wi_a_id = available[0]["id"]

    # Complete Activity A
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_a_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Activity B should now be active with work item
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    wi_b_id = available[0]["id"]

    # Acquire Activity B work item (required for reject)
    resp = await async_client.post(
        f"/api/v1/inbox/{wi_b_id}/acquire", headers=headers
    )
    assert resp.status_code == 200

    # Reject Activity B
    resp = await async_client.post(
        f"/api/v1/inbox/{wi_b_id}/reject",
        json={"reason": "Needs revision"},
        headers=headers,
    )
    assert resp.status_code == 200

    # Verify: Activity A is back to ACTIVE with new work item
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    data = resp.json()["data"]
    assert data["state"] == "running", "Workflow should still be running after reject"

    # Find Activity A instance state
    activity_a_instances = [
        a for a in data["activity_instances"]
        if a["activity_template_id"] == tmpl["activity_a_id"]
    ]
    assert len(activity_a_instances) == 1
    assert activity_a_instances[0]["state"] == "active", "Activity A should be reactivated"

    # New work item should be available for Activity A
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    all_items = resp.json()["data"]
    available = [wi for wi in all_items if wi["state"] == "available"]
    assert len(available) >= 1, "Should have at least one available work item for Activity A"

    # Old Activity B work item should be rejected
    rejected = [wi for wi in all_items if wi["state"] == "rejected"]
    assert len(rejected) >= 1, "Activity B work item should be in rejected state"


# ---------------------------------------------------------------------------
# EXEC-11 negative: Reject without reject flow returns error
# ---------------------------------------------------------------------------


async def test_reject_no_reject_flow_errors(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """EXEC-11 negative: Rejecting when no reject flow exists returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create a simple template without reject flows: Start -> Manual -> End
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "No Reject Test", "description": "No reject flow"},
        headers=headers,
    )
    template_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "Start", "activity_type": "start"},
        headers=headers,
    )
    start_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Task",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    task_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": task_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": task_id, "target_activity_id": end_id},
        headers=headers,
    )

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    assert resp.status_code == 200
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )
    assert resp.status_code == 200

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    # Get work item and acquire
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    wi_id = available[0]["id"]

    resp = await async_client.post(
        f"/api/v1/inbox/{wi_id}/acquire", headers=headers
    )
    assert resp.status_code == 200

    # Try to reject -- should fail
    resp = await async_client.post(
        f"/api/v1/inbox/{wi_id}/reject",
        json={"reason": "Testing"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "No reject flow" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# D-04: Reject preserves variables
# ---------------------------------------------------------------------------


async def test_reject_preserves_variables(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """D-04: Process variables are preserved when a reject flow reactivates a previous activity."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create template with reject flow and a variable
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "Reject Vars Test", "description": "Reject preserves vars"},
        headers=headers,
    )
    template_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "Start", "activity_type": "start"},
        headers=headers,
    )
    start_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Activity A",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    activity_a_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Activity B",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    activity_b_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    # Flows
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": activity_a_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": activity_a_id, "target_activity_id": activity_b_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": activity_b_id, "target_activity_id": end_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={
            "source_activity_id": activity_b_id,
            "target_activity_id": activity_a_id,
            "flow_type": "reject",
        },
        headers=headers,
    )

    # Add variable
    await async_client.post(
        f"/api/v1/templates/{template_id}/variables",
        json={"name": "revision_count", "variable_type": "int", "default_int_value": 0},
        headers=headers,
    )

    # Validate and install
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    assert resp.status_code == 200
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )
    assert resp.status_code == 200

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    # Complete Activity A, setting revision_count = 1
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    wi_a_id = available[0]["id"]

    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_a_id}/complete",
        json={"output_variables": {"revision_count": 1}},
        headers=headers,
    )
    assert resp.status_code == 200

    # Acquire and reject Activity B
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    wi_b_id = available[0]["id"]

    resp = await async_client.post(
        f"/api/v1/inbox/{wi_b_id}/acquire", headers=headers
    )
    assert resp.status_code == 200

    resp = await async_client.post(
        f"/api/v1/inbox/{wi_b_id}/reject",
        json={"reason": "Needs revision"},
        headers=headers,
    )
    assert resp.status_code == 200

    # Verify revision_count is still 1 (preserved through rejection)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/variables", headers=headers
    )
    assert resp.status_code == 200
    vars_data = resp.json()["data"]
    revision_var = [v for v in vars_data if v["name"] == "revision_count"][0]
    assert revision_var["int_value"] == 1, (
        f"revision_count should be preserved as 1, got {revision_var['int_value']}"
    )
