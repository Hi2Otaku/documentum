---
phase: 11-dashboards-query-interface-validation
verified: 2026-04-05T12:00:00Z
status: gaps_found
score: 21/22 must-haves verified
re_verification: true
  previous_status: gaps_found
  previous_score: 14/22
  gaps_closed:
    - "GET /api/v1/dashboard/metrics endpoint created (unified /metrics route)"
    - "Dashboard auth changed to get_current_active_admin on all routes"
    - "Audit router restored to main.py — audit 404 regression fixed"
    - "SlaCompliance schema, get_sla_data(), KpiMetrics, DashboardMetrics added"
    - "get_kpi_metrics() and get_all_metrics() added to dashboard_service"
    - "GET /api/v1/dashboard/stream SSE endpoint created with token auth"
    - "MetricsSummary model created (src/app/models/metrics.py)"
    - "aggregate_dashboard_metrics Celery task created (src/app/tasks/metrics_aggregation.py)"
    - "celery_app include list and beat_schedule updated with metrics_aggregation"
    - "expected_duration_hours field added to ActivityTemplate model"
    - "All three contract approval tests pass (EXAMPLE-01, EXAMPLE-02, EXAMPLE-03)"
    - "Dashboard test suite expanded to 15 tests covering KPI, SLA, get_all_metrics"
  gaps_remaining:
    - "No Alembic migration for expected_duration_hours column or metrics_summary table"
  regressions: []
gaps:
  - truth: "Celery beat task pre-aggregates chart data into metrics_summary table"
    status: partial
    reason: "MetricsSummary model (src/app/models/metrics.py) and Celery task (src/app/tasks/metrics_aggregation.py) both exist and are wired. However, no Alembic migration file was created for the metrics_summary table or the expected_duration_hours column on activity_templates. Tests pass because SQLite creates tables from scratch; a real PostgreSQL deployment will fail with 'relation metrics_summary does not exist' until the migration is applied."
    artifacts:
      - path: "alembic/versions/"
        issue: "No migration file containing CREATE TABLE metrics_summary or ADD COLUMN expected_duration_hours. The five existing migration files (phase6_001, phase7_001, phase10_001, a1b2c3d4e5f6, and one other) do not include these schema changes."
    missing:
      - "Create Alembic migration: alembic revision --autogenerate -m 'add_expected_duration_hours_and_metrics_summary' and verify it includes CREATE TABLE metrics_summary and ADD COLUMN expected_duration_hours TO activity_templates"
human_verification:
  - test: "Visually verify Dashboard page KPI card colors and SSE indicator"
    expected: "5 colored KPI cards visible; SSE indicator shows connected state when stream is live"
    why_human: "Visual verification of UI colors, responsive layout, and SSE status indicator requires browser rendering"
  - test: "Visually verify Query page three-tab layout and filter interaction"
    expected: "Three tabs (Workflows, Work Items, Documents) visible; Search returns real data; tab filter state preserved on switch"
    why_human: "Visual layout and interactive tab-state behavior requires browser"
  - test: "Run seed script against live stack: python -m scripts.seed_contract_approval"
    expected: "Script completes, prints final workflow state 'finished', audit trail shows >= 5 entries"
    why_human: "Requires running Docker stack (PostgreSQL, Redis, MinIO, Celery worker)"
  - test: "Apply Alembic migrations against PostgreSQL and verify metrics_summary table and expected_duration_hours column exist"
    expected: "alembic upgrade head succeeds; SELECT expected_duration_hours FROM activity_templates and SELECT * FROM metrics_summary both return without error"
    why_human: "Requires live PostgreSQL instance — tests run against SQLite"
---

# Phase 11: Dashboards, Query Interface & Validation — Verification Report

**Phase Goal:** Admins have BAM dashboards for process metrics, a query interface for administration, and the contract approval example proves the entire system works end-to-end

**Verified:** 2026-04-05T12:00:00Z
**Status:** GAPS FOUND (1 remaining gap)
**Re-verification:** Yes — after gap closure. Previous score: 14/22. Current score: 21/22.

---

## Re-verification Summary

**8 gaps from initial verification.** 7 fully closed. 1 remains.

| Previous Gap | Closed? | Evidence |
|---|---|---|
| No /metrics endpoint (Cluster A) | YES | `@router.get("/metrics")` at dashboard.py line 81 |
| No SLA implementation (BAM-05) | YES | `get_sla_data()` in dashboard_service.py line 244; `SlaCompliance` schema in dashboard.py line 54 |
| No /stream SSE endpoint | YES | `@router.get("/stream")` at dashboard.py line 135; StreamingResponse with token auth |
| No Celery beat task / MetricsSummary model | YES | src/app/models/metrics.py, src/app/tasks/metrics_aggregation.py, both wired in celery_app.py |
| Dashboard admin auth (Cluster B) | YES | All 4 original routes + new /metrics use `Depends(get_current_active_admin)` |
| Audit router regression (Cluster C) | YES | main.py line 87: `application.include_router(audit.router, ...)` |
| KPI cards data hollow (frontend) | YES | fetchDashboardMetrics calls /dashboard/metrics — endpoint now exists |
| SSE hook hollow (frontend) | YES | useDashboardSSE connects to /dashboard/stream — endpoint now exists |
| Missing Alembic migration | NO | No migration file for metrics_summary table or expected_duration_hours column |

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /api/v1/dashboard/metrics returns counts of running, halted, finished, failed workflows | VERIFIED | `get_kpi_metrics()` queries WorkflowInstance grouped by state; test_kpi_metrics_shape passes with running=2, halted=1, finished=1, failed=1 |
| 2 | GET /api/v1/dashboard/metrics returns average completion time per template | VERIFIED | `avg_completion_hours` in KpiMetrics; template-level avg in `get_template_metrics()`; test_kpi_metrics_shape asserts avg_completion_hours > 0 |
| 3 | GET /api/v1/dashboard/metrics returns bottleneck activities sorted by avg duration | VERIFIED | `get_bottleneck_data()` reshapes to DashboardBottleneck with avg_duration_hours; test_bottleneck_with_data confirms sort order |
| 4 | GET /api/v1/dashboard/metrics returns workload per user (assigned, completed, pending) | VERIFIED | `get_all_metrics()` calls get_user_workload(), reshapes to DashboardWorkload with assigned/completed/pending; test_user_workload_with_data passes |
| 5 | GET /api/v1/dashboard/metrics returns SLA compliance rate per activity | VERIFIED | `get_sla_data()` joins WorkItem -> ActivityInstance -> ActivityTemplate on expected_duration_hours; test_sla_data_with_on_time_and_overdue asserts on_time=2, overdue=1, compliance_percent≈66.67 |
| 6 | GET /api/v1/dashboard/stream returns SSE events for live KPI updates | VERIFIED (with caveat) | `/stream` endpoint exists, accepts token query param, validates admin, returns StreamingResponse; uses asyncio.sleep(5) polling (not LISTEN/NOTIFY per D-04 design decision — see note below) |
| 7 | Celery beat task pre-aggregates chart data into metrics_summary table | PARTIAL | Task file exists and is wired in celery_app.py. Model exists. No Alembic migration — metrics_summary table will not exist in PostgreSQL until migration is created and applied |
| 8 | Dashboard endpoints require admin authentication | VERIFIED | All 5 dashboard routes (summary, bottlenecks, workload, templates, metrics) use `Depends(get_current_active_admin)` per dashboard.py lines 34, 47, 62, 75, 85 |
| 9 | Admin can query workflow instances by template, state, date range, started_by | VERIFIED | GET /api/v1/query/workflows with all filter params; 6 tests pass |
| 10 | Admin can query work items by assignee, state, workflow, priority | VERIFIED | GET /api/v1/query/work-items; 4 tests pass |
| 11 | Admin can query documents by lifecycle, metadata, version | VERIFIED | GET /api/v1/query/documents; 3 tests pass including metadata filter |
| 12 | All query endpoints require admin authentication | VERIFIED | All three use Depends(get_current_active_admin); test_query_requires_admin returns 403 |
| 13 | All query endpoints return paginated results | VERIFIED | PaginationMeta with page, page_size, total_count, total_pages in EnvelopeResponse |
| 14 | 7-step contract approval template with correct activity types | VERIFIED | test_contract_approval_template_creation PASSES — 8 activities: 1 start, 4 manual, 2 auto, 1 end |
| 15 | Template demonstrates all routing types (sequential, parallel, conditional, reject, auto) | VERIFIED | test_contract_approval_routing_types PASSES — parallel split, AND-join, performer_chosen, reject flow all verified |
| 16 | Seed script exists and creates 4 test users | VERIFIED | scripts/seed_contract_approval.py with async main(); contains drafter, lawyer, accountant, director creation |
| 17 | Seed script creates template, installs, executes | VERIFIED | Script code complete and importable; uses retry polling |
| 18 | Complete audit trail exists after E2E execution | VERIFIED | test_contract_approval_e2e_execution PASSES — GET /api/v1/audit returns 200, audit_data >= 5 entries |
| 19 | Dashboard page renders at /dashboard with KPI cards | VERIFIED | DashboardPage.tsx wired to /dashboard/metrics (endpoint now exists); TypeScript compiles clean |
| 20 | KPI cards update via SSE connection | VERIFIED | useDashboardSSE connects to /dashboard/stream (endpoint now exists); EventSource wired to kpi_update event |
| 21 | Query page renders at /query with three tabs | VERIFIED | QueryPage at /query with WorkflowQueryTab, WorkItemQueryTab, DocumentQueryTab |
| 22 | Dashboard and Query links in AppShell navigation | VERIFIED | AppShell.tsx has to="/dashboard" and to="/query"; App.tsx registers both routes |

**Score: 21/22 truths verified**

**Note on SSE (Truth #6):** The `/stream` endpoint implements 5-second polling (`asyncio.sleep(5)`) rather than PostgreSQL LISTEN/NOTIFY as specified in design decision D-04. The REQUIREMENTS.md does not specify the transport mechanism for live updates — only that the dashboard "shows" metrics. The endpoint is functionally correct and provides live updates. LISTEN/NOTIFY was a design decision, not a named requirement. Truth #6 is marked VERIFIED because the observable behavior (live KPI updates) is achievable; the implementation differs from the plan's intended approach.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/app/models/metrics.py` | MetricsSummary model | VERIFIED | `class MetricsSummary(BaseModel)` with metric_type, dimension_key, numeric_value, count_value, computed_at |
| `src/app/models/workflow.py` | ActivityTemplate.expected_duration_hours | VERIFIED | Line 106: `expected_duration_hours: Mapped[float \| None] = mapped_column(Float, nullable=True)` |
| `src/app/schemas/dashboard.py` | KpiMetrics, SlaCompliance, DashboardMetrics | VERIFIED | All classes present: KpiMetrics (line 46), SlaCompliance (line 54), DashboardBottleneck (line 61), DashboardWorkload (line 68), DashboardMetrics (line 77) |
| `src/app/services/dashboard_service.py` | get_kpi_metrics, get_all_metrics, get_sla_data | VERIFIED | All 5 service functions: get_kpi_metrics (line 314), get_all_metrics (line 376), get_sla_data (line 244), get_bottleneck_activities (line 70), get_user_workload (line 136) |
| `src/app/routers/dashboard.py` | /metrics and /stream endpoints, admin auth | VERIFIED | /metrics at line 81 (get_current_active_admin); /stream at line 135 with token auth |
| `src/app/tasks/metrics_aggregation.py` | Celery beat task | VERIFIED | `@celery_app.task(name="app.tasks.metrics_aggregation.aggregate_dashboard_metrics")` at line 11 |
| `src/app/celery_app.py` | metrics_aggregation in include, beat_schedule entry | VERIFIED | Line 14: include contains "app.tasks.metrics_aggregation"; line 31: "aggregate-dashboard-metrics" with schedule 300.0 |
| `src/app/main.py` | audit and dashboard routers registered | VERIFIED | Line 87: audit.router; line 88: dashboard.router; line 90: query.router |
| `alembic/versions/` | Migration for expected_duration_hours and metrics_summary | MISSING | No migration file found. Five existing migrations do not include these schema changes. |
| `src/app/schemas/query.py` | WorkflowQueryResponse, WorkItemQueryResponse, DocumentQueryResponse | VERIFIED | All three classes present with correct fields |
| `src/app/services/query_service.py` | query_workflows, query_work_items, query_documents | VERIFIED | All three async functions with filtering and pagination |
| `src/app/routers/query.py` | GET /workflows, /work-items, /documents | VERIFIED | All three endpoints with admin auth and paginated EnvelopeResponse |
| `tests/test_dashboard.py` | Tests covering BAM-01 through BAM-05 | VERIFIED | 15 tests — all pass including test_sla_data_*, test_kpi_metrics_*, test_all_metrics_shape |
| `tests/test_query.py` | 14 integration tests | VERIFIED | 14 tests pass |
| `scripts/seed_contract_approval.py` | E2E seed script | VERIFIED | async main(), 4 users, 8 activities, 9 flows, retry polling |
| `tests/test_contract_approval.py` | 3 contract approval tests | VERIFIED | All 3 pass — EXAMPLE-01, EXAMPLE-02, EXAMPLE-03 |
| `frontend/src/api/dashboard.ts` | fetchDashboardMetrics calling /dashboard/metrics | VERIFIED | Calls `/api/v1/dashboard/metrics`; interface matches DashboardMetrics backend schema |
| `frontend/src/hooks/useDashboardSSE.ts` | useDashboardSSE with EventSource | VERIFIED | Connects to `/api/v1/dashboard/stream?token=...`; listens for kpi_update events |
| `frontend/src/pages/DashboardPage.tsx` | Full dashboard with KPI/charts/SSE | VERIFIED | All UI structure present; TypeScript compiles clean |
| `frontend/src/components/dashboard/KpiCards.tsx` | 5 semantic KPI cards | VERIFIED | 5 cards with correct border colors, aria-live, loading skeleton |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `src/app/routers/dashboard.py` | `src/app/services/dashboard_service.py` | async function calls | VERIFIED | /metrics calls get_all_metrics(); /summary, /bottlenecks, /workload, /templates call respective service functions |
| `src/app/main.py` | `src/app/routers/dashboard.py` | include_router | VERIFIED | Line 88 — dashboard.router registered |
| `src/app/main.py` | `src/app/routers/audit.py` | include_router | VERIFIED | Line 87 — audit.router registered (regression FIXED) |
| `src/app/main.py` | `src/app/routers/query.py` | include_router | VERIFIED | Line 90 — query.router registered |
| `src/app/celery_app.py` | `src/app/tasks/metrics_aggregation.py` | beat_schedule | VERIFIED | "aggregate-dashboard-metrics" in beat_schedule with schedule: 300.0; task file in include list |
| `src/app/tasks/metrics_aggregation.py` | `src/app/models/metrics.py` | MetricsSummary import | VERIFIED | _aggregate_async() imports and uses MetricsSummary |
| `src/app/services/dashboard_service.py` | `src/app/models/workflow.py` | ActivityTemplate.expected_duration_hours | VERIFIED | get_sla_data() references ActivityTemplate.expected_duration_hours at line 283 |
| `frontend/src/pages/DashboardPage.tsx` | `frontend/src/api/dashboard.ts` | fetchDashboardMetrics | VERIFIED | useQuery calls fetchDashboardMetrics; endpoint /dashboard/metrics now exists on backend |
| `frontend/src/pages/DashboardPage.tsx` | `frontend/src/hooks/useDashboardSSE.ts` | useDashboardSSE hook | VERIFIED | Hook called; EventSource connects to /dashboard/stream (endpoint exists) |
| `frontend/src/App.tsx` | `frontend/src/pages/DashboardPage.tsx` | React Router path="/dashboard" | VERIFIED | Route registered |
| `frontend/src/App.tsx` | `frontend/src/pages/QueryPage.tsx` | React Router path="/query" | VERIFIED | Route registered |
| `alembic/versions/` | PostgreSQL schema | migration | BROKEN | No migration for metrics_summary table or expected_duration_hours column |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `DashboardPage.tsx` | `metrics.kpi` | `fetchDashboardMetrics()` -> `/api/v1/dashboard/metrics` -> `get_all_metrics()` -> `get_kpi_metrics()` | Yes — DB queries WorkflowInstance by state | FLOWING |
| `DashboardPage.tsx` | `sseMetrics` | `useDashboardSSE()` -> `/api/v1/dashboard/stream` -> `get_kpi_metrics()` every 5s | Yes — same DB query on polling interval | FLOWING |
| `DashboardPage.tsx` | `metrics.bottleneck_activities` | `fetchDashboardMetrics()` -> `get_bottleneck_data()` -> DB query ActivityInstance + ActivityTemplate | Yes — real DB query | FLOWING |
| `DashboardPage.tsx` | `metrics.sla_compliance` | `fetchDashboardMetrics()` -> `get_sla_data()` -> WorkItem + ActivityInstance + ActivityTemplate join | Yes — real DB query on expected_duration_hours | FLOWING (model column present; migration absent — data won't exist in PostgreSQL until migration applied) |
| `WorkflowQueryTab.tsx` | `queryData` | `queryWorkflows()` -> `/api/v1/query/workflows` | Yes — backend returns real DB data | FLOWING |
| `WorkItemQueryTab.tsx` | `queryData` | `queryWorkItems()` -> `/api/v1/query/work-items` | Yes — backend returns real DB data | FLOWING |
| `DocumentQueryTab.tsx` | `queryData` | `queryDocuments()` -> `/api/v1/query/documents` | Yes — backend returns real DB data | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All dashboard tests pass | `python -m pytest tests/test_dashboard.py -q` | 15 passed in 1.29s | PASS |
| All query tests pass | `python -m pytest tests/test_query.py -q` | 14 passed in 2.19s | PASS |
| Contract approval template creation (EXAMPLE-01) | `python -m pytest tests/test_contract_approval.py::test_contract_approval_template_creation` | PASSED | PASS |
| Contract approval routing types (EXAMPLE-02) | `python -m pytest tests/test_contract_approval.py::test_contract_approval_routing_types` | PASSED | PASS |
| Contract approval E2E execution (EXAMPLE-03) | `python -m pytest tests/test_contract_approval.py::test_contract_approval_e2e_execution` | PASSED — audit 404 regression FIXED | PASS |
| Full test suite | `python -m pytest tests/ -q` | 265 passed in 45.59s — zero failures | PASS |
| TypeScript compiles clean | `cd frontend && npx tsc --noEmit` | No errors | PASS |
| Seed script importable | `python -c "import scripts.seed_contract_approval"` | Exit 0 | PASS |
| Alembic migration covers new schema | `ls alembic/versions/ \| grep -i "expected_duration\|metrics_summary"` | No output — migration absent | FAIL |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BAM-01 | 11-01 | Dashboard shows count of running, halted, finished, failed workflows | SATISFIED | GET /api/v1/dashboard/metrics returns KpiMetrics with running/halted/finished/failed fields. get_kpi_metrics() verified by test_kpi_metrics_shape. |
| BAM-02 | 11-01 | Dashboard shows avg completion time per workflow template | SATISFIED | KpiMetrics.avg_completion_hours computed from finished workflows. DashboardMetrics also contains per-bottleneck avg. test_kpi_metrics_shape asserts avg_completion_hours > 0. |
| BAM-03 | 11-01 | Dashboard identifies bottleneck activities (longest avg duration) | SATISFIED | get_bottleneck_data() returns DashboardBottleneck list sorted descending by avg_duration_hours. test_bottleneck_with_data confirms sort order. |
| BAM-04 | 11-01 | Dashboard shows workload per user | SATISFIED | get_user_workload() returns assigned/completed/pending per user. DashboardMetrics.workload is list[DashboardWorkload]. test_user_workload_with_data passes. |
| BAM-05 | 11-01 | Dashboard shows SLA compliance rate | SATISFIED | get_sla_data() computes on_time/overdue/compliance_percent per activity using expected_duration_hours. test_sla_data_with_on_time_and_overdue passes with on_time=2, overdue=1, compliance_percent≈66.67. (Note: requires migration for production deployment.) |
| QUERY-01 | 11-02 | Admin can query workflow instances by template, state, date range, performer | SATISFIED | GET /api/v1/query/workflows with all filters. 6 passing tests. Frontend WorkflowQueryTab wired. |
| QUERY-02 | 11-02 | Admin can query work items by assignee, state, workflow, priority | SATISFIED | GET /api/v1/query/work-items. 4 passing tests. Frontend WorkItemQueryTab wired. |
| QUERY-03 | 11-02 | Admin can query documents by metadata, lifecycle, version | SATISFIED | GET /api/v1/query/documents with metadata filtering. 3 passing tests. Frontend DocumentQueryTab wired. |
| EXAMPLE-01 | 11-03 | 7-step contract approval template | SATISFIED | test_contract_approval_template_creation PASSES. 8 activities, correct type distribution verified. |
| EXAMPLE-02 | 11-03 | All routing types demonstrated | SATISFIED | test_contract_approval_routing_types PASSES. Sequential, parallel split, AND-join, performer_chosen, reject all verified. |
| EXAMPLE-03 | 11-03 | E2E execution with complete audit trail | SATISFIED | test_contract_approval_e2e_execution PASSES — workflow FINISHED, audit returns 200 with >= 5 entries. Audit router regression FIXED. |

All 11 requirements are now SATISFIED at the code and test level.

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `alembic/versions/` | Missing migration for metrics_summary table and expected_duration_hours column | BLOCKER (production) | SLA data and Celery aggregation task will fail on PostgreSQL with "relation metrics_summary does not exist" and "column expected_duration_hours does not exist". Tests pass only because SQLite creates tables from scratch via metadata. |
| `src/app/routers/dashboard.py` lines 127-132 | SSE uses asyncio.sleep(5) polling instead of PostgreSQL LISTEN/NOTIFY (design decision D-04) | WARNING | KPI updates are delivered every 5 seconds regardless of workflow state changes, rather than being event-driven. Functional but less efficient at scale. Not a requirements failure — D-04 was a design choice, not a named requirement. |

---

## Human Verification Required

### 1. Dashboard Visual Layout

**Test:** Start full Docker stack. Navigate to http://localhost:5173/dashboard as admin user.
**Expected:** Page title "Dashboard", 5 colored KPI cards visible (running/halted/finished/failed/avg time), SSE connection indicator shows connected state, chart areas visible, template filter dropdown populated.
**Why human:** Visual color correctness, responsive layout, and SSE live indicator behavior require browser rendering.

### 2. Query Page Tab Interaction

**Test:** Navigate to http://localhost:5173/query. Click each tab and run a search.
**Expected:** Three tabs visible (Workflows, Work Items, Documents). Filter forms appear per tab. Search returns real data in paginated table. Switching tabs preserves previous tab filter values.
**Why human:** Tab state preservation and interactive filter behavior require browser.

### 3. Seed Script Live Run

**Test:** With full Docker stack running: `python -m scripts.seed_contract_approval`
**Expected:** Script completes printing final workflow state "finished", audit trail shows entry count >= 5.
**Why human:** Requires live PostgreSQL, Redis, MinIO, and Celery worker — cannot run in test context.

### 4. Alembic Migration Against PostgreSQL

**Test:** Run `alembic upgrade head` against a live PostgreSQL instance. Then verify: `SELECT expected_duration_hours FROM activity_templates LIMIT 1;` and `SELECT * FROM metrics_summary LIMIT 1;`
**Expected:** Both queries execute without error; metrics aggregation Celery task can run without "relation does not exist" errors.
**Why human:** Requires live PostgreSQL — all tests use SQLite.

---

## Gaps Summary

**1 gap remaining** after gap closure:

**Missing Alembic migration (Celery pre-aggregation fully functional in tests, broken in production):**
The `MetricsSummary` model in `src/app/models/metrics.py` and the `expected_duration_hours` field on `ActivityTemplate` are both present in code. The Celery task (`aggregate_dashboard_metrics`) is wired and beat-scheduled. The SLA service function (`get_sla_data`) references `expected_duration_hours`. However, no Alembic migration file exists to CREATE TABLE metrics_summary or ADD COLUMN expected_duration_hours to activity_templates in PostgreSQL. The five existing migration files cover phases 6, 7, 10, and earlier schema. Tests pass because aiosqlite creates schema from SQLAlchemy metadata. Against a real PostgreSQL deployment, `alembic upgrade head` will not create these objects, causing runtime failures in both the Celery task and SLA queries.

The fix is a single command: `alembic revision --autogenerate -m "add_expected_duration_hours_and_metrics_summary"` followed by verifying the generated file includes both DDL operations.

---

_Verified: 2026-04-05T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — previous gaps_found (14/22), current gaps_found (21/22)_
