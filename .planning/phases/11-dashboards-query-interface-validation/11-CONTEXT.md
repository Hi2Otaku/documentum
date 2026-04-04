# Phase 11: Dashboards, Query Interface & Validation - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Admins have BAM dashboards for process metrics (workflow counts, completion time, bottlenecks, workload, SLA compliance), a query interface for searching workflows/work items/documents by multiple criteria, and the contract approval example proves the entire system works end-to-end with sequential, parallel, and conditional routing, reject flows, auto activities, and full audit trail.

</domain>

<decisions>
## Implementation Decisions

### Dashboard Layout & Metrics
- **D-01:** KPI cards + charts layout. Top row of summary cards (running/halted/finished/failed counts, average completion time per template). Below: two-column chart area with bottleneck chart (bar chart showing avg duration per activity) and workload by user (bar chart showing assigned/completed/pending). Bottom section for SLA compliance visualization.
- **D-02:** SLA measured per-activity via optional `expected_duration_hours` field on activity templates. SLA compliance % = work items completed within the configured time limit. Activities without a time limit are excluded from SLA calculations.
- **D-03:** Template dropdown filter on dashboard. Default view shows all templates combined. Dropdown lets admin filter to a specific template — all KPIs and charts update accordingly.

### Real-Time Update Strategy
- **D-04:** SSE (Server-Sent Events) for live dashboard updates. FastAPI `StreamingResponse` endpoint pushes data when workflow state changes. Backed by PostgreSQL LISTEN/NOTIFY to detect state changes without polling.
- **D-05:** Hybrid metrics computation. KPI counts (running/halted/finished/failed) computed on-the-fly from live queries — always accurate. Chart data (bottleneck analysis, trends, workload aggregation) pre-aggregated by a Celery beat task into a summary table at regular intervals.

### Query Interface Design
- **D-06:** Form-based filter panel with structured dropdowns and date pickers. Three tabs: Workflows, Work Items, Documents. Each tab has entity-specific filters:
  - Workflows: template, state, date range, performer (started_by)
  - Work Items: assignee, state, workflow, priority
  - Documents: metadata fields, lifecycle state, version
- **D-07:** Results displayed in sortable, paginated tables (using @tanstack/react-table). Clickable rows navigate to detail views showing full entity state — workflow detail shows active activities, work items, audit trail; document detail shows versions and metadata.

### Contract Approval Example
- **D-08:** Python seed script that calls backend REST APIs to create the full 7-step contract approval template. Runs as a CLI command (`python -m scripts.seed_contract_approval`) or invocable at startup. Creates: template with activities, flows, alias set, and test users.
- **D-09:** The 7 steps: (1) Initiate — start activity, (2) Draft Contract — manual, drafter, (3) Parallel Legal Review + Financial Review — manual, lawyer and accountant simultaneously, (4) Director Approval — manual, director, conditional (approve/reject), (5) Digital Signing — auto activity, sets `signed=true` process variable + logs, (6) Archival — auto activity, transitions document lifecycle to Archived state, (7) End.
- **D-10:** Simulated auto-activity actions. Digital signing sets a process variable and logs the action. Archival triggers a lifecycle transition to Archived state using existing lifecycle APIs. Real behavior using existing system capabilities, no external dependencies.
- **D-11:** Full demo run — seed script also creates 4 test users (drafter, lawyer, accountant, director), starts a workflow instance, auto-completes all activities step by step, and produces a finished workflow with a complete audit trail. One command proves E2E.

### Claude's Discretion
- Recharts chart types and styling details (bar vs horizontal bar, color scheme)
- SSE endpoint implementation details (event format, reconnection strategy)
- Celery beat interval for pre-aggregated metrics (e.g., every 5 minutes)
- Summary table schema for pre-aggregated chart data
- Detail view layout and information hierarchy
- Seed script error handling and idempotency approach
- Exact filter field components (combobox vs dropdown for user/template pickers)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — BAM-01 through BAM-05 (dashboard metrics), QUERY-01 through QUERY-03 (query interface), EXAMPLE-01 through EXAMPLE-03 (contract approval)

### Existing Backend Patterns
- `src/app/routers/audit.py` — Existing audit query endpoint with filtering pattern (condition-based WHERE, count subquery, pagination). Reuse this pattern for new query endpoints.
- `src/app/routers/workflows.py` — Workflow CRUD and state management endpoints. Query interface extends this with additional filters.
- `src/app/services/` — 14 service files establishing the async service layer pattern. New dashboard and query services follow this.
- `src/app/models/audit.py` — AuditLog model, primary data source for audit trail metrics.
- `src/app/models/execution_log.py` — AutoActivityLog model for auto-activity execution metrics.

### Existing Frontend Patterns
- `frontend/src/pages/TemplateListPage.tsx` — Existing list page pattern to follow for query results pages.
- `frontend/src/components/` — shadcn/ui component library and app shell structure.
- `frontend/src/api/` — API client pattern (auth.ts, templates.ts) to extend for dashboard and query APIs.

### Background Task Patterns
- `src/app/tasks/auto_activity.py` — Celery task pattern with `@celery_app.task`, periodic scheduling, error handling. Follow for metrics aggregation task.
- `src/app/celery_app.py` — Celery app configuration and beat schedule setup.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EnvelopeResponse[T]` + `PaginationMeta`: Standard response wrapper for all paginated endpoints — use for query results
- `get_current_active_admin` dependency: Admin-only route protection — use for dashboard and query routes
- `AuditLog` model with indexed timestamp/entity fields: Ready for metrics aggregation queries
- `@tanstack/react-table` in tech stack: Use for query result tables
- `Recharts` in tech stack: Use for dashboard charts (bar charts, gauges)
- Existing audit query endpoint pattern: Condition-based filtering with skip/limit pagination

### Established Patterns
- Router → Service → Model async pattern across all 12 existing routers
- Alembic migrations for schema changes (new `expected_duration_hours` field, metrics summary table)
- Celery beat for periodic tasks (auto-activity polling)
- React Router for page navigation, Zustand for UI state, TanStack Query for server state

### Integration Points
- Dashboard page added to app shell navigation (top nav bar)
- Query interface page added to app shell navigation
- SSE endpoint registered in `main.py` alongside existing routers
- Celery beat schedule extended with metrics aggregation task
- Activity template model extended with `expected_duration_hours` for SLA
- Seed script creates data via existing REST API endpoints

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-dashboards-query-interface-validation*
*Context gathered: 2026-04-04*
