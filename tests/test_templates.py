"""Integration tests for workflow template API (TMPL-01 through TMPL-11)."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _create_template(
    client: AsyncClient,
    token: str,
    name: str = "My Workflow",
    description: str = "Test template",
) -> dict:
    """Create a template and return response JSON data."""
    resp = await client.post(
        "/api/v1/templates/",
        json={"name": name, "description": description},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["data"]


async def _add_activity(
    client: AsyncClient,
    token: str,
    template_id: str,
    name: str = "Activity",
    activity_type: str = "manual",
    **kwargs,
) -> dict:
    """Add an activity and return response JSON data."""
    payload = {"name": name, "activity_type": activity_type, **kwargs}
    resp = await client.post(
        f"/api/v1/templates/{template_id}/activities",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["data"] if resp.status_code in (200, 201) else resp.json()


async def _add_flow(
    client: AsyncClient,
    token: str,
    template_id: str,
    source_id: str,
    target_id: str,
    **kwargs,
) -> dict:
    """Add a flow and return the full response."""
    payload = {
        "source_activity_id": source_id,
        "target_activity_id": target_id,
        **kwargs,
    }
    resp = await client.post(
        f"/api/v1/templates/{template_id}/flows",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


# ── TMPL-01: Template CRUD ──────────────────────────────────────────────────


async def test_create_template(async_client: AsyncClient, admin_token: str):
    """POST /templates/ creates a draft template with version 1."""
    data = await _create_template(async_client, admin_token)
    assert data["name"] == "My Workflow"
    assert data["state"] == "draft"
    assert data["version"] == 1
    assert data["is_installed"] is False


async def test_create_template_no_auth(async_client: AsyncClient):
    """POST /templates/ without auth returns 401."""
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "No Auth"},
    )
    assert resp.status_code == 401


async def test_list_templates(async_client: AsyncClient, admin_token: str):
    """GET /templates/ returns paginated list."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    await _create_template(async_client, admin_token, name="Template A")
    await _create_template(async_client, admin_token, name="Template B")

    resp = await async_client.get("/api/v1/templates/", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["meta"]["total_count"] == 2
    assert "page" in body["meta"]


async def test_get_template_detail(async_client: AsyncClient, admin_token: str):
    """GET /templates/{id} returns template with nested activities."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)
    await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Step 1", activity_type="manual",
        performer_type="user", performer_id="u1",
    )

    resp = await async_client.get(
        f"/api/v1/templates/{tmpl['id']}", headers=headers,
    )
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert len(detail["activities"]) == 1
    assert detail["activities"][0]["name"] == "Step 1"


async def test_update_template(async_client: AsyncClient, admin_token: str):
    """PUT /templates/{id} updates template metadata."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    resp = await async_client.put(
        f"/api/v1/templates/{tmpl['id']}",
        json={"name": "Updated"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Updated"


async def test_delete_template(async_client: AsyncClient, admin_token: str):
    """DELETE /templates/{id} soft-deletes; subsequent GET returns 404."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    resp = await async_client.delete(
        f"/api/v1/templates/{tmpl['id']}", headers=headers,
    )
    assert resp.status_code == 200

    resp = await async_client.get(
        f"/api/v1/templates/{tmpl['id']}", headers=headers,
    )
    assert resp.status_code == 404


# ── TMPL-02: Manual Activities ──────────────────────────────────────────────


async def test_add_manual_activity(async_client: AsyncClient, admin_token: str):
    """POST /templates/{id}/activities with manual type stores performer info."""
    tmpl = await _create_template(async_client, admin_token)
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/activities",
        json={
            "name": "Review",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": "user-123",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["performer_type"] == "user"
    assert data["performer_id"] == "user-123"
    assert data["activity_type"] == "manual"


async def test_update_activity(async_client: AsyncClient, admin_token: str):
    """PUT /templates/{id}/activities/{aid} updates an activity."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)
    act = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Original", activity_type="manual",
        performer_type="user", performer_id="u1",
    )

    resp = await async_client.put(
        f"/api/v1/templates/{tmpl['id']}/activities/{act['id']}",
        json={"name": "Renamed"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Renamed"


async def test_delete_activity(async_client: AsyncClient, admin_token: str):
    """DELETE /templates/{id}/activities/{aid} soft-deletes activity."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)
    act = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="ToDelete", activity_type="manual",
        performer_type="user", performer_id="u1",
    )

    resp = await async_client.delete(
        f"/api/v1/templates/{tmpl['id']}/activities/{act['id']}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["is_deleted"] is True


# ── TMPL-03: Auto Activities ────────────────────────────────────────────────


async def test_add_auto_activity(async_client: AsyncClient, admin_token: str):
    """POST /templates/{id}/activities with auto type stores method_name."""
    tmpl = await _create_template(async_client, admin_token)
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/activities",
        json={
            "name": "Send Email",
            "activity_type": "auto",
            "method_name": "send_email",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["method_name"] == "send_email"
    assert data["activity_type"] == "auto"


# ── TMPL-04: Flows (Normal and Reject) ──────────────────────────────────────


async def test_add_normal_flow(async_client: AsyncClient, admin_token: str):
    """POST /templates/{id}/flows creates a normal flow by default."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)
    a1 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Start", activity_type="start",
    )
    a2 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Review", activity_type="manual",
        performer_type="user", performer_id="u1",
    )

    resp = await _add_flow(
        async_client, admin_token, tmpl["id"], a1["id"], a2["id"],
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["flow_type"] == "normal"


async def test_add_reject_flow(async_client: AsyncClient, admin_token: str):
    """POST /templates/{id}/flows with flow_type=reject creates reject flow."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)
    a1 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Review", activity_type="manual",
        performer_type="user", performer_id="u1",
    )
    a2 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Draft", activity_type="manual",
        performer_type="user", performer_id="u2",
    )

    resp = await _add_flow(
        async_client, admin_token, tmpl["id"], a1["id"], a2["id"],
        flow_type="reject",
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["flow_type"] == "reject"


async def test_add_flow_self_loop_rejected(async_client: AsyncClient, admin_token: str):
    """POST /templates/{id}/flows with source == target returns 400."""
    tmpl = await _create_template(async_client, admin_token)
    act = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Loop", activity_type="manual",
        performer_type="user", performer_id="u1",
    )

    resp = await _add_flow(
        async_client, admin_token, tmpl["id"], act["id"], act["id"],
    )
    assert resp.status_code == 400


async def test_update_flow(async_client: AsyncClient, admin_token: str):
    """PUT /templates/{id}/flows/{fid} updates flow type."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)
    a1 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Start", activity_type="start",
    )
    a2 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Review", activity_type="manual",
        performer_type="user", performer_id="u1",
    )
    flow_resp = await _add_flow(
        async_client, admin_token, tmpl["id"], a1["id"], a2["id"],
    )
    flow_id = flow_resp.json()["data"]["id"]

    resp = await async_client.put(
        f"/api/v1/templates/{tmpl['id']}/flows/{flow_id}",
        json={"flow_type": "reject"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["flow_type"] == "reject"


async def test_delete_flow(async_client: AsyncClient, admin_token: str):
    """DELETE /templates/{id}/flows/{fid} soft-deletes a flow."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)
    a1 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Start", activity_type="start",
    )
    a2 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="End", activity_type="end",
    )
    flow_resp = await _add_flow(
        async_client, admin_token, tmpl["id"], a1["id"], a2["id"],
    )
    flow_id = flow_resp.json()["data"]["id"]

    resp = await async_client.delete(
        f"/api/v1/templates/{tmpl['id']}/flows/{flow_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["is_deleted"] is True


# ── TMPL-05: Process Variables ──────────────────────────────────────────────


async def test_add_string_variable(async_client: AsyncClient, admin_token: str):
    """POST /templates/{id}/variables with string type."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/variables",
        json={
            "name": "requester_name",
            "variable_type": "string",
            "default_string_value": "John",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["variable_type"] == "string"
    assert data["string_value"] == "John"


async def test_add_int_variable(async_client: AsyncClient, admin_token: str):
    """POST /templates/{id}/variables with int type."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/variables",
        json={
            "name": "amount",
            "variable_type": "int",
            "default_int_value": 42,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["variable_type"] == "int"
    assert data["int_value"] == 42


async def test_add_boolean_variable(async_client: AsyncClient, admin_token: str):
    """POST /templates/{id}/variables with boolean type."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/variables",
        json={
            "name": "is_urgent",
            "variable_type": "boolean",
            "default_bool_value": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["variable_type"] == "boolean"
    assert data["bool_value"] is True


async def test_add_date_variable(async_client: AsyncClient, admin_token: str):
    """POST /templates/{id}/variables with date type."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/variables",
        json={
            "name": "due_date",
            "variable_type": "date",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["variable_type"] == "date"


async def test_invalid_variable_type(async_client: AsyncClient, admin_token: str):
    """POST /templates/{id}/variables with invalid type returns 422."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/variables",
        json={"name": "bad", "variable_type": "array"},
        headers=headers,
    )
    assert resp.status_code == 422


# ── TMPL-06: Trigger Types ─────────────────────────────────────────────────


async def test_activity_default_trigger_or_join(async_client: AsyncClient, admin_token: str):
    """Activity without explicit trigger_type defaults to or_join."""
    tmpl = await _create_template(async_client, admin_token)
    act = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Step", activity_type="manual",
        performer_type="user", performer_id="u1",
    )
    assert act["trigger_type"] == "or_join"


async def test_activity_and_join_trigger(async_client: AsyncClient, admin_token: str):
    """Activity with trigger_type=and_join stores it correctly."""
    tmpl = await _create_template(async_client, admin_token)
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/activities",
        json={
            "name": "Merge",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": "u1",
            "trigger_type": "and_join",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["trigger_type"] == "and_join"


# ── TMPL-07: Conditional Routing ────────────────────────────────────────────


async def test_flow_with_condition_expression(async_client: AsyncClient, admin_token: str):
    """Flow with simple condition expression stores and returns the dict."""
    tmpl = await _create_template(async_client, admin_token)
    a1 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Start", activity_type="start",
    )
    a2 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Review", activity_type="manual",
        performer_type="user", performer_id="u1",
    )

    condition = {"field": "amount", "operator": ">", "value": 10000}
    resp = await _add_flow(
        async_client, admin_token, tmpl["id"], a1["id"], a2["id"],
        condition_expression=condition,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["condition_expression"] == condition


async def test_flow_with_compound_condition(async_client: AsyncClient, admin_token: str):
    """Flow with compound (all) condition expression is stored correctly."""
    tmpl = await _create_template(async_client, admin_token)
    a1 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Start", activity_type="start",
    )
    a2 = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Legal", activity_type="manual",
        performer_type="user", performer_id="u1",
    )

    condition = {
        "all": [
            {"field": "amount", "operator": ">", "value": 1000},
            {"field": "dept", "operator": "==", "value": "legal"},
        ]
    }
    resp = await _add_flow(
        async_client, admin_token, tmpl["id"], a1["id"], a2["id"],
        condition_expression=condition,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["condition_expression"] == condition


# ── TMPL-08: Validation ─────────────────────────────────────────────────────


async def test_validate_valid_template(
    async_client: AsyncClient, admin_token: str, valid_template: dict,
):
    """POST /templates/{id}/validate on valid template returns valid=true."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tid = valid_template["template_id"]

    resp = await async_client.post(
        f"/api/v1/templates/{tid}/validate", headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["valid"] is True
    assert data["errors"] == []


async def test_validate_missing_start(async_client: AsyncClient, admin_token: str):
    """Validation detects missing start activity."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    # Only add manual + end, no start
    manual = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Review", activity_type="manual",
        performer_type="user", performer_id="u1",
    )
    end = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="End", activity_type="end",
    )
    await _add_flow(
        async_client, admin_token, tmpl["id"], manual["id"], end["id"],
    )

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/validate", headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["valid"] is False
    error_codes = [e["code"] for e in data["errors"]]
    assert "INVALID_START_COUNT" in error_codes


async def test_validate_missing_end(async_client: AsyncClient, admin_token: str):
    """Validation detects missing end activity."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    start = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Start", activity_type="start",
    )
    manual = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Review", activity_type="manual",
        performer_type="user", performer_id="u1",
    )
    await _add_flow(
        async_client, admin_token, tmpl["id"], start["id"], manual["id"],
    )

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/validate", headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["valid"] is False
    error_codes = [e["code"] for e in data["errors"]]
    assert "NO_END_ACTIVITY" in error_codes


async def test_validate_unreachable_activity(async_client: AsyncClient, admin_token: str):
    """Validation detects unreachable (disconnected) activity."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    start = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Start", activity_type="start",
    )
    end = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="End", activity_type="end",
    )
    # Disconnected manual activity -- not connected by any flow from start
    await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Orphan", activity_type="manual",
        performer_type="user", performer_id="u1",
    )
    await _add_flow(
        async_client, admin_token, tmpl["id"], start["id"], end["id"],
    )

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/validate", headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["valid"] is False
    error_codes = [e["code"] for e in data["errors"]]
    assert "UNREACHABLE_ACTIVITY" in error_codes


async def test_validate_missing_performer(async_client: AsyncClient, admin_token: str):
    """Validation detects manual activity without performer_type."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    start = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Start", activity_type="start",
    )
    # Manual activity without performer_type
    manual = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Review", activity_type="manual",
    )
    end = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="End", activity_type="end",
    )
    await _add_flow(
        async_client, admin_token, tmpl["id"], start["id"], manual["id"],
    )
    await _add_flow(
        async_client, admin_token, tmpl["id"], manual["id"], end["id"],
    )

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/validate", headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["valid"] is False
    error_codes = [e["code"] for e in data["errors"]]
    assert "MISSING_PERFORMER" in error_codes


async def test_validate_missing_method(async_client: AsyncClient, admin_token: str):
    """Validation detects auto activity without method_name."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    start = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Start", activity_type="start",
    )
    # Auto activity without method_name
    auto = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="Auto Step", activity_type="auto",
    )
    end = await _add_activity(
        async_client, admin_token, tmpl["id"],
        name="End", activity_type="end",
    )
    await _add_flow(
        async_client, admin_token, tmpl["id"], start["id"], auto["id"],
    )
    await _add_flow(
        async_client, admin_token, tmpl["id"], auto["id"], end["id"],
    )

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/validate", headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["valid"] is False
    error_codes = [e["code"] for e in data["errors"]]
    assert "MISSING_METHOD" in error_codes


async def test_validate_sets_state_to_validated(
    async_client: AsyncClient, admin_token: str, valid_template: dict,
):
    """After successful validation, template state becomes validated."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tid = valid_template["template_id"]

    await async_client.post(
        f"/api/v1/templates/{tid}/validate", headers=headers,
    )

    resp = await async_client.get(
        f"/api/v1/templates/{tid}", headers=headers,
    )
    assert resp.json()["data"]["state"] == "validated"


# ── TMPL-09: Installation ──────────────────────────────────────────────────


async def test_install_validated_template(
    async_client: AsyncClient, admin_token: str, valid_template: dict,
):
    """Validate then install transitions to active + is_installed."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tid = valid_template["template_id"]

    # Validate first
    await async_client.post(
        f"/api/v1/templates/{tid}/validate", headers=headers,
    )

    # Install
    resp = await async_client.post(
        f"/api/v1/templates/{tid}/install", headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["state"] == "active"
    assert data["is_installed"] is True


async def test_install_draft_template_rejected(async_client: AsyncClient, admin_token: str):
    """Install without validating returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = await _create_template(async_client, admin_token)

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/install", headers=headers,
    )
    assert resp.status_code == 400


async def test_install_deprecates_old_version(
    async_client: AsyncClient, admin_token: str, valid_template: dict,
):
    """Installing v2 deprecates v1."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tid_v1 = valid_template["template_id"]

    # Validate + install v1
    await async_client.post(
        f"/api/v1/templates/{tid_v1}/validate", headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{tid_v1}/install", headers=headers,
    )

    # Create new version from v1
    resp = await async_client.post(
        f"/api/v1/templates/{tid_v1}/new-version", headers=headers,
    )
    assert resp.status_code == 201
    tid_v2 = resp.json()["data"]["id"]

    # Validate + install v2
    await async_client.post(
        f"/api/v1/templates/{tid_v2}/validate", headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{tid_v2}/install", headers=headers,
    )

    # Check v1 is deprecated
    resp = await async_client.get(
        f"/api/v1/templates/{tid_v1}", headers=headers,
    )
    assert resp.json()["data"]["state"] == "deprecated"


# ── TMPL-10: Versioning ────────────────────────────────────────────────────


async def test_create_new_version(
    async_client: AsyncClient, admin_token: str, valid_template: dict,
):
    """POST /templates/{id}/new-version creates draft v2."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tid = valid_template["template_id"]

    # Validate + install so it's active
    await async_client.post(
        f"/api/v1/templates/{tid}/validate", headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{tid}/install", headers=headers,
    )

    resp = await async_client.post(
        f"/api/v1/templates/{tid}/new-version", headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["version"] == 2
    assert data["state"] == "draft"


async def test_new_version_has_cloned_activities(
    async_client: AsyncClient, admin_token: str, valid_template: dict,
):
    """New version clones activities with same names but different IDs."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tid = valid_template["template_id"]

    await async_client.post(
        f"/api/v1/templates/{tid}/validate", headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{tid}/install", headers=headers,
    )

    resp = await async_client.post(
        f"/api/v1/templates/{tid}/new-version", headers=headers,
    )
    new_id = resp.json()["data"]["id"]

    # Get the new version detail
    resp = await async_client.get(
        f"/api/v1/templates/{new_id}", headers=headers,
    )
    detail = resp.json()["data"]
    activity_names = {a["name"] for a in detail["activities"]}
    assert "Start" in activity_names
    assert "Review" in activity_names
    assert "End" in activity_names

    # IDs should differ from originals
    new_ids = {a["id"] for a in detail["activities"]}
    original_ids = {valid_template["start_id"], valid_template["manual_id"], valid_template["end_id"]}
    assert new_ids.isdisjoint(original_ids)


async def test_new_version_has_cloned_flows(
    async_client: AsyncClient, admin_token: str, valid_template: dict,
):
    """New version clones flows with different IDs."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tid = valid_template["template_id"]

    await async_client.post(
        f"/api/v1/templates/{tid}/validate", headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{tid}/install", headers=headers,
    )

    resp = await async_client.post(
        f"/api/v1/templates/{tid}/new-version", headers=headers,
    )
    new_id = resp.json()["data"]["id"]

    resp = await async_client.get(
        f"/api/v1/templates/{new_id}", headers=headers,
    )
    detail = resp.json()["data"]
    assert len(detail["flows"]) == 2

    # Flow IDs should differ from originals
    new_flow_ids = {f["id"] for f in detail["flows"]}
    original_flow_ids = {valid_template["flow1_id"], valid_template["flow2_id"]}
    assert new_flow_ids.isdisjoint(original_flow_ids)


# ── TMPL-11: Start/End Activity Types ──────────────────────────────────────


async def test_start_activity_type(async_client: AsyncClient, admin_token: str):
    """POST activity with activity_type=start is accepted."""
    tmpl = await _create_template(async_client, admin_token)
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/activities",
        json={"name": "Start", "activity_type": "start"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["activity_type"] == "start"


async def test_end_activity_type(async_client: AsyncClient, admin_token: str):
    """POST activity with activity_type=end is accepted."""
    tmpl = await _create_template(async_client, admin_token)
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await async_client.post(
        f"/api/v1/templates/{tmpl['id']}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["activity_type"] == "end"


# ── State Transition Tests ──────────────────────────────────────────────────


async def test_edit_validated_resets_to_draft(
    async_client: AsyncClient, admin_token: str, valid_template: dict,
):
    """Modifying a validated template resets state to draft."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tid = valid_template["template_id"]

    # Validate
    await async_client.post(
        f"/api/v1/templates/{tid}/validate", headers=headers,
    )

    # Confirm validated
    resp = await async_client.get(f"/api/v1/templates/{tid}", headers=headers)
    assert resp.json()["data"]["state"] == "validated"

    # Add another activity (edit)
    await async_client.post(
        f"/api/v1/templates/{tid}/activities",
        json={
            "name": "Extra",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": "u1",
        },
        headers=headers,
    )

    # Should be back to draft
    resp = await async_client.get(f"/api/v1/templates/{tid}", headers=headers)
    assert resp.json()["data"]["state"] == "draft"


async def test_cannot_modify_installed_template(
    async_client: AsyncClient, admin_token: str, valid_template: dict,
):
    """Adding activity to installed (active) template returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tid = valid_template["template_id"]

    # Validate + install
    await async_client.post(
        f"/api/v1/templates/{tid}/validate", headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{tid}/install", headers=headers,
    )

    # Try to add activity -- should fail
    resp = await async_client.post(
        f"/api/v1/templates/{tid}/activities",
        json={
            "name": "Illegal",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": "u1",
        },
        headers=headers,
    )
    assert resp.status_code == 400
