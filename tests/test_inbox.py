"""Integration tests for inbox API (INBOX-01 through INBOX-07, PERF-01 through PERF-03)."""
import pytest
from httpx import AsyncClient

from app.models.user import User


# ---------------------------------------------------------------------------
# Helper fixture: start a workflow so a work item exists
# ---------------------------------------------------------------------------


@pytest.fixture
async def started_workflow(async_client: AsyncClient, admin_token: str, installed_template: dict):
    """Start a workflow from installed_template so a work item exists for admin_user."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": installed_template["template_id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    wf = resp.json()["data"]
    return wf


# ---------------------------------------------------------------------------
# INBOX-01, PERF-02: Work item appears in performer's inbox
# ---------------------------------------------------------------------------


async def test_work_item_appears_in_inbox(
    async_client: AsyncClient, admin_token: str, started_workflow: dict
):
    """INBOX-01/PERF-02: Work item appears in performer's inbox when workflow starts."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1, "Expected at least one work item in inbox"

    item = data[0]
    assert item["state"] == "available"
    assert "activity" in item
    assert "name" in item["activity"]
    assert "workflow" in item
    assert "template_name" in item["workflow"]


# ---------------------------------------------------------------------------
# INBOX-03: Inbox item detail with activity, workflow, documents, comments
# ---------------------------------------------------------------------------


async def test_inbox_item_detail(
    async_client: AsyncClient, admin_token: str, started_workflow: dict
):
    """INBOX-03: Detail endpoint returns activity, workflow, documents, and comments."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get work item id from inbox list
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) >= 1
    work_item_id = items[0]["id"]

    # Get detail
    resp = await async_client.get(f"/api/v1/inbox/{work_item_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]

    # Activity info
    assert "activity" in data
    assert "name" in data["activity"]
    assert "activity_type" in data["activity"]

    # Workflow info
    assert "workflow" in data
    assert "id" in data["workflow"]
    assert "template_name" in data["workflow"]
    assert "state" in data["workflow"]

    # Documents and comments
    assert "documents" in data
    assert isinstance(data["documents"], list)
    assert "comments" in data
    assert isinstance(data["comments"], list)


# ---------------------------------------------------------------------------
# INBOX-07: Priority and due_date visible in inbox
# ---------------------------------------------------------------------------


async def test_inbox_shows_priority_due_date(
    async_client: AsyncClient, admin_token: str, started_workflow: dict
):
    """INBOX-07: Inbox items include priority and due_date fields."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1

    for item in data:
        assert "priority" in item, "Item missing priority field"
        assert isinstance(item["priority"], int), "priority should be int"
        assert "due_date" in item, "Item missing due_date field"
        # due_date can be None, but the key must exist


# ---------------------------------------------------------------------------
# INBOX-02: Filtering and sorting
# ---------------------------------------------------------------------------


async def test_inbox_filters_and_sorting(
    async_client: AsyncClient, admin_token: str, started_workflow: dict
):
    """INBOX-02: Inbox list filterable by state, priority, template_name; sortable."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Filter by state=available
    resp = await async_client.get("/api/v1/inbox?state=available", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    for item in data:
        assert item["state"] == "available", f"Expected state available, got {item['state']}"

    # Sort by priority ascending
    resp = await async_client.get(
        "/api/v1/inbox?sort_by=priority&sort_order=asc", headers=headers
    )
    assert resp.status_code == 200

    # Filter by template_name (installed_template is named "Simple Workflow")
    resp = await async_client.get("/api/v1/inbox?template_name=Simple", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1, "Expected at least 1 result for template_name=Simple"


# ---------------------------------------------------------------------------
# D-08, D-09: Acquire and release
# ---------------------------------------------------------------------------


async def test_acquire_and_release(
    async_client: AsyncClient, admin_token: str, started_workflow: dict
):
    """D-08/D-09: Acquire transitions AVAILABLE->ACQUIRED, release ACQUIRED->AVAILABLE."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get work item id
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    work_item_id = resp.json()["data"][0]["id"]

    # Acquire
    resp = await async_client.post(f"/api/v1/inbox/{work_item_id}/acquire", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["state"] == "acquired"
    assert data["performer_id"] is not None

    # Release
    resp = await async_client.post(f"/api/v1/inbox/{work_item_id}/release", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["state"] == "available"
    assert data["performer_id"] is None

    # Re-acquire
    resp = await async_client.post(f"/api/v1/inbox/{work_item_id}/acquire", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["state"] == "acquired"


# ---------------------------------------------------------------------------
# INBOX-04: Complete from inbox advances workflow
# ---------------------------------------------------------------------------


async def test_complete_from_inbox(
    async_client: AsyncClient, admin_token: str, started_workflow: dict
):
    """INBOX-04: Complete from inbox marks work item complete and advances workflow."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    wf_id = started_workflow["id"]

    # Get work item id
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    work_item_id = resp.json()["data"][0]["id"]

    # Must acquire before completing
    resp = await async_client.post(f"/api/v1/inbox/{work_item_id}/acquire", headers=headers)
    assert resp.status_code == 200

    # Complete
    resp = await async_client.post(
        f"/api/v1/inbox/{work_item_id}/complete",
        json={"output_variables": {}},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["state"] == "complete"

    # Verify workflow has advanced (simple template: start -> manual -> end, should be finished)
    resp = await async_client.get(f"/api/v1/workflows/{wf_id}", headers=headers)
    assert resp.status_code == 200
    wf_data = resp.json()["data"]
    assert wf_data["state"] == "finished", "Workflow should be finished after completing the only manual step"


# ---------------------------------------------------------------------------
# D-08: Complete requires acquire
# ---------------------------------------------------------------------------


async def test_complete_requires_acquire(
    async_client: AsyncClient, admin_token: str, started_workflow: dict
):
    """D-08: Attempting to complete without acquiring first returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get work item id (state is AVAILABLE)
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    work_item_id = resp.json()["data"][0]["id"]

    # Try to complete without acquiring
    resp = await async_client.post(
        f"/api/v1/inbox/{work_item_id}/complete",
        json={"output_variables": {}},
        headers=headers,
    )
    assert resp.status_code == 400, "Should fail when completing without acquiring first"


# ---------------------------------------------------------------------------
# INBOX-05, D-04: Reject work item
# ---------------------------------------------------------------------------


async def test_reject_work_item(
    async_client: AsyncClient, admin_token: str, started_workflow: dict
):
    """INBOX-05/D-04: Reject marks work item as REJECTED."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get work item id
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    work_item_id = resp.json()["data"][0]["id"]

    # Must acquire first
    resp = await async_client.post(f"/api/v1/inbox/{work_item_id}/acquire", headers=headers)
    assert resp.status_code == 200

    # Reject
    resp = await async_client.post(
        f"/api/v1/inbox/{work_item_id}/reject",
        json={"reason": "Needs revision"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["state"] == "rejected"


# ---------------------------------------------------------------------------
# INBOX-06: Comments
# ---------------------------------------------------------------------------


async def test_work_item_comments(
    async_client: AsyncClient, admin_token: str, started_workflow: dict
):
    """INBOX-06: Comments can be added and listed on work items."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get work item id
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    work_item_id = resp.json()["data"][0]["id"]

    # Add first comment
    resp = await async_client.post(
        f"/api/v1/inbox/{work_item_id}/comments",
        json={"content": "This looks good"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["content"] == "This looks good"

    # Add second comment
    resp = await async_client.post(
        f"/api/v1/inbox/{work_item_id}/comments",
        json={"content": "Second comment"},
        headers=headers,
    )
    assert resp.status_code == 201

    # List comments
    resp = await async_client.get(
        f"/api/v1/inbox/{work_item_id}/comments", headers=headers
    )
    assert resp.status_code == 200
    comments = resp.json()["data"]
    assert len(comments) == 2, f"Expected 2 comments, got {len(comments)}"

    # Check comment_count in detail
    resp = await async_client.get(f"/api/v1/inbox/{work_item_id}", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["comment_count"] == 2, f"Expected comment_count=2, got {detail['comment_count']}"


# ---------------------------------------------------------------------------
# PERF-01: Supervisor performer
# ---------------------------------------------------------------------------


async def test_supervisor_performer(
    async_client: AsyncClient, admin_token: str, admin_user: User
):
    """PERF-01: Supervisor performer type routes work item to workflow initiator."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create a template with supervisor performer type
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "Supervisor Workflow", "description": "Supervisor test"},
        headers=headers,
    )
    assert resp.status_code == 201
    template_id = resp.json()["data"]["id"]

    # Start activity
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "Start", "activity_type": "start"},
        headers=headers,
    )
    start_id = resp.json()["data"]["id"]

    # Manual activity with supervisor performer
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Supervisor Review",
            "activity_type": "manual",
            "performer_type": "supervisor",
        },
        headers=headers,
    )
    manual_id = resp.json()["data"]["id"]

    # End activity
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

    # Validate and install
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    assert resp.status_code == 200
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )
    assert resp.status_code == 200

    # Start workflow (admin_user becomes supervisor)
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    assert resp.status_code == 201

    # Check inbox -- admin should see the work item
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    supervisor_items = [
        item for item in data
        if item["activity"]["name"] == "Supervisor Review"
    ]
    assert len(supervisor_items) >= 1, "Supervisor work item should appear in initiator's inbox"


# ---------------------------------------------------------------------------
# PERF-03: Group performer
# ---------------------------------------------------------------------------


async def test_group_performer(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User,
    regular_user: User,
    regular_token: str,
):
    """PERF-03: Group performer creates work items for all group members."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create a group
    resp = await async_client.post(
        "/api/v1/groups/",
        json={"name": "Reviewers", "description": "Review group"},
        headers=headers,
    )
    assert resp.status_code == 201
    group_id = resp.json()["data"]["id"]

    # Add both users to group
    resp = await async_client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_ids": [str(admin_user.id), str(regular_user.id)]},
        headers=headers,
    )
    assert resp.status_code == 200

    # Create template with group performer
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "Group Workflow", "description": "Group test"},
        headers=headers,
    )
    template_id = resp.json()["data"]["id"]

    # Start
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "Start", "activity_type": "start"},
        headers=headers,
    )
    start_id = resp.json()["data"]["id"]

    # Manual activity with group performer
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Group Review",
            "activity_type": "manual",
            "performer_type": "group",
            "performer_id": group_id,
        },
        headers=headers,
    )
    manual_id = resp.json()["data"]["id"]

    # End
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
    assert resp.status_code == 201

    # Admin should see work item
    resp = await async_client.get("/api/v1/inbox", headers=headers)
    assert resp.status_code == 200
    admin_items = [
        item for item in resp.json()["data"]
        if item["activity"]["name"] == "Group Review"
    ]
    assert len(admin_items) >= 1, "Admin should see group work item in inbox"

    # Regular user should also see work item
    regular_headers = {"Authorization": f"Bearer {regular_token}"}
    resp = await async_client.get("/api/v1/inbox", headers=regular_headers)
    assert resp.status_code == 200
    regular_items = [
        item for item in resp.json()["data"]
        if item["activity"]["name"] == "Group Review"
    ]
    assert len(regular_items) >= 1, "Regular user should see group work item in inbox"
