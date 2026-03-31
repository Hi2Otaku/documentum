"""Integration tests for sequential and runtime-selection performers (PERF-04, PERF-05)."""
import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User


# ---------------------------------------------------------------------------
# Helper: create users via HTTP
# ---------------------------------------------------------------------------


async def _create_test_user(
    client: AsyncClient,
    headers: dict,
    username: str,
) -> dict:
    """Create a user via POST /api/v1/users/ and return user data dict."""
    resp = await client.post(
        "/api/v1/users/",
        json={
            "username": username,
            "password": "testpass123",
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Create user {username} failed: {resp.json()}"
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# Helper: create sequential template
# ---------------------------------------------------------------------------


async def _create_sequential_template(
    client: AsyncClient,
    headers: dict,
    performer_ids: list[str],
) -> dict:
    """Create and install: Start -> Sequential_Activity(performer_list) -> End.

    Returns dict with template_id, sequential_id, end_id.
    """
    resp = await client.post(
        "/api/v1/templates/",
        json={"name": "Sequential Test", "description": "Sequential performers"},
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

    # Sequential activity
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Sequential Review",
            "activity_type": "manual",
            "performer_type": "sequential",
            "performer_list": performer_ids,
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Create sequential activity failed: {resp.json()}"
    sequential_id = resp.json()["data"]["id"]

    # End
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    # Flows
    await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": sequential_id},
        headers=headers,
    )
    await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": sequential_id, "target_activity_id": end_id},
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
        "sequential_id": sequential_id,
        "end_id": end_id,
    }


# ---------------------------------------------------------------------------
# PERF-04: Sequential performers (ordered completion)
# ---------------------------------------------------------------------------


async def test_sequential_performers(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """PERF-04: Sequential performer creates work items one at a time in order."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create 2 test users
    user_a = await _create_test_user(async_client, headers, "seq_user_a")
    user_b = await _create_test_user(async_client, headers, "seq_user_b")

    # Create sequential template
    tmpl = await _create_sequential_template(
        async_client, headers, [user_a["id"], user_b["id"]]
    )

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": tmpl["template_id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # First work item should be for user_a
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    assert available[0]["performer_id"] == user_a["id"]
    wi_a_id = available[0]["id"]

    # Complete as user_a via workflow endpoint (admin can do this)
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_a_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Next work item should be for user_b (activity still ACTIVE)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    assert available[0]["performer_id"] == user_b["id"]
    wi_b_id = available[0]["id"]

    # Verify activity is still ACTIVE (not COMPLETE)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    sequential_instances = [
        a for a in resp.json()["data"]["activity_instances"]
        if a["activity_template_id"] == tmpl["sequential_id"]
    ]
    assert len(sequential_instances) == 1
    assert sequential_instances[0]["state"] == "active", (
        "Sequential activity should remain ACTIVE until last performer completes"
    )

    # Complete as user_b
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_b_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Workflow should be finished (all sequential performers done, activity advances to end)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    assert resp.json()["data"]["state"] == "finished"


# ---------------------------------------------------------------------------
# PERF-04: Sequential reject back
# ---------------------------------------------------------------------------


async def test_sequential_reject_back(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """PERF-04: Rejecting in sequential performer goes back to previous performer."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    user_a = await _create_test_user(async_client, headers, "seq_rej_a")
    user_b = await _create_test_user(async_client, headers, "seq_rej_b")

    tmpl = await _create_sequential_template(
        async_client, headers, [user_a["id"], user_b["id"]]
    )

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": tmpl["template_id"]},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    # Complete first performer (user_a)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    wi_a_id = available[0]["id"]

    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_a_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # user_b's work item
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    wi_b_id = available[0]["id"]

    # user_b rejects (need to acquire first via inbox)
    # Use the workflow endpoint to acquire isn't needed -- we need to reject.
    # The engine reject_work_item requires ACQUIRED state. Let's acquire via inbox.
    # But inbox checks performer_id == current_user. Use user_b's token.
    user_b_token = create_access_token({"sub": user_b["id"], "username": "seq_rej_b"})
    user_b_headers = {"Authorization": f"Bearer {user_b_token}"}

    resp = await async_client.post(
        f"/api/v1/inbox/{wi_b_id}/acquire", headers=user_b_headers
    )
    assert resp.status_code == 200, f"Acquire failed: {resp.json()}"

    resp = await async_client.post(
        f"/api/v1/inbox/{wi_b_id}/reject",
        json={"reason": "Needs revision"},
        headers=user_b_headers,
    )
    assert resp.status_code == 200, f"Reject failed: {resp.json()}"

    # New work item should be for user_a (index decremented back to 0)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    assert available[0]["performer_id"] == user_a["id"], (
        "After reject, work item should go back to first performer"
    )

    # Complete again: user_a -> user_b -> finish
    wi_a2_id = available[0]["id"]
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_a2_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    wi_b2_id = available[0]["id"]

    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_b2_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Workflow should be finished
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    assert resp.json()["data"]["state"] == "finished"


# ---------------------------------------------------------------------------
# PERF-04: Sequential reject at first performer errors
# ---------------------------------------------------------------------------


async def test_sequential_reject_at_first_errors(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """PERF-04: Rejecting at first performer (index 0) returns error."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    user_a = await _create_test_user(async_client, headers, "seq_err_a")
    user_b = await _create_test_user(async_client, headers, "seq_err_b")

    tmpl = await _create_sequential_template(
        async_client, headers, [user_a["id"], user_b["id"]]
    )

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": tmpl["template_id"]},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    # Get first work item (user_a, index 0)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    wi_id = available[0]["id"]

    # Acquire as user_a
    user_a_token = create_access_token({"sub": user_a["id"], "username": "seq_err_a"})
    user_a_headers = {"Authorization": f"Bearer {user_a_token}"}

    resp = await async_client.post(
        f"/api/v1/inbox/{wi_id}/acquire", headers=user_a_headers
    )
    assert resp.status_code == 200

    # Try to reject at index 0 -> should fail
    resp = await async_client.post(
        f"/api/v1/inbox/{wi_id}/reject",
        json={"reason": "Testing"},
        headers=user_a_headers,
    )
    assert resp.status_code == 400
    assert "first performer" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# PERF-05: Runtime selection
# ---------------------------------------------------------------------------


async def test_runtime_selection(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """PERF-05: Runtime selection requires next_performer_id and routes to selected user."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create users
    user_a = await _create_test_user(async_client, headers, "rt_user_a")
    user_b = await _create_test_user(async_client, headers, "rt_user_b")

    # Create a group with both users
    resp = await async_client.post(
        "/api/v1/groups/",
        json={"name": "Runtime Group", "description": "Candidate group"},
        headers=headers,
    )
    assert resp.status_code == 201
    group_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_ids": [user_a["id"], user_b["id"]]},
        headers=headers,
    )
    assert resp.status_code == 200

    # Create template: Start -> Activity1(runtime_selection, group) -> Activity2(user, user_b) -> End
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "Runtime Selection Test", "description": "RT test"},
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
            "name": "Select Next",
            "activity_type": "manual",
            "performer_type": "runtime_selection",
            "performer_id": group_id,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    select_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Next Task",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": user_b["id"],
        },
        headers=headers,
    )
    next_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    # Flows
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": select_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": select_id, "target_activity_id": next_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": next_id, "target_activity_id": end_id},
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
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # First activity: runtime_selection should create unassigned work item
    # (no performer resolved by resolve_performers for runtime_selection)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    wi_select_id = available[0]["id"]

    # Complete with next_performer_id=user_b
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_select_id}/complete",
        json={"next_performer_id": user_b["id"]},
        headers=headers,
    )
    assert resp.status_code == 200

    # Next Task activity should have work item for user_b
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    assert available[0]["performer_id"] == user_b["id"]
    wi_next_id = available[0]["id"]

    # Complete Next Task
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_next_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Workflow should be finished
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    assert resp.json()["data"]["state"] == "finished"


# ---------------------------------------------------------------------------
# PERF-05: Runtime selection missing performer errors
# ---------------------------------------------------------------------------


async def test_runtime_selection_missing_performer_errors(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """PERF-05 negative: Completing runtime_selection without next_performer_id returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    user_a = await _create_test_user(async_client, headers, "rt_miss_a")

    # Create group
    resp = await async_client.post(
        "/api/v1/groups/",
        json={"name": "RT Miss Group", "description": "Test"},
        headers=headers,
    )
    group_id = resp.json()["data"]["id"]
    await async_client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_ids": [user_a["id"]]},
        headers=headers,
    )

    # Create template
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "RT Missing Test", "description": "Test"},
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
            "name": "Select Next",
            "activity_type": "manual",
            "performer_type": "runtime_selection",
            "performer_id": group_id,
        },
        headers=headers,
    )
    select_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": select_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": select_id, "target_activity_id": end_id},
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

    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    wi_id = available[0]["id"]

    # Complete without next_performer_id -> error
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "next_performer_id" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# PERF-05: Runtime selection invalid performer errors
# ---------------------------------------------------------------------------


async def test_runtime_selection_invalid_performer_errors(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """PERF-05 negative: Selecting a user not in the group returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    user_a = await _create_test_user(async_client, headers, "rt_inv_a")
    user_not_in_group = await _create_test_user(async_client, headers, "rt_inv_outside")

    # Create group with only user_a
    resp = await async_client.post(
        "/api/v1/groups/",
        json={"name": "RT Invalid Group", "description": "Test"},
        headers=headers,
    )
    group_id = resp.json()["data"]["id"]
    await async_client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_ids": [user_a["id"]]},
        headers=headers,
    )

    # Create template
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "RT Invalid Test", "description": "Test"},
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
            "name": "Select Next",
            "activity_type": "manual",
            "performer_type": "runtime_selection",
            "performer_id": group_id,
        },
        headers=headers,
    )
    select_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": select_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": select_id, "target_activity_id": end_id},
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

    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    wi_id = available[0]["id"]

    # Complete with user NOT in the group -> error
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_id}/complete",
        json={"next_performer_id": user_not_in_group["id"]},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "not a member" in resp.json()["detail"].lower()
