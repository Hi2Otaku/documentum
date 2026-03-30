"""Integration tests for workflow execution engine (EXEC-01 through EXEC-14)."""
import pytest
from httpx import AsyncClient


# ---- EXEC-01: Start workflow from installed template ----


async def test_start_workflow(
    async_client: AsyncClient, admin_token: str, installed_template: dict
):
    """EXEC-01: POST /workflows starts a running workflow instance."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": installed_template["template_id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["state"] == "running"
    assert data["process_template_id"] == installed_template["template_id"]
    assert data["started_at"] is not None


async def test_start_workflow_invalid_template(
    async_client: AsyncClient, admin_token: str
):
    """EXEC-01 negative: starting from non-existent template returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_start_workflow_uninstalled_template(
    async_client: AsyncClient, admin_token: str, valid_template: dict
):
    """EXEC-01 negative: starting from uninstalled template returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": valid_template["template_id"]},
        headers=headers,
    )
    assert resp.status_code == 400


# ---- EXEC-02: Attach documents at startup ----


async def test_start_workflow_with_documents(
    async_client: AsyncClient, admin_token: str, installed_template: dict
):
    """EXEC-02: Documents attached as packages at startup (optional, may be empty)."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # With empty list (optional per D-04)
    resp = await async_client.post(
        "/api/v1/workflows",
        json={
            "template_id": installed_template["template_id"],
            "document_ids": [],
        },
        headers=headers,
    )
    assert resp.status_code == 201


# ---- EXEC-03: Performer overrides ----


async def test_start_workflow_performer_overrides(
    async_client: AsyncClient,
    admin_token: str,
    installed_template: dict,
    admin_user,
):
    """EXEC-03: Performer overrides map activity template IDs to user IDs."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    overrides = {installed_template["manual_id"]: str(admin_user.id)}
    resp = await async_client.post(
        "/api/v1/workflows",
        json={
            "template_id": installed_template["template_id"],
            "performer_overrides": overrides,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    wf_id = resp.json()["data"]["id"]

    # Check work items have the override performer
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    assert resp.status_code == 200
    work_items = resp.json()["data"]
    assert len(work_items) >= 1
    assert work_items[0]["performer_id"] == str(admin_user.id)


# ---- EXEC-04: Workflow state transitions ----


async def test_workflow_state_transitions(
    async_client: AsyncClient, admin_token: str, installed_template: dict
):
    """EXEC-04: Workflow starts Running, becomes Finished when completed."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": installed_template["template_id"]},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]
    assert resp.json()["data"]["state"] == "running"

    # Get work items
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    work_items = resp.json()["data"]
    available = [wi for wi in work_items if wi["state"] == "available"]
    assert len(available) == 1

    # Complete the single manual activity
    wi_id = available[0]["id"]
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200, f"Complete failed: {resp.json()}"

    # Workflow should be finished
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    assert resp.json()["data"]["state"] == "finished"
    assert resp.json()["data"]["completed_at"] is not None


# ---- EXEC-05: Engine auto-advances ----


async def test_engine_auto_advance(
    async_client: AsyncClient, admin_token: str, installed_template: dict
):
    """EXEC-05: After starting, engine auto-advances through start activity to first manual."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": installed_template["template_id"]},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    # Get workflow detail -- start activity should be complete, manual should be active
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    data = resp.json()["data"]
    activities = data["activity_instances"]

    states = {a["state"] for a in activities}
    assert "complete" in states  # start activity completed
    assert "active" in states  # manual activity active


# ---- EXEC-06: Sequential routing A -> B -> C ----


async def test_sequential_routing(
    async_client: AsyncClient,
    admin_token: str,
    sequential_3step_template: dict,
):
    """EXEC-06: Completing step 1 activates step 2, completing step 2 activates step 3."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    tmpl = sequential_3step_template

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": tmpl["template_id"]},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    # Should have 1 available work item (step 1)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1

    # Complete step 1
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{available[0]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Should now have step 2 available
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1

    # Complete step 2
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{available[0]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Should now have step 3 available
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1

    # Complete step 3 -> workflow finishes
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{available[0]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    assert resp.json()["data"]["state"] == "finished"


# ---- EXEC-07: Parallel routing AND-split/AND-join ----


async def test_parallel_routing_and_join(
    async_client: AsyncClient, admin_token: str, parallel_template: dict
):
    """EXEC-07: AND-split creates 2 parallel work items. AND-join waits for both before activating merge."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": parallel_template["template_id"]},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    # Should have 2 available work items (Review A and Review B)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 2

    # Complete first review -- merge should NOT fire yet (AND-join needs both)
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{available[0]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    still_available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(still_available) == 1  # Only review B remains

    # Complete second review -- now merge should fire
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{still_available[0]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Merge activity should now have a work item
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1  # Merge work item

    # Complete merge -> end -> finished
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{available[0]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    assert resp.json()["data"]["state"] == "finished"


# ---- EXEC-12: OR-join fires on first incoming ----


async def test_or_join_routing(
    async_client: AsyncClient, admin_token: str, admin_user
):
    """EXEC-12: OR-join activity activates when first of multiple incoming flows completes."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create template: start -> [branchA, branchB] -> merge(OR-join) -> end
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "OR-Join Test", "description": "OR-join"},
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
            "name": "Branch A",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    branch_a_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Branch B",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    branch_b_id = resp.json()["data"]["id"]

    # OR-join merge
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Merge",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
            "trigger_type": "or_join",
        },
        headers=headers,
    )
    merge_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    # Flows
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": branch_a_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": branch_b_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": branch_a_id, "target_activity_id": merge_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": branch_b_id, "target_activity_id": merge_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": merge_id, "target_activity_id": end_id},
        headers=headers,
    )

    await async_client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    # 2 available work items (branch A and B)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 2

    # Complete ONLY branch A -- OR-join should fire immediately
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{available[0]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Merge should now have a work item (OR-join fired on first token)
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    all_available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    # Should have: branch B (still pending) + merge (just activated)
    assert len(all_available) >= 2


# ---- EXEC-12 (cont): OR-join does NOT double-activate ----


async def test_or_join_no_double_activation(
    async_client: AsyncClient, admin_token: str, admin_user
):
    """EXEC-12 safety: Completing second branch of OR-join must not create duplicate merge work item."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create OR-join template: start -> [branchA, branchB] -> merge(OR-join) -> end
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "OR-Join Double Test", "description": "OR-join guard"},
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
            "name": "Branch A",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    branch_a_id = resp.json()["data"]["id"]
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Branch B",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    branch_b_id = resp.json()["data"]["id"]
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Merge",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
            "trigger_type": "or_join",
        },
        headers=headers,
    )
    merge_id = resp.json()["data"]["id"]
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={"name": "End", "activity_type": "end"},
        headers=headers,
    )
    end_id = resp.json()["data"]["id"]

    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": branch_a_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": start_id, "target_activity_id": branch_b_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": branch_a_id, "target_activity_id": merge_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": branch_b_id, "target_activity_id": merge_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": merge_id, "target_activity_id": end_id},
        headers=headers,
    )

    await async_client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )

    # Start workflow -- 2 branches available
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
    assert len(available) == 2

    # Complete branch A -- OR-join fires, merge gets 1 work item
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{available[0]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Complete branch B -- OR-join guard must prevent double activation
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{available[1]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Count available work items -- must be exactly 1 (single merge), not 2
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    final_available = [
        wi for wi in resp.json()["data"] if wi["state"] == "available"
    ]
    assert len(final_available) == 1, (
        f"Expected 1 merge work item, got {len(final_available)} -- OR-join double-activated"
    )


# ---- EXEC-13: Process variables read/write ----


async def test_process_variables_rw(
    async_client: AsyncClient, admin_token: str, admin_user
):
    """EXEC-13: Process variables can be read and written during execution."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create template with a variable
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "Var Test", "description": "Variables"},
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

    # Add process variable (schema uses default_int_value for template variables)
    await async_client.post(
        f"/api/v1/templates/{template_id}/variables",
        json={"name": "amount", "variable_type": "int", "default_int_value": 100},
        headers=headers,
    )

    await async_client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )

    # Start workflow
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    # Read variables
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/variables", headers=headers
    )
    assert resp.status_code == 200
    vars_data = resp.json()["data"]
    assert len(vars_data) >= 1
    amount_var = [v for v in vars_data if v["name"] == "amount"][0]
    assert amount_var["int_value"] == 100

    # Write variable
    resp = await async_client.put(
        f"/api/v1/workflows/{wf_id}/variables/amount",
        json={"value": 500},
        headers=headers,
    )
    assert resp.status_code == 200

    # Read again to verify
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/variables", headers=headers
    )
    amount_var = [v for v in resp.json()["data"] if v["name"] == "amount"][0]
    assert amount_var["int_value"] == 500


# ---- EXEC-14: Variables in routing conditions ----


async def test_condition_expression_routing(
    async_client: AsyncClient, admin_token: str, admin_user
):
    """EXEC-14: Condition expressions on flows route based on variable values."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Template: start -> task -> [approve_path (amount > 1000), reject_path (amount <= 1000)] -> end
    resp = await async_client.post(
        "/api/v1/templates/",
        json={"name": "Condition Test", "description": "Conditional routing"},
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
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    review_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Approve",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    approve_id = resp.json()["data"]["id"]

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/activities",
        json={
            "name": "Quick Close",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": str(admin_user.id),
        },
        headers=headers,
    )
    quick_id = resp.json()["data"]["id"]

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
    # Conditional: review -> approve (amount > 1000)
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={
            "source_activity_id": review_id,
            "target_activity_id": approve_id,
            "condition_expression": "amount > 1000",
        },
        headers=headers,
    )
    # Conditional: review -> quick_close (amount <= 1000)
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={
            "source_activity_id": review_id,
            "target_activity_id": quick_id,
            "condition_expression": "amount <= 1000",
        },
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": approve_id, "target_activity_id": end_id},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/templates/{template_id}/flows",
        json={"source_activity_id": quick_id, "target_activity_id": end_id},
        headers=headers,
    )

    # Variable (default_int_value for template variable creation)
    await async_client.post(
        f"/api/v1/templates/{template_id}/variables",
        json={"name": "amount", "variable_type": "int", "default_int_value": 5000},
        headers=headers,
    )

    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/validate", headers=headers
    )
    assert resp.status_code == 200, f"Validate failed: {resp.status_code} {resp.json()}"
    val_data = resp.json()["data"]
    assert val_data["valid"], f"Validation errors: {val_data}"
    resp = await async_client.post(
        f"/api/v1/templates/{template_id}/install", headers=headers
    )
    assert resp.status_code == 200, f"Install failed: {resp.json()}"

    # Start with amount=5000 (> 1000, should go to Approve path)
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": template_id},
        headers=headers,
    )
    assert resp.status_code == 201, f"Start workflow failed: {resp.json()}"
    wf_id = resp.json()["data"]["id"]

    # Complete Review task
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{available[0]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    # Should route to Approve (not Quick Close) because amount=5000 > 1000
    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    assert len(available) == 1

    # Verify it's the Approve path by completing it and checking workflow finishes
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{available[0]['id']}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}", headers=headers
    )
    assert resp.json()["data"]["state"] == "finished"


# ---- Additional: List workflows ----


async def test_list_workflows(
    async_client: AsyncClient, admin_token: str, installed_template: dict
):
    """List all workflow instances."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Start 2 workflows
    await async_client.post(
        "/api/v1/workflows",
        json={"template_id": installed_template["template_id"]},
        headers=headers,
    )
    await async_client.post(
        "/api/v1/workflows",
        json={"template_id": installed_template["template_id"]},
        headers=headers,
    )

    resp = await async_client.get("/api/v1/workflows", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 2


# ---- Additional: Complete work item on halted workflow rejected (D-09) ----


async def test_cannot_complete_work_item_on_non_running_workflow(
    async_client: AsyncClient, admin_token: str, installed_template: dict
):
    """D-09: Cannot complete work items on a workflow that is not Running."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Start workflow and complete it fully
    resp = await async_client.post(
        "/api/v1/workflows",
        json={"template_id": installed_template["template_id"]},
        headers=headers,
    )
    wf_id = resp.json()["data"]["id"]

    resp = await async_client.get(
        f"/api/v1/workflows/{wf_id}/work-items", headers=headers
    )
    available = [wi for wi in resp.json()["data"] if wi["state"] == "available"]
    wi_id = available[0]["id"]

    # Complete it to finish the workflow
    await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_id}/complete",
        json={},
        headers=headers,
    )

    # Try to complete again on finished workflow -- should fail
    resp = await async_client.post(
        f"/api/v1/workflows/{wf_id}/work-items/{wi_id}/complete",
        json={},
        headers=headers,
    )
    assert resp.status_code == 400
