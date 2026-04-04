"""Integration tests for work queues (QUEUE-01, QUEUE-02, QUEUE-03, QUEUE-04)."""
import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(
    db_session, username: str, *, is_superuser: bool = False
) -> User:
    user = User(
        id=uuid.uuid4(),
        username=username,
        hashed_password=hash_password("password123"),
        is_active=True,
        is_superuser=is_superuser,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _token(user: User) -> str:
    return create_access_token({"sub": str(user.id), "username": user.username})


async def _create_queue(
    client: AsyncClient, admin_token: str, name: str, description: str = "Test queue"
) -> dict:
    """Create a queue via API and return the response data."""
    resp = await client.post(
        "/api/v1/queues",
        json={"name": name, "description": description},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return resp.json()["data"]


async def _create_queue_workflow_setup(
    client: AsyncClient,
    db_session,
    admin_token: str,
    admin_user: User,
) -> dict:
    """Create a queue with 2 members, a template using queue performer, and start workflow.

    Returns dict with: queue_id, member_a, member_b, workflow_id, token_a, token_b
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create queue
    queue = await _create_queue(client, admin_token, f"Test Queue {uuid.uuid4().hex[:6]}")
    queue_id = queue["id"]

    # Create two queue member users
    member_a = await _create_user(db_session, f"qmember_a_{uuid.uuid4().hex[:6]}")
    member_b = await _create_user(db_session, f"qmember_b_{uuid.uuid4().hex[:6]}")

    # Add both as members
    await client.post(
        f"/api/v1/queues/{queue_id}/members",
        json={"user_id": str(member_a.id)},
        headers=headers,
    )
    await client.post(
        f"/api/v1/queues/{queue_id}/members",
        json={"user_id": str(member_b.id)},
        headers=headers,
    )

    # Create template: start -> manual(queue performer) -> end
    resp = await client.post(
        "/api/v1/templates/",
        json={"name": f"Queue Template {uuid.uuid4().hex[:6]}", "description": "Queue test"},
        headers=headers,
    )
    template_id = resp.json()["data"]["id"]

    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "Start", "activity_type": "start"},
        headers=headers,
    )
    start_id = resp.json()["data"]["id"]

    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Queue Review",
            "activity_type": "manual",
            "performer_type": "queue",
            "performer_id": queue_id,
        },
        headers=headers,
    )
    manual_id = resp.json()["data"]["id"]

    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": manual_id},
        headers=headers,
    )
    await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": manual_id, "target_activity_id": end_id},
        headers=headers,
    )

    resp = await client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    assert resp.status_code == 200
    resp = await client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )
    assert resp.status_code == 200

    # Start workflow
    resp = await client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    assert resp.status_code == 201
    workflow_id = resp.json()["data"]["id"]

    return {
        "queue_id": queue_id,
        "member_a": member_a,
        "member_b": member_b,
        "workflow_id": workflow_id,
        "token_a": _token(member_a),
        "token_b": _token(member_b),
    }


# ---------------------------------------------------------------------------
# QUEUE-01: Queue CRUD
# ---------------------------------------------------------------------------


class TestQueueCRUD:
    """QUEUE-01: queue CRUD and member management."""

    async def test_create_queue(self, async_client: AsyncClient, admin_token):
        """Create a queue successfully."""
        data = await _create_queue(async_client, admin_token, "Review Queue")
        assert data["name"] == "Review Queue"
        assert data["is_active"] is True
        assert "id" in data

    async def test_create_queue_duplicate_name(
        self, async_client: AsyncClient, admin_token
    ):
        """Duplicate queue name returns 400."""
        await _create_queue(async_client, admin_token, "Dup Queue")
        resp = await async_client.post(
            "/api/v1/queues",
            json={"name": "Dup Queue"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400

    async def test_list_queues(self, async_client: AsyncClient, admin_token):
        """List queues returns all created queues."""
        await _create_queue(async_client, admin_token, "List Q1")
        await _create_queue(async_client, admin_token, "List Q2")

        resp = await async_client.get(
            "/api/v1/queues",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 2

    async def test_update_queue(self, async_client: AsyncClient, admin_token):
        """Update queue name."""
        queue = await _create_queue(async_client, admin_token, "Old Name")
        resp = await async_client.put(
            f"/api/v1/queues/{queue['id']}",
            json={"name": "New Name"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "New Name"

    async def test_delete_queue(self, async_client: AsyncClient, admin_token):
        """Soft-delete a queue."""
        queue = await _create_queue(async_client, admin_token, "Delete Me")
        resp = await async_client.delete(
            f"/api/v1/queues/{queue['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 204

        # Should not appear in list
        resp = await async_client.get(
            "/api/v1/queues",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        queue_ids = [q["id"] for q in resp.json()["data"]]
        assert queue["id"] not in queue_ids

    async def test_add_remove_member(
        self, async_client: AsyncClient, admin_token, db_session, admin_user
    ):
        """Add and remove a member from a queue."""
        queue = await _create_queue(async_client, admin_token, "Member Queue")
        user = await _create_user(db_session, "member_test_user")

        # Add member
        resp = await async_client.post(
            f"/api/v1/queues/{queue['id']}/members",
            json={"user_id": str(user.id)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201

        # Verify member appears in queue detail
        resp = await async_client.get(
            f"/api/v1/queues/{queue['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        members = resp.json()["data"]["members"]
        member_ids = [m["id"] for m in members]
        assert str(user.id) in member_ids

        # Remove member
        resp = await async_client.delete(
            f"/api/v1/queues/{queue['id']}/members/{user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 204

    async def test_queue_admin_only(
        self, async_client: AsyncClient, regular_token
    ):
        """Non-admin users cannot manage queues."""
        resp = await async_client.post(
            "/api/v1/queues",
            json={"name": "Forbidden Queue"},
            headers={"Authorization": f"Bearer {regular_token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# QUEUE-02: Queue performer creates shared item
# ---------------------------------------------------------------------------


class TestQueuePerformer:
    """QUEUE-02: queue performer type creates shared work items."""

    async def test_queue_performer_creates_shared_item(
        self, async_client: AsyncClient, db_session, admin_token, admin_user
    ):
        """Starting a workflow with queue performer creates one item with queue_id."""
        setup = await _create_queue_workflow_setup(
            async_client, db_session, admin_token, admin_user
        )

        # Check work items for this workflow
        resp = await async_client.get(
            f"/api/v1/workflows/{setup['workflow_id']}/work-items",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        work_items = resp.json()["data"]

        # Should have exactly one work item for the manual queue activity
        # (start and end auto-complete, no work items for those)
        queue_items = [wi for wi in work_items if wi["performer_id"] is None]
        assert len(queue_items) == 1, "Should have exactly one unassigned queue item"
        assert queue_items[0]["state"] == "available"


# ---------------------------------------------------------------------------
# QUEUE-03: Queue claim
# ---------------------------------------------------------------------------


class TestQueueClaim:
    """QUEUE-03: queue members can claim work items."""

    async def test_queue_member_can_claim(
        self, async_client: AsyncClient, db_session, admin_token, admin_user
    ):
        """A queue member can acquire (claim) a queue work item."""
        setup = await _create_queue_workflow_setup(
            async_client, db_session, admin_token, admin_user
        )

        # Member A sees the item in inbox
        resp = await async_client.get(
            "/api/v1/inbox",
            headers={"Authorization": f"Bearer {setup['token_a']}"},
        )
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) >= 1, "Queue member A should see queue item in inbox"
        item_id = items[0]["id"]

        # Member A claims it
        resp = await async_client.post(
            f"/api/v1/inbox/{item_id}/acquire",
            headers={"Authorization": f"Bearer {setup['token_a']}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["state"] == "acquired"
        assert data["performer_id"] == str(setup["member_a"].id)

    async def test_non_member_cannot_claim(
        self, async_client: AsyncClient, db_session, admin_token, admin_user
    ):
        """A user who is NOT a queue member cannot claim a queue item."""
        setup = await _create_queue_workflow_setup(
            async_client, db_session, admin_token, admin_user
        )
        outsider = await _create_user(db_session, f"outsider_{uuid.uuid4().hex[:6]}")
        outsider_token = _token(outsider)

        # Get the work item ID from work items list
        resp = await async_client.get(
            f"/api/v1/workflows/{setup['workflow_id']}/work-items",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        work_items = resp.json()["data"]
        queue_item = [wi for wi in work_items if wi["performer_id"] is None][0]

        # Outsider tries to claim
        resp = await async_client.post(
            f"/api/v1/inbox/{queue_item['id']}/acquire",
            headers={"Authorization": f"Bearer {outsider_token}"},
        )
        assert resp.status_code == 400

    async def test_queue_item_visible_in_inbox(
        self, async_client: AsyncClient, db_session, admin_token, admin_user
    ):
        """Queue items appear in queue member's inbox."""
        setup = await _create_queue_workflow_setup(
            async_client, db_session, admin_token, admin_user
        )

        # Member A inbox
        resp = await async_client.get(
            "/api/v1/inbox",
            headers={"Authorization": f"Bearer {setup['token_a']}"},
        )
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) >= 1

        # Member B inbox also sees it
        resp = await async_client.get(
            "/api/v1/inbox",
            headers={"Authorization": f"Bearer {setup['token_b']}"},
        )
        assert resp.status_code == 200
        items_b = resp.json()["data"]
        assert len(items_b) >= 1


# ---------------------------------------------------------------------------
# QUEUE-04: Claim locking and release
# ---------------------------------------------------------------------------


class TestQueueLocking:
    """QUEUE-04: claimed items are locked; can be released."""

    async def test_claimed_item_locked(
        self, async_client: AsyncClient, db_session, admin_token, admin_user
    ):
        """Once claimed by A, user B cannot claim the same item."""
        setup = await _create_queue_workflow_setup(
            async_client, db_session, admin_token, admin_user
        )

        # Member A sees and claims
        resp = await async_client.get(
            "/api/v1/inbox",
            headers={"Authorization": f"Bearer {setup['token_a']}"},
        )
        item_id = resp.json()["data"][0]["id"]

        resp = await async_client.post(
            f"/api/v1/inbox/{item_id}/acquire",
            headers={"Authorization": f"Bearer {setup['token_a']}"},
        )
        assert resp.status_code == 200

        # Member B tries to claim the same item
        resp = await async_client.post(
            f"/api/v1/inbox/{item_id}/acquire",
            headers={"Authorization": f"Bearer {setup['token_b']}"},
        )
        assert resp.status_code == 400

    async def test_release_claimed_queue_item(
        self, async_client: AsyncClient, db_session, admin_token, admin_user
    ):
        """Releasing a claimed item makes it available for others."""
        setup = await _create_queue_workflow_setup(
            async_client, db_session, admin_token, admin_user
        )

        # Member A claims
        resp = await async_client.get(
            "/api/v1/inbox",
            headers={"Authorization": f"Bearer {setup['token_a']}"},
        )
        item_id = resp.json()["data"][0]["id"]

        await async_client.post(
            f"/api/v1/inbox/{item_id}/acquire",
            headers={"Authorization": f"Bearer {setup['token_a']}"},
        )

        # Member A releases
        resp = await async_client.post(
            f"/api/v1/inbox/{item_id}/release",
            headers={"Authorization": f"Bearer {setup['token_a']}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["state"] == "available"
        assert data["performer_id"] is None

        # Now member B can claim
        resp = await async_client.post(
            f"/api/v1/inbox/{item_id}/acquire",
            headers={"Authorization": f"Bearer {setup['token_b']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["state"] == "acquired"
