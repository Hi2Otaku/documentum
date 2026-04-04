---
phase: 11-dashboards-query-interface-validation
plan: 07
subsystem: api
tags: [fastapi, sse, celery, sla, dashboard, metrics]

requires:
  - phase: 11-dashboards-query-interface-validation (plans 01-06)
    provides: existing dashboard service, router, schemas, frontend dashboard page
provides:
  - Unified GET /dashboard/metrics endpoint matching frontend DashboardMetrics contract
  - SSE GET /dashboard/stream endpoint emitting kpi_update events
  - SLA compliance computation from expected_duration_hours on ActivityTemplate
  - MetricsSummary model for pre-aggregated chart data
  - Celery beat aggregation task running every 5 minutes
affects: [frontend-dashboard, bam-dashboards]

tech-stack:
  added: []
  patterns: [SSE via StreamingResponse with JWT query param auth, julianday-based SLA duration calc]

key-files:
  created:
    - src/app/models/metrics.py
    - src/app/tasks/metrics_aggregation.py
  modified:
    - src/app/models/workflow.py
    - src/app/schemas/dashboard.py
    - src/app/services/dashboard_service.py
    - src/app/routers/dashboard.py
    - src/app/celery_app.py
    - tests/test_dashboard.py

key-decisions:
  - "SSE uses StreamingResponse with manual event formatting (not EventSourceResponse) for compatibility"
  - "SLA duration computed via julianday for SQLite compatibility"
  - "Completed work item counts queried separately in get_all_metrics for workload reshaping"

patterns-established:
  - "SSE auth via JWT query param with manual token validation (EventSource cannot send headers)"
  - "Per-iteration session creation for SSE generators to avoid long-lived DB sessions"

requirements-completed: [BAM-01, BAM-02, BAM-03, BAM-04, BAM-05]

duration: 5min
completed: 2026-04-04
---

# Phase 11 Plan 07: Dashboard Backend Gap Closure Summary

**Unified /dashboard/metrics and SSE /dashboard/stream endpoints with SLA compliance computation and Celery beat aggregation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-04T17:25:24Z
- **Completed:** 2026-04-04T17:30:21Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Implemented GET /dashboard/metrics returning DashboardMetrics JSON matching the frontend TypeScript interface exactly (kpi, bottleneck_activities, workload, sla_compliance)
- Implemented GET /dashboard/stream SSE endpoint emitting kpi_update events every 5 seconds with JWT query param auth
- Added SLA compliance computation using expected_duration_hours on ActivityTemplate with on_time/overdue/compliance_percent
- Created MetricsSummary model for pre-aggregated chart data storage
- Added Celery beat task aggregating bottleneck, workload, and SLA data every 5 minutes

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SLA field, MetricsSummary model, schemas, and service functions** - `b024076` (feat)
2. **Task 2: Add unified /metrics endpoint, SSE /stream endpoint, and Celery aggregation task** - `f9ee757` (feat)

## Files Created/Modified
- `src/app/models/metrics.py` - MetricsSummary SQLAlchemy model for pre-aggregated chart data
- `src/app/models/workflow.py` - Added expected_duration_hours to ActivityTemplate
- `src/app/schemas/dashboard.py` - KpiMetrics, SlaCompliance, DashboardBottleneck, DashboardWorkload, DashboardMetrics schemas
- `src/app/services/dashboard_service.py` - get_sla_data, get_kpi_metrics, get_all_metrics functions
- `src/app/routers/dashboard.py` - /metrics and /stream SSE endpoints with JWT query param auth
- `src/app/tasks/metrics_aggregation.py` - Celery beat task for dashboard data pre-aggregation
- `src/app/celery_app.py` - Added metrics_aggregation to include list and beat_schedule
- `tests/test_dashboard.py` - SLA, KPI, and unified metrics tests

## Decisions Made
- SSE uses StreamingResponse with manual SSE formatting rather than EventSourceResponse for broad compatibility
- SLA duration uses julianday arithmetic for SQLite compatibility (same pattern as existing bottleneck queries)
- Completed work item counts queried separately in get_all_metrics to reshape workload data for frontend contract
- SSE token validation creates its own session (not Depends) per RESEARCH.md pitfall guidance

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all data paths are wired to live queries.

## Next Phase Readiness
- Dashboard backend fully implements the frontend contract
- SSE stream, unified metrics, and SLA computation all operational
- All 15 dashboard tests pass including new SLA/KPI/unified metrics tests

---
*Phase: 11-dashboards-query-interface-validation*
*Completed: 2026-04-04*
