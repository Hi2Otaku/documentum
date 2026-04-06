"""Tests for retention policies, document-policy assignment, legal holds, and deletion blocking."""
import io

import pytest
from httpx import AsyncClient

from app.models.user import User

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _upload_document(client: AsyncClient, token: str, title: str = "Test Doc") -> str:
    """Upload a document and return its ID."""
    resp = await client.post(
        "/api/v1/documents/",
        data={"title": title},
        files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def _create_policy(
    client: AsyncClient,
    token: str,
    name: str = "7-Year Retention",
    days: int = 2555,
    action: str = "archive",
) -> str:
    """Create a retention policy and return its ID."""
    resp = await client.post(
        "/api/v1/retention-policies",
        json={
            "name": name,
            "retention_period_days": days,
            "disposition_action": action,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


# ---------------------------------------------------------------------------
# Retention Policy CRUD
# ---------------------------------------------------------------------------

class TestRetentionPolicyCRUD:
    async def test_create_policy(self, async_client: AsyncClient, admin_token: str):
        resp = await async_client.post(
            "/api/v1/retention-policies",
            json={
                "name": "Legal 7yr",
                "description": "Keep for 7 years",
                "retention_period_days": 2555,
                "disposition_action": "archive",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "Legal 7yr"
        assert data["retention_period_days"] == 2555
        assert data["disposition_action"] == "archive"

    async def test_create_policy_delete_disposition(self, async_client: AsyncClient, admin_token: str):
        resp = await async_client.post(
            "/api/v1/retention-policies",
            json={
                "name": "Short-term",
                "retention_period_days": 90,
                "disposition_action": "delete",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["disposition_action"] == "delete"

    async def test_list_policies(self, async_client: AsyncClient, admin_token: str):
        await _create_policy(async_client, admin_token, "Policy A", 365)
        await _create_policy(async_client, admin_token, "Policy B", 730)

        resp = await async_client.get(
            "/api/v1/retention-policies",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    async def test_get_policy(self, async_client: AsyncClient, admin_token: str):
        policy_id = await _create_policy(async_client, admin_token)
        resp = await async_client.get(
            f"/api/v1/retention-policies/{policy_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == policy_id

    async def test_update_policy(self, async_client: AsyncClient, admin_token: str):
        policy_id = await _create_policy(async_client, admin_token)
        resp = await async_client.put(
            f"/api/v1/retention-policies/{policy_id}",
            json={"name": "Updated Name", "retention_period_days": 3650},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "Updated Name"
        assert data["retention_period_days"] == 3650

    async def test_delete_policy(self, async_client: AsyncClient, admin_token: str):
        policy_id = await _create_policy(async_client, admin_token)
        resp = await async_client.delete(
            f"/api/v1/retention-policies/{policy_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        # Should be gone now (soft-deleted)
        resp = await async_client.get(
            f"/api/v1/retention-policies/{policy_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    async def test_non_admin_cannot_create(self, async_client: AsyncClient, regular_token: str):
        resp = await async_client.post(
            "/api/v1/retention-policies",
            json={"name": "Blocked", "retention_period_days": 30, "disposition_action": "delete"},
            headers={"Authorization": f"Bearer {regular_token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Document-Policy Assignment
# ---------------------------------------------------------------------------

class TestDocumentRetentionAssignment:
    async def test_assign_policy(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)
        policy_id = await _create_policy(async_client, admin_token)

        resp = await async_client.post(
            f"/api/v1/documents/{doc_id}/retention",
            json={"policy_id": policy_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["document_id"] == doc_id
        assert data["policy_id"] == policy_id
        assert data["policy_name"] == "7-Year Retention"

    async def test_remove_assignment(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)
        policy_id = await _create_policy(async_client, admin_token)

        resp = await async_client.post(
            f"/api/v1/documents/{doc_id}/retention",
            json={"policy_id": policy_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        retention_id = resp.json()["data"]["id"]

        resp = await async_client.delete(
            f"/api/v1/documents/{doc_id}/retention/{retention_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    async def test_retention_status_shows_assignment(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)
        policy_id = await _create_policy(async_client, admin_token)

        await async_client.post(
            f"/api/v1/documents/{doc_id}/retention",
            json={"policy_id": policy_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = await async_client.get(
            f"/api/v1/documents/{doc_id}/retention-status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        status_data = resp.json()["data"]
        assert status_data["is_retained"] is True
        assert status_data["is_deletable"] is False
        assert len(status_data["active_retentions"]) == 1


# ---------------------------------------------------------------------------
# Deletion Blocking
# ---------------------------------------------------------------------------

class TestDeletionBlocking:
    async def test_delete_blocked_by_retention(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)
        policy_id = await _create_policy(async_client, admin_token)

        await async_client.post(
            f"/api/v1/documents/{doc_id}/retention",
            json={"policy_id": policy_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = await async_client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 403
        assert "retention" in resp.json()["detail"].lower()

    async def test_delete_allowed_after_retention_removed(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)
        policy_id = await _create_policy(async_client, admin_token)

        resp = await async_client.post(
            f"/api/v1/documents/{doc_id}/retention",
            json={"policy_id": policy_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        retention_id = resp.json()["data"]["id"]

        # Remove retention
        await async_client.delete(
            f"/api/v1/documents/{doc_id}/retention/{retention_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Now delete should work
        resp = await async_client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    async def test_delete_blocked_by_legal_hold(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)

        await async_client.post(
            f"/api/v1/documents/{doc_id}/legal-hold",
            json={"reason": "Pending litigation"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = await async_client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 403
        assert "legal hold" in resp.json()["detail"].lower()

    async def test_delete_allowed_after_hold_released(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)

        resp = await async_client.post(
            f"/api/v1/documents/{doc_id}/legal-hold",
            json={"reason": "Pending litigation"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        hold_id = resp.json()["data"]["id"]

        # Release hold
        await async_client.delete(
            f"/api/v1/documents/{doc_id}/legal-hold/{hold_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Now delete should work
        resp = await async_client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    async def test_document_without_retention_deletable(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)
        resp = await async_client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Legal Holds
# ---------------------------------------------------------------------------

class TestLegalHolds:
    async def test_place_hold(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)
        resp = await async_client.post(
            f"/api/v1/documents/{doc_id}/legal-hold",
            json={"reason": "SEC investigation"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["reason"] == "SEC investigation"
        assert data["released_at"] is None

    async def test_release_hold(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)
        resp = await async_client.post(
            f"/api/v1/documents/{doc_id}/legal-hold",
            json={"reason": "Investigation"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        hold_id = resp.json()["data"]["id"]

        resp = await async_client.delete(
            f"/api/v1/documents/{doc_id}/legal-hold/{hold_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["released_at"] is not None

    async def test_legal_hold_blocks_deletion_even_without_retention(
        self, async_client: AsyncClient, admin_token: str
    ):
        """Legal hold alone (no retention policy) should block deletion."""
        doc_id = await _upload_document(async_client, admin_token)

        await async_client.post(
            f"/api/v1/documents/{doc_id}/legal-hold",
            json={"reason": "Compliance hold"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = await async_client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 403

    async def test_retention_status_shows_hold(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)

        await async_client.post(
            f"/api/v1/documents/{doc_id}/legal-hold",
            json={"reason": "Investigation"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = await async_client.get(
            f"/api/v1/documents/{doc_id}/retention-status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        status_data = resp.json()["data"]
        assert status_data["is_held"] is True
        assert status_data["is_deletable"] is False
        assert len(status_data["active_holds"]) == 1

    async def test_multiple_holds_all_must_release(self, async_client: AsyncClient, admin_token: str):
        doc_id = await _upload_document(async_client, admin_token)

        resp1 = await async_client.post(
            f"/api/v1/documents/{doc_id}/legal-hold",
            json={"reason": "Hold 1"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        hold1_id = resp1.json()["data"]["id"]

        await async_client.post(
            f"/api/v1/documents/{doc_id}/legal-hold",
            json={"reason": "Hold 2"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Release first hold -- should still be blocked
        await async_client.delete(
            f"/api/v1/documents/{doc_id}/legal-hold/{hold1_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = await async_client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 403
