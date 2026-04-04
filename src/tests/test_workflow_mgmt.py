"""Integration tests for workflow management (MGMT-01 through MGMT-05)."""
import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper: create and start a workflow
# ---------------------------------------------------------------------------


async def _create_and_start_workflow(
    client: AsyncClient, admin_token: str, admin_user: User, name_suffix: str = ""
) -> dict:
    """Create start -> manual -> end template, install, and start workflow.

    Returns dict with: template_id, workflow_id.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    tname = f"Mgmt Template {uuid.uuid4().hex[:6]}{name_suffix}"

    resp = await client.post(
        "/api/v1/templates/",
        json={"name": tname, "description": "Workflow mgmt test"},
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
            "performer_id": str(admin_user.id),
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

    return {"template_id": template_id, "workflow_id": workflow_id}


# ---------------------------------------------------------------------------
# MGMT-01: Halt
# ---------------------------------------------------------------------------


class TestHaltWorkflow:
    """MGMT-01: halt a running workflow."""

    async def test_halt_running_workflow(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Halting a running workflow sets state to HALTED and suspends work items."""
        setup = await _create_and_start_workflow(
            async_client, admin_token, admin_user
        )
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Halt it
        resp = await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/halt",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["state"] == "halted"

        # Verify work items are SUSPENDED
        resp = await async_client.get(
            f"/api/v1/workflows/{setup['workflow_id']}/work-items",
            headers=headers,
        )
        work_items = resp.json()["data"]
        active_items = [
            wi for wi in work_items if wi["state"] in ("available", "acquired")
        ]
        suspended_items = [wi for wi in work_items if wi["state"] == "suspended"]
        assert len(active_items) == 0, "No active items after halt"
        assert len(suspended_items) >= 1, "Items should be suspended"

    async def test_halt_non_running_fails(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Cannot halt a workflow that is not running."""
        setup = await _create_and_start_workflow(
            async_client, admin_token, admin_user
        )
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Halt first time -- success
        resp = await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/halt", headers=headers
        )
        assert resp.status_code == 200

        # Halt again -- should fail
        resp = await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/halt", headers=headers
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# MGMT-02: Resume
# ---------------------------------------------------------------------------


class TestResumeWorkflow:
    """MGMT-02: resume a halted workflow."""

    async def test_resume_halted_workflow(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Resuming a halted workflow restores state to RUNNING and items to AVAILABLE."""
        setup = await _create_and_start_workflow(
            async_client, admin_token, admin_user
        )
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Halt then resume
        await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/halt", headers=headers
        )
        resp = await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/resume", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["state"] == "running"

        # Work items should be back to AVAILABLE
        resp = await async_client.get(
            f"/api/v1/workflows/{setup['workflow_id']}/work-items", headers=headers
        )
        work_items = resp.json()["data"]
        available_items = [wi for wi in work_items if wi["state"] == "available"]
        assert len(available_items) >= 1, "Items should be restored to available"

    async def test_resume_non_halted_fails(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Cannot resume a workflow that is not halted."""
        setup = await _create_and_start_workflow(
            async_client, admin_token, admin_user
        )
        headers = {"Authorization": f"Bearer {admin_token}"}

        resp = await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/resume", headers=headers
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# MGMT-03: Abort
# ---------------------------------------------------------------------------


class TestAbortWorkflow:
    """MGMT-03: abort a running or halted workflow."""

    async def test_abort_running_workflow(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Aborting a running workflow sets state to FAILED."""
        setup = await _create_and_start_workflow(
            async_client, admin_token, admin_user
        )
        headers = {"Authorization": f"Bearer {admin_token}"}

        resp = await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/abort", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["state"] == "failed"

    async def test_abort_halted_workflow(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Can also abort a halted workflow."""
        setup = await _create_and_start_workflow(
            async_client, admin_token, admin_user
        )
        headers = {"Authorization": f"Bearer {admin_token}"}

        await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/halt", headers=headers
        )
        resp = await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/abort", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["state"] == "failed"


# ---------------------------------------------------------------------------
# MGMT-05: Restart
# ---------------------------------------------------------------------------


class TestRestartWorkflow:
    """MGMT-05: restart a failed workflow."""

    async def test_restart_failed_workflow(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Restarting a failed workflow sets state to DORMANT, clears work items."""
        setup = await _create_and_start_workflow(
            async_client, admin_token, admin_user
        )
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Abort to FAILED
        await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/abort", headers=headers
        )

        # Restart to DORMANT
        resp = await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/restart", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["state"] == "dormant"

        # Work items should be deleted
        resp = await async_client.get(
            f"/api/v1/workflows/{setup['workflow_id']}/work-items", headers=headers
        )
        work_items = resp.json()["data"]
        assert len(work_items) == 0, "Work items should be deleted after restart"

        # Verify workflow detail shows DORMANT with all activities in DORMANT
        resp = await async_client.get(
            f"/api/v1/workflows/{setup['workflow_id']}", headers=headers
        )
        wf = resp.json()["data"]
        assert wf["state"] == "dormant"
        for ai in wf.get("activity_instances", []):
            assert ai["state"] == "dormant"

    async def test_restart_non_failed_fails(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Cannot restart a running workflow."""
        setup = await _create_and_start_workflow(
            async_client, admin_token, admin_user
        )
        headers = {"Authorization": f"Bearer {admin_token}"}

        resp = await async_client.post(
            f"/api/v1/workflows/{setup['workflow_id']}/restart", headers=headers
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# MGMT-04: Filtered listing
# ---------------------------------------------------------------------------


class TestWorkflowAdminList:
    """MGMT-04: admin filtered workflow listing."""

    async def test_list_workflows_filtered(
        self, async_client: AsyncClient, admin_token, admin_user
    ):
        """Filter workflows by state."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create 3 workflows
        s1 = await _create_and_start_workflow(
            async_client, admin_token, admin_user, "_list1"
        )
        s2 = await _create_and_start_workflow(
            async_client, admin_token, admin_user, "_list2"
        )
        s3 = await _create_and_start_workflow(
            async_client, admin_token, admin_user, "_list3"
        )

        # Halt one
        await async_client.post(
            f"/api/v1/workflows/{s2['workflow_id']}/halt", headers=headers
        )
        # Abort another
        await async_client.post(
            f"/api/v1/workflows/{s3['workflow_id']}/abort", headers=headers
        )

        # Filter by running
        resp = await async_client.get(
            "/api/v1/workflows/admin/list?state=running", headers=headers
        )
        assert resp.status_code == 200
        running = resp.json()["data"]
        running_ids = [w["id"] for w in running]
        assert s1["workflow_id"] in running_ids
        assert s2["workflow_id"] not in running_ids

        # Filter by template_id
        resp = await async_client.get(
            f"/api/v1/workflows/admin/list?template_id={s1['template_id']}",
            headers=headers,
        )
        assert resp.status_code == 200
        tmpl_filtered = resp.json()["data"]
        assert len(tmpl_filtered) >= 1
        for w in tmpl_filtered:
            assert w["process_template_id"] == s1["template_id"]

        # No filters
        resp = await async_client.get(
            "/api/v1/workflows/admin/list", headers=headers
        )
        assert resp.status_code == 200
        all_wfs = resp.json()["data"]
        assert len(all_wfs) >= 3


# ---------------------------------------------------------------------------
# Admin-only enforcement
# ---------------------------------------------------------------------------


class TestAdminOnlyEnforcement:
    """MGMT-01-05: admin-only enforcement on management endpoints."""

    async def test_admin_only_enforcement(
        self, async_client: AsyncClient, admin_token, admin_user, regular_token
    ):
        """Non-admin users get 403 for halt/resume/abort/restart."""
        setup = await _create_and_start_workflow(
            async_client, admin_token, admin_user
        )
        headers = {"Authorization": f"Bearer {regular_token}"}
        wf_id = setup["workflow_id"]

        resp = await async_client.post(
            f"/api/v1/workflows/{wf_id}/halt", headers=headers
        )
        assert resp.status_code == 403

        resp = await async_client.post(
            f"/api/v1/workflows/{wf_id}/resume", headers=headers
        )
        assert resp.status_code == 403

        resp = await async_client.post(
            f"/api/v1/workflows/{wf_id}/abort", headers=headers
        )
        assert resp.status_code == 403

        resp = await async_client.post(
            f"/api/v1/workflows/{wf_id}/restart", headers=headers
        )
        assert resp.status_code == 403

        # Admin list also restricted
        resp = await async_client.get(
            "/api/v1/workflows/admin/list", headers=headers
        )
        assert resp.status_code == 403
