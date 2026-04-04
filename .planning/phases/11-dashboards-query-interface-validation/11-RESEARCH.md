# Phase 11: Dashboards, Query Interface & Validation - Research

**Researched:** 2026-04-04
**Domain:** Real-time dashboards (SSE + Recharts), admin query interface, E2E seed script
**Confidence:** HIGH

## Summary

Phase 11 spans three distinct work areas: (1) a BAM dashboard with real-time KPI cards and charts, (2) a form-based admin query interface for workflows/work items/documents, and (3) a contract approval seed script that proves the entire system works end-to-end. All three build on well-established patterns already present in the codebase -- the audit query pattern for filters, the Celery beat pattern for periodic tasks, and the existing frontend SPA architecture.

The backend work is straightforward: new dashboard service with aggregation queries, SSE endpoint using FastAPI's built-in `EventSourceResponse`, a Celery beat task for pre-aggregating chart data, three query endpoints following the existing audit query pattern, and an Alembic migration for the `expected_duration_hours` field on ActivityTemplate plus a metrics summary table. The frontend adds two new pages (dashboard, query) using Recharts for charts and @tanstack/react-table for result tables. The seed script is a standalone Python module that calls existing REST APIs.

**Primary recommendation:** Follow the existing router-service-model async pattern. Use FastAPI's built-in `EventSourceResponse` (available since 0.135.0) for SSE. Use Recharts 2.x as specified in CLAUDE.md. The seed script should use httpx to call REST APIs directly, making it both a validation tool and documentation of API usage.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** KPI cards + charts layout. Top row of summary cards (running/halted/finished/failed counts, average completion time per template). Below: two-column chart area with bottleneck chart (bar chart showing avg duration per activity) and workload by user (bar chart showing assigned/completed/pending). Bottom section for SLA compliance visualization.
- **D-02:** SLA measured per-activity via optional `expected_duration_hours` field on activity templates. SLA compliance % = work items completed within the configured time limit. Activities without a time limit are excluded from SLA calculations.
- **D-03:** Template dropdown filter on dashboard. Default view shows all templates combined. Dropdown lets admin filter to a specific template -- all KPIs and charts update accordingly.
- **D-04:** SSE (Server-Sent Events) for live dashboard updates. FastAPI `StreamingResponse` endpoint pushes data when workflow state changes. Backed by PostgreSQL LISTEN/NOTIFY to detect state changes without polling.
- **D-05:** Hybrid metrics computation. KPI counts (running/halted/finished/failed) computed on-the-fly from live queries -- always accurate. Chart data (bottleneck analysis, trends, workload aggregation) pre-aggregated by a Celery beat task into a summary table at regular intervals.
- **D-06:** Form-based filter panel with structured dropdowns and date pickers. Three tabs: Workflows, Work Items, Documents. Each tab has entity-specific filters.
- **D-07:** Results displayed in sortable, paginated tables (using @tanstack/react-table). Clickable rows navigate to detail views.
- **D-08:** Python seed script that calls backend REST APIs to create the full 7-step contract approval template. Runs as `python -m scripts.seed_contract_approval`.
- **D-09:** The 7 steps: (1) Initiate, (2) Draft Contract, (3) Parallel Legal + Financial Review, (4) Director Approval (conditional), (5) Digital Signing (auto), (6) Archival (auto), (7) End.
- **D-10:** Simulated auto-activity actions. Digital signing sets process variable. Archival triggers lifecycle transition.
- **D-11:** Full demo run -- seed script creates 4 test users, starts workflow, auto-completes all steps, produces finished workflow with audit trail.

### Claude's Discretion
- Recharts chart types and styling details (bar vs horizontal bar, color scheme)
- SSE endpoint implementation details (event format, reconnection strategy)
- Celery beat interval for pre-aggregated metrics (e.g., every 5 minutes)
- Summary table schema for pre-aggregated chart data
- Detail view layout and information hierarchy
- Seed script error handling and idempotency approach
- Exact filter field components (combobox vs dropdown for user/template pickers)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BAM-01 | Dashboard shows count of running, halted, finished, and failed workflows | Live KPI queries against WorkflowInstance.state with GROUP BY |
| BAM-02 | Dashboard shows average completion time per workflow template | AVG(completed_at - started_at) grouped by process_template_id |
| BAM-03 | Dashboard identifies bottleneck activities (longest average duration) | AVG(completed_at - started_at) on ActivityInstance joined with ActivityTemplate |
| BAM-04 | Dashboard shows workload per user (tasks assigned, completed, pending) | COUNT on WorkItem grouped by performer_id and state |
| BAM-05 | Dashboard shows SLA compliance rate | Compare WorkItem completion time against ActivityTemplate.expected_duration_hours |
| QUERY-01 | Admin can query workflow instances by template, state, date range, performer | Extend existing audit query pattern with condition-based WHERE clauses |
| QUERY-02 | Admin can query work items by assignee, state, workflow, priority | Same pattern, joining WorkItem with ActivityInstance for workflow_id |
| QUERY-03 | Admin can query documents by metadata, lifecycle state, version | Filter on Document model fields including lifecycle_state and metadata JSON |
| EXAMPLE-01 | Pre-built contract approval template matching 7-step spec | Seed script creates template via REST API with all 7 activities and flows |
| EXAMPLE-02 | Example demonstrates sequential, parallel, conditional, reject, auto routing | Template graph covers all routing types; seed script exercises each path |
| EXAMPLE-03 | Example executed E2E with test users, producing complete audit trail | Seed script creates users, starts workflow, completes all steps, verifies audit |
</phase_requirements>

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.x | HTTP API + SSE via built-in EventSourceResponse | Built-in SSE support since 0.135.0, no extra dependency needed |
| SQLAlchemy | 2.0.48 | ORM for aggregation queries | Already in use; func.count, func.avg, GROUP BY for metrics |
| Celery | 5.6.x | Beat scheduler for metrics pre-aggregation | Already configured with beat_schedule in celery_app.py |
| Recharts | 2.x | Dashboard charts (BarChart, gauge-like display) | Specified in CLAUDE.md tech stack |
| @tanstack/react-table | 8.21.x | Query results tables with sort/filter/pagination | Specified in CLAUDE.md tech stack |
| @tanstack/react-query | 5.96.x | Data fetching and SSE integration | Already installed in frontend |

### New Dependencies to Install
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| recharts | ^2.15.x | Dashboard charts | Frontend: npm install recharts |
| @tanstack/react-table | ^8.21.x | Sortable paginated tables | Frontend: npm install @tanstack/react-table |

**Note on Recharts version:** CLAUDE.md specifies Recharts 2.x. The latest stable in the 2.x line should be used. Recharts 3.x exists but would contradict the project spec.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Built-in EventSourceResponse | sse-starlette | Extra dependency; FastAPI 0.135+ includes SSE natively |
| Recharts BarChart | Recharts Treemap | Bar charts are more readable for bottleneck/workload data |
| Celery beat for aggregation | Materialized views | Materialized views require PostgreSQL-specific SQL; Celery beat is already set up and DB-agnostic for tests |

**Installation:**
```bash
cd frontend && npm install recharts @tanstack/react-table
```

## Architecture Patterns

### Recommended Project Structure (New Files)
```
src/app/
  routers/
    dashboard.py          # GET /dashboard/metrics, GET /dashboard/stream (SSE)
    query.py              # GET /query/workflows, /query/work-items, /query/documents
  services/
    dashboard_service.py  # Aggregation queries, metrics computation
    query_service.py      # Filtered queries for all three entity types
  tasks/
    metrics_aggregation.py  # Celery beat task for pre-aggregated chart data
  models/
    metrics.py            # MetricsSummary model for pre-aggregated data

frontend/src/
  pages/
    DashboardPage.tsx     # KPI cards + charts layout
    QueryPage.tsx         # Three-tab query interface
  api/
    dashboard.ts          # Dashboard API client + SSE hook
    query.ts              # Query API client
  components/
    dashboard/
      KpiCards.tsx        # Summary cards row
      BottleneckChart.tsx # Bar chart for activity durations
      WorkloadChart.tsx   # Bar chart for user workload
      SlaChart.tsx        # SLA compliance visualization
    query/
      WorkflowQueryTab.tsx
      WorkItemQueryTab.tsx
      DocumentQueryTab.tsx
      QueryResultTable.tsx  # Shared @tanstack/react-table wrapper

scripts/
  seed_contract_approval.py  # CLI seed script
```

### Pattern 1: Dashboard Metrics Service (Live KPIs)
**What:** Service functions that execute aggregation queries for real-time KPI data
**When to use:** For KPI counts that must always be accurate (running/halted/finished/failed counts)
**Example:**
```python
# Source: Follows existing audit.py query pattern
from sqlalchemy import func, select, case
from app.models.workflow import WorkflowInstance, ActivityInstance, WorkItem
from app.models.enums import WorkflowState

async def get_workflow_counts(db: AsyncSession, template_id: uuid.UUID | None = None):
    """Get counts of workflows by state."""
    conditions = []
    if template_id:
        conditions.append(WorkflowInstance.process_template_id == template_id)
    
    stmt = select(
        WorkflowInstance.state,
        func.count(WorkflowInstance.id),
    ).group_by(WorkflowInstance.state)
    
    if conditions:
        stmt = stmt.where(*conditions)
    
    result = await db.execute(stmt)
    return {row[0].value: row[1] for row in result.all()}
```

### Pattern 2: SSE Endpoint with EventSourceResponse
**What:** Server-Sent Events endpoint using FastAPI's built-in support
**When to use:** For pushing real-time dashboard updates to connected clients
**Example:**
```python
# Source: FastAPI official docs (fastapi.tiangolo.com/tutorial/server-sent-events/)
from collections.abc import AsyncIterable
from fastapi import Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

@router.get("/stream", response_class=EventSourceResponse)
async def dashboard_stream(
    template_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> AsyncIterable[ServerSentEvent]:
    """SSE stream for live dashboard updates."""
    while True:
        metrics = await dashboard_service.get_kpi_metrics(db, template_id)
        yield ServerSentEvent(
            data=metrics,
            event="metrics_update",
        )
        await asyncio.sleep(5)  # Poll interval; PostgreSQL LISTEN/NOTIFY can replace
```

### Pattern 3: Query Endpoint (Extending Audit Pattern)
**What:** Condition-based filtered queries with pagination
**When to use:** For all three query tabs (workflows, work items, documents)
**Example:**
```python
# Source: Existing src/app/routers/audit.py pattern
@router.get("/workflows", response_model=EnvelopeResponse[list[WorkflowQueryResponse]])
async def query_workflows(
    template_id: uuid.UUID | None = Query(None),
    state: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    started_by: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    conditions = []
    if template_id:
        conditions.append(WorkflowInstance.process_template_id == template_id)
    if state:
        conditions.append(WorkflowInstance.state == state)
    if date_from:
        conditions.append(WorkflowInstance.created_at >= date_from)
    if date_to:
        conditions.append(WorkflowInstance.created_at <= date_to)
    if started_by:
        conditions.append(WorkflowInstance.supervisor_id == started_by)
    
    # Count + paginate (same as audit.py)
    ...
```

### Pattern 4: Celery Beat Pre-Aggregation Task
**What:** Periodic task that computes chart data and stores in summary table
**When to use:** For bottleneck analysis, workload aggregation, trend data
**Example:**
```python
# Source: Follows existing app/tasks/auto_activity.py pattern
@celery_app.task(name="app.tasks.metrics_aggregation.aggregate_dashboard_metrics")
def aggregate_dashboard_metrics():
    """Periodic task: pre-aggregate chart data into metrics_summary table."""
    asyncio.run(_aggregate_async())

async def _aggregate_async():
    from app.core.database import async_session_factory
    async with async_session_factory() as session:
        # Compute bottleneck data, workload, SLA metrics
        # Upsert into MetricsSummary table
        ...
        await session.commit()
```

### Pattern 5: Seed Script via REST API
**What:** Python script that creates full contract approval template + runs E2E demo
**When to use:** For the EXAMPLE-01/02/03 requirements
**Example:**
```python
# scripts/seed_contract_approval.py
import httpx
import asyncio

BASE_URL = "http://localhost:8000/api/v1"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # 1. Login as admin
        resp = await client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        token = resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Create test users (drafter, lawyer, accountant, director)
        # 3. Create template with 7 activities
        # 4. Add flows (sequential, parallel split, conditional)
        # 5. Validate and install
        # 6. Start workflow instance
        # 7. Complete each step in order
        # 8. Verify final state and audit trail
```

### Anti-Patterns to Avoid
- **Polling from frontend for dashboard data:** Use SSE instead of setInterval + fetch. The EventSource API handles reconnection automatically.
- **Computing all metrics on every SSE push:** Split into live (KPI counts) and pre-aggregated (charts). KPIs are cheap queries; chart aggregations should run on Celery beat schedule.
- **Seed script using direct DB access:** Use REST APIs so the script also validates API contracts. This makes it a true E2E test.
- **Putting all query logic in routers:** Keep the router thin (parameter parsing, HTTP mapping). Move query building to service layer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE protocol formatting | Manual "data: ...\n\n" string formatting | FastAPI EventSourceResponse | Handles encoding, content-type headers, keep-alive automatically |
| Data tables with sort/page | Custom table component with sort state | @tanstack/react-table | Headless, handles column sorting, pagination state, filtering |
| Chart rendering | SVG/Canvas chart drawing | Recharts BarChart/PieChart | D3-based, responsive, tooltip/legend built-in |
| SSE reconnection on client | Manual EventSource reconnection logic | Browser EventSource API | Auto-reconnects with exponential backoff by default |
| Pagination math | Custom skip/limit calculations | Existing EnvelopeResponse + PaginationMeta | Already established in 12+ endpoints |

## Common Pitfalls

### Pitfall 1: SQLite Limitations in Tests for Aggregation Queries
**What goes wrong:** SQLite doesn't support `EXTRACT(EPOCH FROM ...)` or PostgreSQL-specific date arithmetic used in AVG completion time queries.
**Why it happens:** Tests use aiosqlite in-memory DB. Complex date functions differ between SQLite and PostgreSQL.
**How to avoid:** Use `func.julianday()` for SQLite or write DB-agnostic duration calculations. Alternatively, compute duration in Python after fetching raw timestamps. The project already handles dialect differences (see database.py pool_size check).
**Warning signs:** Tests pass locally but aggregation queries return wrong results or errors.

### Pitfall 2: SSE Connection Lifecycle with Database Sessions
**What goes wrong:** SSE endpoint holds a database session open for the lifetime of the connection (potentially hours).
**Why it happens:** The `get_db` dependency yields a session per request, but SSE streams are long-lived.
**How to avoid:** Don't inject `db` via Depends for SSE. Instead, create a new session for each metrics query inside the SSE loop using `async_session_factory()` directly (same pattern as Celery tasks).
**Warning signs:** Database connection pool exhaustion under multiple dashboard viewers.

### Pitfall 3: EventSource API Doesn't Support Auth Headers
**What goes wrong:** Browser's `EventSource` API cannot set custom headers (no Authorization header).
**Why it happens:** The SSE/EventSource spec only allows URL and withCredentials options.
**How to avoid:** Pass the JWT token as a query parameter for the SSE endpoint: `/dashboard/stream?token=xxx`. Validate the token in the endpoint. This is the standard workaround.
**Warning signs:** 401 errors when trying to connect to SSE from the dashboard.

### Pitfall 4: Seed Script Assumes Clean Database
**What goes wrong:** Running seed script twice creates duplicate data or fails on unique constraints.
**Why it happens:** No idempotency check.
**How to avoid:** Check if the contract approval template already exists by name before creating. Use a "find or create" pattern. Print clear messages about what was created vs. skipped.
**Warning signs:** IntegrityError on second run.

### Pitfall 5: expected_duration_hours Migration on Existing Data
**What goes wrong:** Adding non-nullable column to existing activity_templates breaks migration.
**Why it happens:** Existing rows have no value for the new field.
**How to avoid:** Add as nullable (which it should be -- D-02 says "optional"). Activities without a time limit are excluded from SLA calculations.
**Warning signs:** Alembic migration fails with NOT NULL constraint violation.

### Pitfall 6: Recharts 2.x vs 3.x API Differences
**What goes wrong:** Installing recharts@3.x breaks examples written for 2.x API.
**Why it happens:** Recharts 3.x has breaking changes (migration guide exists).
**How to avoid:** Pin to `recharts@^2.15.0` in package.json to stay on 2.x as specified in CLAUDE.md.
**Warning signs:** Import errors or missing component props after install.

## Code Examples

### SSE Dashboard Endpoint (Backend)
```python
# Source: FastAPI SSE docs + project patterns
import asyncio
import json
import uuid
from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.dependencies import get_current_active_admin
from app.models.user import User
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics")
async def get_dashboard_metrics(
    template_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Get current dashboard metrics (one-shot)."""
    return EnvelopeResponse(
        data=await dashboard_service.get_all_metrics(db, template_id)
    )


@router.get("/stream", response_class=EventSourceResponse)
async def dashboard_stream(
    template_id: uuid.UUID | None = Query(None),
    token: str = Query(...),  # JWT passed as query param (EventSource limitation)
) -> AsyncIterable[ServerSentEvent]:
    """SSE stream for live dashboard KPI updates."""
    # Validate token manually (can't use Depends with SSE)
    user = await _validate_sse_token(token)
    
    while True:
        async with async_session_factory() as session:
            metrics = await dashboard_service.get_kpi_metrics(session, template_id)
        yield ServerSentEvent(data=metrics, event="kpi_update")
        await asyncio.sleep(5)
```

### SSE Client Hook (Frontend)
```typescript
// Source: Browser EventSource API + React Query pattern
import { useEffect, useState } from "react";

interface KpiMetrics {
  running: number;
  halted: number;
  finished: number;
  failed: number;
  avg_completion_hours: number;
}

export function useDashboardSSE(templateId?: string): KpiMetrics | null {
  const [metrics, setMetrics] = useState<KpiMetrics | null>(null);
  
  useEffect(() => {
    const token = localStorage.getItem("token");
    const params = new URLSearchParams();
    if (token) params.set("token", token);
    if (templateId) params.set("template_id", templateId);
    
    const es = new EventSource(`/api/v1/dashboard/stream?${params}`);
    
    es.addEventListener("kpi_update", (event) => {
      setMetrics(JSON.parse(event.data));
    });
    
    es.onerror = () => {
      // EventSource auto-reconnects; optionally show connection status
    };
    
    return () => es.close();
  }, [templateId]);
  
  return metrics;
}
```

### Recharts BarChart (Frontend)
```typescript
// Source: Recharts 2.x docs
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";

interface BottleneckData {
  activity_name: string;
  avg_duration_hours: number;
}

export function BottleneckChart({ data }: { data: BottleneckData[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} layout="vertical" margin={{ left: 120 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" label={{ value: "Avg Hours", position: "bottom" }} />
        <YAxis type="category" dataKey="activity_name" width={110} />
        <Tooltip />
        <Bar dataKey="avg_duration_hours" fill="hsl(var(--primary))" />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

### MetricsSummary Model (New Table)
```python
# Source: Project model patterns
class MetricsSummary(BaseModel):
    __tablename__ = "metrics_summary"

    metric_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # e.g., "bottleneck", "workload", "sla"
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("process_templates.id"), nullable=True
    )
    dimension_key: Mapped[str] = mapped_column(String(255), nullable=False)
    # e.g., activity name, user ID
    dimension_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    numeric_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    count_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sse-starlette package | FastAPI built-in EventSourceResponse | FastAPI 0.135.0 (2025) | No extra dependency; Pydantic serialization built-in |
| StreamingResponse for SSE | EventSourceResponse with yield | FastAPI 0.135.0 | Cleaner API, automatic content-type, ServerSentEvent model |
| Recharts 2.x | Recharts 3.x available | 2025-2026 | 3.x has breaking changes; CLAUDE.md specifies 2.x, stay on 2.x |

**Deprecated/outdated:**
- `sse-starlette` package: Still works but unnecessary with FastAPI 0.135+
- Manual `text/event-stream` content-type on StreamingResponse: Use EventSourceResponse instead

## Open Questions

1. **PostgreSQL LISTEN/NOTIFY vs Polling for SSE**
   - What we know: D-04 mentions LISTEN/NOTIFY backing. The test DB is SQLite (no LISTEN/NOTIFY). Production uses PostgreSQL.
   - What's unclear: Whether to implement LISTEN/NOTIFY now or use simple polling (asyncio.sleep) as a first pass.
   - Recommendation: Start with polling in the SSE loop (asyncio.sleep(5)). Add LISTEN/NOTIFY as an optimization later if needed. This keeps tests simple and delivers the same user experience. The SSE contract stays the same either way.

2. **Recharts 2.x Exact Version**
   - What we know: CLAUDE.md says "Recharts 2.x". The latest 2.x on npm needs verification.
   - What's unclear: Latest patch version in the 2.x line.
   - Recommendation: Install `recharts@^2.15.0` (or latest 2.x). The API has been stable within 2.x for years.

3. **Document Query Metadata Search**
   - What we know: QUERY-03 requires querying by metadata. Documents have `metadata` as a JSON column.
   - What's unclear: How deep metadata search needs to go (top-level keys only vs nested).
   - Recommendation: Support top-level key-value matching only (e.g., `metadata_key=author&metadata_value=John`). This is sufficient for the requirement and avoids complex JSON path queries that differ between SQLite and PostgreSQL.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BAM-01 | Workflow state counts endpoint returns correct counts | integration | `python -m pytest tests/test_dashboard.py::test_workflow_counts -x` | Wave 0 |
| BAM-02 | Average completion time per template | integration | `python -m pytest tests/test_dashboard.py::test_avg_completion_time -x` | Wave 0 |
| BAM-03 | Bottleneck activities identification | integration | `python -m pytest tests/test_dashboard.py::test_bottleneck_activities -x` | Wave 0 |
| BAM-04 | Workload per user metrics | integration | `python -m pytest tests/test_dashboard.py::test_workload_per_user -x` | Wave 0 |
| BAM-05 | SLA compliance rate calculation | integration | `python -m pytest tests/test_dashboard.py::test_sla_compliance -x` | Wave 0 |
| QUERY-01 | Query workflows by template/state/date/performer | integration | `python -m pytest tests/test_query.py::test_query_workflows -x` | Wave 0 |
| QUERY-02 | Query work items by assignee/state/workflow/priority | integration | `python -m pytest tests/test_query.py::test_query_work_items -x` | Wave 0 |
| QUERY-03 | Query documents by metadata/lifecycle/version | integration | `python -m pytest tests/test_query.py::test_query_documents -x` | Wave 0 |
| EXAMPLE-01 | Contract approval template created correctly | integration | `python -m pytest tests/test_contract_approval.py::test_template_creation -x` | Wave 0 |
| EXAMPLE-02 | Template has correct routing types | integration | `python -m pytest tests/test_contract_approval.py::test_routing_types -x` | Wave 0 |
| EXAMPLE-03 | E2E execution produces audit trail | integration | `python -m pytest tests/test_contract_approval.py::test_e2e_execution -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_dashboard.py tests/test_query.py tests/test_contract_approval.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dashboard.py` -- covers BAM-01 through BAM-05
- [ ] `tests/test_query.py` -- covers QUERY-01 through QUERY-03
- [ ] `tests/test_contract_approval.py` -- covers EXAMPLE-01 through EXAMPLE-03

## Sources

### Primary (HIGH confidence)
- FastAPI SSE official docs: https://fastapi.tiangolo.com/tutorial/server-sent-events/ -- EventSourceResponse pattern, ServerSentEvent model
- Existing codebase: `src/app/routers/audit.py` -- Condition-based query pattern with pagination
- Existing codebase: `src/app/tasks/auto_activity.py` -- Celery task + asyncio.run pattern
- Existing codebase: `src/app/celery_app.py` -- Beat schedule configuration
- Existing codebase: `src/app/auto_methods/builtin.py` -- Registered auto methods for seed script

### Secondary (MEDIUM confidence)
- Recharts npm: https://www.npmjs.com/package/recharts -- Version 3.8.1 is latest; 2.x line still maintained
- Browser EventSource API: Standard Web API, auto-reconnection behavior

### Tertiary (LOW confidence)
- PostgreSQL LISTEN/NOTIFY integration with async SQLAlchemy -- not verified for this project's exact driver setup; deferred to polling approach

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already specified in CLAUDE.md or installed in project
- Architecture: HIGH - Follows existing codebase patterns (router/service/model async, Celery beat, audit query)
- Pitfalls: HIGH - Based on direct codebase analysis (SQLite test limitations, session lifecycle, EventSource auth)
- SSE implementation: HIGH - Verified against FastAPI 0.135+ official docs
- Seed script: HIGH - Uses existing auto_methods (change_lifecycle_state) and REST API patterns

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable -- all core libraries are established)
