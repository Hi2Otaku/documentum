"""Tests for process analytics endpoints."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import (
    ActivityInstance,
    ActivityTemplate,
    ProcessTemplate,
    WorkflowInstance,
)
from app.models.enums import (
    ActivityState,
    ActivityType,
    ProcessState,
    WorkflowState,
)


@pytest.fixture
async def analytics_data(db_session: AsyncSession):
    """Create completed workflow instances with activity instances for analytics testing."""
    now = datetime.now(timezone.utc)

    # Create a process template
    template = ProcessTemplate(
        id=uuid.uuid4(),
        name="Analytics Test Template",
        version=1,
        state=ProcessState.ACTIVE,
        is_installed=True,
        template_family_id=uuid.uuid4(),
    )
    db_session.add(template)
    await db_session.flush()

    # Create activity templates
    start_at = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=template.id,
        name="Start",
        activity_type=ActivityType.START,
    )
    review_at = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=template.id,
        name="Review",
        activity_type=ActivityType.MANUAL,
    )
    approve_at = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=template.id,
        name="Approve",
        activity_type=ActivityType.MANUAL,
    )
    end_at = ActivityTemplate(
        id=uuid.uuid4(),
        process_template_id=template.id,
        name="End",
        activity_type=ActivityType.END,
    )
    db_session.add_all([start_at, review_at, approve_at, end_at])
    await db_session.flush()

    # Create two completed workflow instances
    for i in range(2):
        wf_start = now - timedelta(hours=10 - i)
        wf_end = now - timedelta(hours=5 - i)

        wf = WorkflowInstance(
            id=uuid.uuid4(),
            process_template_id=template.id,
            state=WorkflowState.FINISHED,
            started_at=wf_start,
            completed_at=wf_end,
        )
        db_session.add(wf)
        await db_session.flush()

        # Activity instances: Start -> Review -> Approve -> End
        activities = [
            (start_at, 0, 1),    # 1 minute
            (review_at, 1, 60),  # 59 minutes
            (approve_at, 60, 180),  # 120 minutes
            (end_at, 180, 181),  # 1 minute
        ]
        for at, start_offset_min, end_offset_min in activities:
            ai = ActivityInstance(
                id=uuid.uuid4(),
                workflow_instance_id=wf.id,
                activity_template_id=at.id,
                state=ActivityState.COMPLETE,
                started_at=wf_start + timedelta(minutes=start_offset_min),
                completed_at=wf_start + timedelta(minutes=end_offset_min),
            )
            db_session.add(ai)

    await db_session.commit()
    return {"template_id": str(template.id)}


@pytest.mark.asyncio
async def test_analytics_paths(
    async_client: AsyncClient, admin_token: str, analytics_data: dict
):
    """GET /api/v1/analytics/paths returns discovered execution paths."""
    resp = await async_client.get(
        "/api/v1/analytics/paths",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check shape
    first = data[0]
    assert "path" in first
    assert "frequency" in first
    assert isinstance(first["path"], list)
    assert first["frequency"] >= 1


@pytest.mark.asyncio
async def test_analytics_cycle_times_by_activity(
    async_client: AsyncClient, admin_token: str, analytics_data: dict
):
    """GET /api/v1/analytics/cycle-times returns per-activity cycle time stats."""
    resp = await async_client.get(
        "/api/v1/analytics/cycle-times",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert "activity_name" in first
    assert "avg_seconds" in first
    assert "sample_count" in first
    assert first["sample_count"] >= 1


@pytest.mark.asyncio
async def test_analytics_cycle_times_by_template(
    async_client: AsyncClient, admin_token: str, analytics_data: dict
):
    """GET /api/v1/analytics/cycle-times?group_by=template returns template-grouped results."""
    resp = await async_client.get(
        "/api/v1/analytics/cycle-times?group_by=template",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert "template_name" in first
    assert first["template_name"] == "Analytics Test Template"


@pytest.mark.asyncio
async def test_analytics_bottlenecks(
    async_client: AsyncClient, admin_token: str, analytics_data: dict
):
    """GET /api/v1/analytics/bottlenecks returns activities ranked by duration."""
    resp = await async_client.get(
        "/api/v1/analytics/bottlenecks",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert "activity_name" in first
    assert "avg_duration_seconds" in first
    assert "total_executions" in first
    assert "pct_of_total_time" in first
    # Approve should be the top bottleneck (120 min avg)
    assert first["activity_name"] == "Approve"


@pytest.mark.asyncio
async def test_analytics_summary(
    async_client: AsyncClient, admin_token: str, analytics_data: dict
):
    """GET /api/v1/analytics/summary returns high-level summary."""
    resp = await async_client.get(
        "/api/v1/analytics/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_instances"] >= 2
    assert data["completed_instances"] >= 2
    assert data["paths_discovered"] >= 1


@pytest.mark.asyncio
async def test_analytics_refresh(
    async_client: AsyncClient, admin_token: str, analytics_data: dict, monkeypatch
):
    """POST /api/v1/analytics/refresh triggers cache refresh."""
    # Mock Redis to avoid connection errors in test
    async def mock_refresh(db):
        pass  # no-op for test

    monkeypatch.setattr(
        "app.routers.analytics.refresh_analytics_cache", mock_refresh
    )

    resp = await async_client.post(
        "/api/v1/analytics/refresh",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "refreshed"


@pytest.mark.asyncio
async def test_analytics_non_admin_forbidden(
    async_client: AsyncClient, regular_token: str, analytics_data: dict
):
    """Non-admin users get 403 on all analytics endpoints."""
    headers = {"Authorization": f"Bearer {regular_token}"}

    for path in [
        "/api/v1/analytics/paths",
        "/api/v1/analytics/cycle-times",
        "/api/v1/analytics/bottlenecks",
        "/api/v1/analytics/summary",
    ]:
        resp = await async_client.get(path, headers=headers)
        assert resp.status_code == 403, f"Expected 403 for {path}, got {resp.status_code}"

    resp = await async_client.post("/api/v1/analytics/refresh", headers=headers)
    assert resp.status_code == 403
