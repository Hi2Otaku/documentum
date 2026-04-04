"""Integration tests for delegation (USER-05, INBOX-08)."""
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
    """Create a user directly in the DB and return it."""
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


async def _create_installed_template(
    client: AsyncClient,
    admin_token: str,
    performer_id: str,
) -> dict:
    """Create start -> manual(performer_id) -> end template, validate, install.

    Returns dict with template_id, start_id, manual_id, end_id.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await client.post(
        "/api/v1/templates/",
        json={"name": f"Deleg Template {uuid.uuid4().hex[:6]}", "description": "For delegation test"},
        headers=headers,
    )
    assert resp.status_code == 201
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
            "name": "Review",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": performer_id,
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

    # Flows
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

    return {
        "template_id": template_id,
        "start_id": start_id,
        "manual_id": manual_id,
        "end_id": end_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDelegationAvailability:
    """USER-05: availability toggle with delegate."""

    async def test_set_unavailable_with_delegate(
        self, async_client: AsyncClient, db_session, admin_user
    ):
        """Setting unavailable requires a delegate and returns updated state."""
        user_a = await _create_user(db_session, "deleg_user_a")
        delegate_b = await _create_user(db_session, "deleg_user_b")
        token_a = _token(user_a)

        resp = await async_client.put(
            "/api/v1/users/me/availability",
            json={"is_available": False, "delegate_id": str(delegate_b.id)},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_available"] is False
        assert data["delegate_id"] == str(delegate_b.id)

    async def test_set_available_again(
        self, async_client: AsyncClient, db_session, admin_user
    ):
        """User can mark themselves available again, clearing delegate."""
        user_a = await _create_user(db_session, "avail_user_a")
        delegate_b = await _create_user(db_session, "avail_user_b")
        token_a = _token(user_a)

        # Set unavailable first
        await async_client.put(
            "/api/v1/users/me/availability",
            json={"is_available": False, "delegate_id": str(delegate_b.id)},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        # Set available again
        resp = await async_client.put(
            "/api/v1/users/me/availability",
            json={"is_available": True},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_available"] is True
        assert data["delegate_id"] is None

    async def test_cannot_delegate_to_self(
        self, async_client: AsyncClient, db_session, admin_user
    ):
        """Cannot set self as delegate."""
        user_a = await _create_user(db_session, "selfdeleg_user")
        token_a = _token(user_a)

        resp = await async_client.put(
            "/api/v1/users/me/availability",
            json={"is_available": False, "delegate_id": str(user_a.id)},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 400

    async def test_unavailable_requires_delegate(
        self, async_client: AsyncClient, db_session, admin_user
    ):
        """Setting unavailable without delegate_id returns 400."""
        user_a = await _create_user(db_session, "nodeleg_user")
        token_a = _token(user_a)

        resp = await async_client.put(
            "/api/v1/users/me/availability",
            json={"is_available": False},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 400


class TestDelegationRouting:
    """INBOX-08: work items auto-route to delegate when user is unavailable."""

    async def test_delegation_routing(
        self, async_client: AsyncClient, db_session, admin_user, admin_token
    ):
        """When user A is unavailable, new work items go to delegate B."""
        user_a = await _create_user(db_session, "route_user_a")
        delegate_b = await _create_user(db_session, "route_user_b")
        token_a = _token(user_a)
        token_b = _token(delegate_b)

        # Set user A unavailable with delegate B
        resp = await async_client.put(
            "/api/v1/users/me/availability",
            json={"is_available": False, "delegate_id": str(delegate_b.id)},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 200

        # Create template targeting user A
        tmpl = await _create_installed_template(
            async_client, admin_token, str(user_a.id)
        )

        # Start workflow
        resp = await async_client.post(
            "/api/v1/workflows",
            json={"template_id": tmpl["template_id"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        wf_id = resp.json()["data"]["id"]

        # Delegate B should have the work item
        resp = await async_client.get(
            "/api/v1/inbox",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 200
        items_b = resp.json()["data"]
        assert len(items_b) >= 1, "Delegate B should have work item"

        # User A should NOT have the item
        resp = await async_client.get(
            "/api/v1/inbox",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 200
        items_a = resp.json()["data"]
        assert len(items_a) == 0, "Unavailable user A should have no items"

        # Verify audit trail contains delegation record
        resp = await async_client.get(
            "/api/v1/audit?action_type=work_item_delegated",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        audit_records = resp.json()["data"]
        assert len(audit_records) >= 1

    async def test_delegation_does_not_affect_existing_items(
        self, async_client: AsyncClient, db_session, admin_user, admin_token
    ):
        """Existing items are not reassigned when user becomes unavailable."""
        user_a = await _create_user(db_session, "existing_user_a")
        delegate_b = await _create_user(db_session, "existing_user_b")
        token_a = _token(user_a)

        # Create template targeting user A and start workflow while A is available
        tmpl = await _create_installed_template(
            async_client, admin_token, str(user_a.id)
        )
        resp = await async_client.post(
            "/api/v1/workflows",
            json={"template_id": tmpl["template_id"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201

        # User A should have the item now
        resp = await async_client.get(
            "/api/v1/inbox",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1, "User A should have existing item"

        # Now set A unavailable
        await async_client.put(
            "/api/v1/users/me/availability",
            json={"is_available": False, "delegate_id": str(delegate_b.id)},
            headers={"Authorization": f"Bearer {token_a}"},
        )

        # User A should STILL have the existing item (not reassigned)
        resp = await async_client.get(
            "/api/v1/inbox",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1, "Existing item should not be reassigned"
