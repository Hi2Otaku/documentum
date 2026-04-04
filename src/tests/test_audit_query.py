"""Integration tests for audit trail query (AUDIT-05)."""
import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user_via_api(
    client: AsyncClient, admin_token: str, username: str
) -> dict:
    """Create a user via the API (generates audit records)."""
    resp = await client.post(
        "/api/v1/users/",
        json={"username": username, "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return resp.json()["data"]


async def _generate_audit_records(
    client: AsyncClient, admin_token: str
) -> None:
    """Generate several audit records by performing auditable actions."""
    await _create_user_via_api(client, admin_token, f"audit_u1_{uuid.uuid4().hex[:6]}")
    await _create_user_via_api(client, admin_token, f"audit_u2_{uuid.uuid4().hex[:6]}")
    await _create_user_via_api(client, admin_token, f"audit_u3_{uuid.uuid4().hex[:6]}")


# ---------------------------------------------------------------------------
# AUDIT-05: Audit query
# ---------------------------------------------------------------------------


class TestAuditQuery:
    """AUDIT-05: query audit trail with filters."""

    async def test_query_audit_no_filters(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Query audit trail without filters returns records with pagination."""
        await _generate_audit_records(async_client, admin_token)

        resp = await async_client.get(
            "/api/v1/audit",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        meta = resp.json()["meta"]
        assert isinstance(data, list)
        assert len(data) >= 3, "Should have audit records from user creation"
        assert "total_count" in meta

    async def test_query_audit_by_action_type(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Filter by action_type returns only matching records."""
        await _generate_audit_records(async_client, admin_token)

        resp = await async_client.get(
            "/api/v1/audit?action_type=create",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 3
        for record in data:
            assert record["action"] == "create"

    async def test_query_audit_by_user_id(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Filter by user_id returns records by that user."""
        await _generate_audit_records(async_client, admin_token)

        resp = await async_client.get(
            f"/api/v1/audit?user_id={admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        for record in data:
            assert record["user_id"] == str(admin_user.id)

    async def test_query_audit_by_date_range(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Date range filter works."""
        await _generate_audit_records(async_client, admin_token)

        # Use a broad date range that encompasses now
        resp = await async_client.get(
            "/api/v1/audit?date_from=2020-01-01T00:00:00&date_to=2030-12-31T23:59:59",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1

        # Use a date range in the past (no records)
        resp = await async_client.get(
            "/api/v1/audit?date_from=2019-01-01T00:00:00&date_to=2019-12-31T23:59:59",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 0

    async def test_query_audit_pagination(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Pagination works: skip/limit return different records."""
        await _generate_audit_records(async_client, admin_token)

        # First page
        resp1 = await async_client.get(
            "/api/v1/audit?skip=0&limit=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp1.status_code == 200
        page1 = resp1.json()["data"]
        assert len(page1) == 2

        # Second page
        resp2 = await async_client.get(
            "/api/v1/audit?skip=2&limit=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp2.status_code == 200
        page2 = resp2.json()["data"]

        # Pages should contain different records
        page1_ids = {r["id"] for r in page1}
        page2_ids = {r["id"] for r in page2}
        assert page1_ids.isdisjoint(page2_ids), "Different pages should have different records"

    async def test_audit_query_admin_only(
        self, async_client: AsyncClient, regular_token
    ):
        """Non-admin users cannot query audit trail."""
        resp = await async_client.get(
            "/api/v1/audit",
            headers={"Authorization": f"Bearer {regular_token}"},
        )
        assert resp.status_code == 403
