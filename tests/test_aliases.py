"""Integration tests for alias set CRUD and snapshot-at-start (ALIAS-01, ALIAS-02, ALIAS-03)."""
import pytest
from httpx import AsyncClient

from app.models.user import User


# ---------------------------------------------------------------------------
# ALIAS-01: Create alias set
# ---------------------------------------------------------------------------


async def test_create_alias_set(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """ALIAS-01: Create an alias set with mappings via POST /api/v1/alias-sets."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await async_client.post(
        "/api/v1/alias-sets/",
        json={
            "name": "Review Team",
            "description": "Reviewers",
            "mappings": [
                {
                    "alias_name": "reviewer",
                    "target_type": "user",
                    "target_id": str(admin_user.id),
                },
                {
                    "alias_name": "approver",
                    "target_type": "user",
                    "target_id": str(admin_user.id),
                },
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Create alias set failed: {resp.json()}"
    data = resp.json()["data"]
    assert data["name"] == "Review Team"
    alias_set_id = data["id"]

    # Verify via GET
    resp = await async_client.get(
        f"/api/v1/alias-sets/{alias_set_id}", headers=headers
    )
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert len(detail["mappings"]) == 2
    mapping_names = {m["alias_name"] for m in detail["mappings"]}
    assert mapping_names == {"reviewer", "approver"}


# ---------------------------------------------------------------------------
# ALIAS-01: List alias sets
# ---------------------------------------------------------------------------


async def test_list_alias_sets(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """ALIAS-01: List alias sets with pagination."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create 2 alias sets
    await async_client.post(
        "/api/v1/alias-sets/",
        json={"name": "Set A", "mappings": []},
        headers=headers,
    )
    await async_client.post(
        "/api/v1/alias-sets/",
        json={"name": "Set B", "mappings": []},
        headers=headers,
    )

    resp = await async_client.get("/api/v1/alias-sets/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 2
    assert resp.json()["meta"]["total_count"] >= 2


# ---------------------------------------------------------------------------
# ALIAS-01: Update alias set
# ---------------------------------------------------------------------------


async def test_update_alias_set(
    async_client: AsyncClient, admin_token: str
):
    """ALIAS-01: Update alias set name via PATCH."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await async_client.post(
        "/api/v1/alias-sets/",
        json={"name": "Original Name", "mappings": []},
        headers=headers,
    )
    alias_set_id = resp.json()["data"]["id"]

    resp = await async_client.patch(
        f"/api/v1/alias-sets/{alias_set_id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await async_client.get(
        f"/api/v1/alias-sets/{alias_set_id}", headers=headers
    )
    assert resp.json()["data"]["name"] == "Updated Name"


# ---------------------------------------------------------------------------
# ALIAS-01: Delete alias set
# ---------------------------------------------------------------------------


async def test_delete_alias_set(
    async_client: AsyncClient, admin_token: str
):
    """ALIAS-01: Soft-delete alias set via DELETE."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await async_client.post(
        "/api/v1/alias-sets/",
        json={"name": "To Delete", "mappings": []},
        headers=headers,
    )
    alias_set_id = resp.json()["data"]["id"]

    resp = await async_client.delete(
        f"/api/v1/alias-sets/{alias_set_id}", headers=headers
    )
    assert resp.status_code == 204

    # GET should return 404 (soft-deleted)
    resp = await async_client.get(
        f"/api/v1/alias-sets/{alias_set_id}", headers=headers
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# ALIAS-01: Add and remove alias mappings
# ---------------------------------------------------------------------------


async def test_add_remove_alias_mapping(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """ALIAS-01: Add and remove individual alias mappings."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create alias set with 1 mapping
    resp = await async_client.post(
        "/api/v1/alias-sets/",
        json={
            "name": "Mapping Test",
            "mappings": [
                {
                    "alias_name": "reviewer",
                    "target_type": "user",
                    "target_id": str(admin_user.id),
                },
            ],
        },
        headers=headers,
    )
    alias_set_id = resp.json()["data"]["id"]

    # Add second mapping
    resp = await async_client.post(
        f"/api/v1/alias-sets/{alias_set_id}/mappings",
        json={
            "alias_name": "approver",
            "target_type": "user",
            "target_id": str(admin_user.id),
        },
        headers=headers,
    )
    assert resp.status_code == 201
    new_mapping_id = resp.json()["data"]["id"]

    # Verify 2 mappings
    resp = await async_client.get(
        f"/api/v1/alias-sets/{alias_set_id}", headers=headers
    )
    assert len(resp.json()["data"]["mappings"]) == 2

    # Remove the new mapping
    resp = await async_client.delete(
        f"/api/v1/alias-sets/{alias_set_id}/mappings/{new_mapping_id}",
        headers=headers,
    )
    assert resp.status_code == 204

    # Verify 1 mapping remains
    resp = await async_client.get(
        f"/api/v1/alias-sets/{alias_set_id}", headers=headers
    )
    assert len(resp.json()["data"]["mappings"]) == 1


# ---------------------------------------------------------------------------
# ALIAS-02: Template with alias set
# ---------------------------------------------------------------------------


async def test_template_alias_set(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """ALIAS-02: Template references alias set; alias performer resolves correctly."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create alias set with "reviewer" -> admin_user
    resp = await async_client.post(
        "/api/v1/alias-sets/",
        json={
            "name": "Template Alias Test",
            "mappings": [
                {
                    "alias_name": "reviewer",
                    "target_type": "user",
                    "target_id": str(admin_user.id),
                },
            ],
        },
        headers=headers,
    )
    alias_set_id = resp.json()["data"]["id"]

    # Create template referencing this alias set
    resp = await async_client.post(
        "/api/v1/templates/",
        json={
            "name": "Alias Template",
            "description": "Uses alias performer",
            "alias_set_id": alias_set_id,
        },
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
            "performer_type": "alias",
            "performer_id": "reviewer",
        },
        headers=headers,
    )
    review_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    # Flows
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": review_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": review_id, "target_activity_id": end_id},
        headers=headers,
    )

    # Install
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    assert resp.status_code == 200
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )
    assert resp.status_code == 200

    # Start workflow -- alias "reviewer" should resolve to admin_user
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # Work item should be assigned to admin_user
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    work_items = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(work_items) == 1
    assert work_items[0]["performer_id"] == str(admin_user.id)


# ---------------------------------------------------------------------------
# ALIAS-03: Update alias set independent of template
# ---------------------------------------------------------------------------


async def test_alias_update_independent(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User,
    regular_user: User,
):
    """ALIAS-03: Updating alias set changes future workflow starts without editing template."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create alias set pointing reviewer to admin_user
    resp = await async_client.post(
        "/api/v1/alias-sets/",
        json={
            "name": "Independent Update Test",
            "mappings": [
                {
                    "alias_name": "reviewer",
                    "target_type": "user",
                    "target_id": str(admin_user.id),
                },
            ],
        },
        headers=headers,
    )
    alias_set_id = resp.json()["data"]["id"]
    original_mapping_id = resp.json()["data"]["mappings"][0]["id"]

    # Create and install template
    resp = await async_client.post(
        "/api/v1/templates/",
        json={
            "name": "Alias Update Test",
            "description": "Test alias independence",
            "alias_set_id": alias_set_id,
        },
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
            "name": "Review",
            "activity_type": "manual",
            "performer_type": "alias",
            "performer_id": "reviewer",
        },
        headers=headers,
    )
    review_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": review_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": review_id, "target_activity_id": end_id},
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

    # Start first workflow (reviewer = admin_user)
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    wf1_id = resp.json()["data"]["id"]

    # Update alias set: remove old mapping, add new one pointing to regular_user
    await async_client.delete(
        f"/api/v1/alias-sets/{alias_set_id}/mappings/{original_mapping_id}",
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/alias-sets/{alias_set_id}/mappings",
        json={
            "alias_name": "reviewer",
            "target_type": "user",
            "target_id": str(regular_user.id),
        },
        headers=headers,
    )

    # Start second workflow (reviewer should now = regular_user)
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    wf2_id = resp.json()["data"]["id"]

    # First workflow: work item assigned to admin_user (from snapshot)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf1_id}/work-items", headers=headers
    )
    wf1_items = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(wf1_items) == 1
    assert wf1_items[0]["performer_id"] == str(admin_user.id), (
        f"First workflow should have admin as reviewer, got {wf1_items[0]['performer_id']}"
    )

    # Second workflow: work item assigned to regular_user (updated alias)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf2_id}/work-items", headers=headers
    )
    wf2_items = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(wf2_items) == 1
    assert wf2_items[0]["performer_id"] == str(regular_user.id), (
        f"Second workflow should have regular_user as reviewer, got {wf2_items[0]['performer_id']}"
    )


# ---------------------------------------------------------------------------
# ALIAS-03 + D-06: Alias snapshot at start
# ---------------------------------------------------------------------------


async def test_alias_snapshot_at_start(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User,
    regular_user: User,
):
    """ALIAS-03/D-06: Mid-workflow alias update does not affect running workflow."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create alias set
    resp = await async_client.post(
        "/api/v1/alias-sets/",
        json={
            "name": "Snapshot Test",
            "mappings": [
                {
                    "alias_name": "reviewer",
                    "target_type": "user",
                    "target_id": str(admin_user.id),
                },
            ],
        },
        headers=headers,
    )
    alias_set_id = resp.json()["data"]["id"]
    mapping_id = resp.json()["data"]["mappings"][0]["id"]

    # Create, install template
    resp = await async_client.post(
        "/api/v1/templates/",
        json={
            "name": "Snapshot Alias",
            "description": "Snapshot test",
            "alias_set_id": alias_set_id,
        },
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
            "name": "Review",
            "activity_type": "manual",
            "performer_type": "alias",
            "performer_id": "reviewer",
        },
        headers=headers,
    )
    review_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": review_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": review_id, "target_activity_id": end_id},
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

    # Start workflow (reviewer = admin_user from snapshot)
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    # Update alias set mid-workflow: change reviewer to regular_user
    await async_client.delete(
        f"/api/v1/alias-sets/{alias_set_id}/mappings/{mapping_id}",
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/alias-sets/{alias_set_id}/mappings",
        json={
            "alias_name": "reviewer",
            "target_type": "user",
            "target_id": str(regular_user.id),
        },
        headers=headers,
    )

    # Running workflow should still have admin_user as reviewer (from snapshot)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    work_items = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(work_items) == 1
    assert work_items[0]["performer_id"] == str(admin_user.id), (
        "Running workflow should use snapshot (admin), not updated alias (regular_user)"
    )
