"""Contract Approval workflow seed script.

Creates a 7-step contract approval template and executes it end-to-end.
Demonstrates sequential, parallel, conditional routing, reject flows,
and auto activities (Digital Signing, Archival).

Run: python -m scripts.seed_contract_approval
Requires: FastAPI server running at http://localhost:8000 with admin/admin123 user.
"""

import asyncio
import sys

import httpx

BASE_URL = "http://localhost:8000/api/v1"


async def login(client: httpx.AsyncClient, username: str, password: str) -> dict:
    """Login and return headers with Bearer token."""
    resp = await client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    resp.raise_for_status()
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_test_users(
    client: httpx.AsyncClient, headers: dict
) -> dict[str, str]:
    """Create 4 test users for the contract approval workflow.

    Returns dict mapping username -> user_id.
    """
    users: dict[str, str] = {}
    for uname in ["drafter", "lawyer", "accountant", "director"]:
        try:
            resp = await client.post(
                "/users/",
                json={
                    "username": uname,
                    "password": f"{uname}123",
                    "is_active": True,
                },
                headers=headers,
            )
            if resp.status_code in (200, 201):
                users[uname] = resp.json()["data"]["id"]
                print(f"  Created user: {uname}")
            elif resp.status_code == 400 and "already" in resp.text.lower():
                # User exists -- fetch by listing
                list_resp = await client.get("/users/", headers=headers)
                list_resp.raise_for_status()
                for u in list_resp.json()["data"]:
                    if u["username"] == uname:
                        users[uname] = u["id"]
                        print(f"  Found existing user: {uname}")
                        break
            else:
                print(f"  Warning: unexpected status {resp.status_code} for {uname}")
        except Exception as e:
            print(f"  Warning: {uname}: {e}")
    return users


async def create_contract_template(
    client: httpx.AsyncClient, headers: dict, users: dict[str, str]
) -> tuple[str, dict[str, str]]:
    """Create the 7-step contract approval template.

    Returns (template_id, activity_name_to_id_map).
    """
    # Create template
    resp = await client.post(
        "/templates/",
        json={
            "name": "Contract Approval",
            "description": (
                "7-step contract approval workflow with sequential, parallel, "
                "conditional routing, reject flows, and auto activities"
            ),
        },
        headers=headers,
    )
    resp.raise_for_status()
    template_id = resp.json()["data"]["id"]
    print(f"  Template created: {template_id}")

    # Add 8 activities (start + 4 manual + 2 auto + end)
    activities: dict[str, str] = {}
    activity_defs = [
        {"name": "Initiate", "activity_type": "start"},
        {
            "name": "Draft Contract",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": users.get("drafter", ""),
        },
        {
            "name": "Legal Review",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": users.get("lawyer", ""),
        },
        {
            "name": "Financial Review",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": users.get("accountant", ""),
        },
        {
            "name": "Director Approval",
            "activity_type": "manual",
            "performer_type": "user",
            "performer_id": users.get("director", ""),
            "routing_type": "performer_chosen",
        },
        {
            "name": "Digital Signing",
            "activity_type": "auto",
            "method_name": "send_email",
        },
        {
            "name": "Archival",
            "activity_type": "auto",
            "method_name": "change_lifecycle_state",
        },
        {"name": "End", "activity_type": "end"},
    ]
    for adef in activity_defs:
        resp = await client.post(
            f"/templates/{template_id}/activities", json=adef, headers=headers
        )
        resp.raise_for_status()
        activities[adef["name"]] = resp.json()["data"]["id"]
        print(f"    Activity: {adef['name']} ({adef['activity_type']})")

    # Add process variables
    variable_defs = [
        {"name": "signed", "variable_type": "boolean", "bool_value": False},
        {"name": "approval_decision", "variable_type": "string", "string_value": ""},
        {"name": "email_to", "variable_type": "string", "string_value": "legal@company.com"},
        {"name": "email_subject", "variable_type": "string", "string_value": "Contract Signed"},
        {
            "name": "email_body",
            "variable_type": "string",
            "string_value": "The contract has been digitally signed.",
        },
    ]
    for vdef in variable_defs:
        resp = await client.post(
            f"/templates/{template_id}/variables", json=vdef, headers=headers
        )
        resp.raise_for_status()
    print(f"    Added {len(variable_defs)} process variables")

    # Add flows
    flow_defs = [
        # Sequential: Initiate -> Draft Contract
        (activities["Initiate"], activities["Draft Contract"], "normal", None, None),
        # Parallel split: Draft Contract -> Legal Review AND Financial Review
        (activities["Draft Contract"], activities["Legal Review"], "normal", None, None),
        (activities["Draft Contract"], activities["Financial Review"], "normal", None, None),
        # Parallel join: Legal Review -> Director Approval, Financial Review -> Director Approval
        (activities["Legal Review"], activities["Director Approval"], "normal", None, None),
        (activities["Financial Review"], activities["Director Approval"], "normal", None, None),
        # Conditional: Director Approval -> Digital Signing (approved)
        (activities["Director Approval"], activities["Digital Signing"], "normal", None, "Approve"),
        # Reject flow: Director Approval -> Draft Contract (rejected)
        (activities["Director Approval"], activities["Draft Contract"], "reject", None, "Reject"),
        # Sequential: Digital Signing -> Archival -> End
        (activities["Digital Signing"], activities["Archival"], "normal", None, None),
        (activities["Archival"], activities["End"], "normal", None, None),
    ]
    for src, tgt, ftype, cond, label in flow_defs:
        flow_data: dict = {
            "source_activity_id": src,
            "target_activity_id": tgt,
            "flow_type": ftype,
        }
        if cond:
            flow_data["condition_expression"] = cond
        if label:
            flow_data["display_label"] = label
        resp = await client.post(
            f"/templates/{template_id}/flows", json=flow_data, headers=headers
        )
        resp.raise_for_status()
    print(f"    Added {len(flow_defs)} flows")

    # Set Director Approval trigger to AND_JOIN (wait for both reviews)
    resp = await client.put(
        f"/templates/{template_id}/activities/{activities['Director Approval']}",
        json={"trigger_type": "and_join"},
        headers=headers,
    )
    if resp.status_code == 200:
        print("    Set Director Approval trigger to AND_JOIN")

    # Validate and install
    resp = await client.post(f"/templates/{template_id}/validate", headers=headers)
    resp.raise_for_status()
    validation = resp.json()["data"]
    if not validation.get("valid", False):
        print(f"  WARNING: Validation errors: {validation.get('errors', [])}")

    resp = await client.post(f"/templates/{template_id}/install", headers=headers)
    resp.raise_for_status()
    print(f"  Template installed: {template_id}")

    return template_id, activities


async def complete_step(
    client: httpx.AsyncClient,
    username: str,
    password: str | None = None,
    output_variables: dict | None = None,
    selected_path: str | None = None,
) -> None:
    """Login as user, find inbox item, and complete it."""
    if password is None:
        password = f"{username}123"

    user_headers = await login(client, username, password)

    # Get inbox
    inbox_resp = await client.get("/inbox", headers=user_headers)
    inbox_resp.raise_for_status()
    items = inbox_resp.json()["data"]

    if not items:
        print(f"  No inbox items for {username}, retrying...")
        await asyncio.sleep(2)
        inbox_resp = await client.get("/inbox", headers=user_headers)
        inbox_resp.raise_for_status()
        items = inbox_resp.json()["data"]

    if items:
        item_id = items[0]["id"]
        # Acquire first
        await client.post(f"/inbox/{item_id}/acquire", headers=user_headers)
        # Complete
        complete_data: dict = {}
        if output_variables:
            complete_data["output_variables"] = output_variables
        if selected_path:
            complete_data["selected_path"] = selected_path
        resp = await client.post(
            f"/inbox/{item_id}/complete", json=complete_data, headers=user_headers
        )
        resp.raise_for_status()
        print(f"  {username} completed work item")
    else:
        print(f"  WARNING: No inbox items for {username}")


async def main() -> None:
    """Run the full contract approval seed and E2E execution."""
    print("=== Contract Approval Seed Script ===\n")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Step 1: Login as admin
        print("Step 1: Login as admin")
        headers = await login(client, "admin", "admin123")

        # Step 2: Create test users
        print("\nStep 2: Create test users")
        users = await create_test_users(client, headers)
        if len(users) < 4:
            print(f"  WARNING: Only {len(users)}/4 users created")

        # Step 3: Create and install template
        print("\nStep 3: Create contract approval template")
        template_id, activities = await create_contract_template(client, headers, users)

        # Step 4: Start workflow
        print("\nStep 4: Start workflow")
        resp = await client.post(
            "/workflows/", json={"template_id": template_id}, headers=headers
        )
        resp.raise_for_status()
        workflow_id = resp.json()["data"]["id"]
        print(f"  Workflow started: {workflow_id}")

        # Step 5: Execute manual steps
        print("\nStep 5: Execute manual steps")
        await complete_step(client, "drafter")  # Draft Contract
        await complete_step(client, "lawyer")  # Legal Review
        await complete_step(client, "accountant")  # Financial Review
        await complete_step(
            client, "director", selected_path="Approve"
        )  # Director Approval

        # Step 6: Wait for auto activities (Digital Signing, Archival)
        print("\nStep 6: Waiting for auto activities to complete...")
        wf_state = "running"
        for attempt in range(30):
            await asyncio.sleep(2)
            resp = await client.get(f"/workflows/{workflow_id}", headers=headers)
            resp.raise_for_status()
            wf_state = resp.json()["data"]["state"]
            if wf_state == "finished":
                break
            print(f"  Attempt {attempt + 1}: state={wf_state}")
        else:
            print(f"  WARNING: Workflow did not finish after 60s, current state: {wf_state}")

        # Step 7: Verify final state
        print(f"\nStep 7: Verify")
        resp = await client.get(f"/workflows/{workflow_id}", headers=headers)
        resp.raise_for_status()
        wf_state = resp.json()["data"]["state"]
        print(f"  Workflow final state: {wf_state}")

        # Step 8: Verify audit trail
        resp = await client.get("/audit", headers=headers)
        if resp.status_code == 200:
            audit_data = resp.json()
            audit_count = audit_data.get("meta", {}).get("total_count", len(audit_data.get("data", [])))
            print(f"  Audit trail entries: {audit_count}")
        else:
            print(f"  Audit endpoint returned: {resp.status_code}")

        print("\n=== Contract Approval E2E Complete ===")

        if wf_state != "finished":
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
