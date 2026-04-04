---
phase: "11"
plan: "01"
subsystem: dashboard-query
tags: [bam-dashboard, query-interface, metrics, admin]
dependency_graph:
  requires: [workflow-models, audit-log, document-models]
  provides: [dashboard-api, query-api]
  affects: [main-router-registration]
tech_stack:
  added: []
  patterns: [aggregate-queries, case-expressions, dynamic-filtering]
key_files:
  created:
    - src/app/schemas/dashboard.py
    - src/app/schemas/query.py
    - src/app/services/dashboard_service.py
    - src/app/services/query_service.py
    - src/app/routers/dashboard.py
    - src/app/routers/query.py
    - tests/test_dashboard.py
    - tests/test_query.py
  modified:
    - src/app/main.py
decisions:
  - Service-level tests used instead of HTTP-level due to worktree editable install limitation
  - julianday() used for SQLite duration calculations (portable to PostgreSQL with extract(epoch))
  - POST method for query endpoints to support complex filter bodies
metrics:
  duration: 9min
  completed: "2026-04-04"
---

# Phase 11 Plan 01: Dashboard Service, Query Interface & API Endpoints Summary

BAM dashboard with workflow summary/bottleneck/workload/template metrics, plus multi-criteria query interface for workflows, work items, documents, and audit logs.

## What Was Built

### Dashboard Service (BAM Metrics)
- **Workflow Summary**: Total counts by state (running/halted/finished/failed) plus average completion time
- **Bottleneck Detection**: Activities ranked by average duration, with active instance counts
- **User Workload**: Pending work item counts per user (available + acquired breakdown)
- **Template Metrics**: Per-template instance counts with state breakdown and avg completion

### Query Interface (Admin Search)
- **Workflow Query**: Filter by template, state, supervisor, date ranges (started/completed)
- **Work Item Query**: Filter by performer, state, workflow, priority range, due date
- **Document Query**: Filter by title (contains), author, content type, lifecycle state, date range
- **Audit Log Query**: Filter by entity type, entity ID, action, user, date range

### API Endpoints
- GET `/api/v1/dashboard/summary` - Workflow counts and completion stats
- GET `/api/v1/dashboard/bottlenecks` - Slow activity identification
- GET `/api/v1/dashboard/workload` - User task distribution
- GET `/api/v1/dashboard/templates` - Template performance breakdown
- POST `/api/v1/query/workflows` - Multi-criteria workflow search
- POST `/api/v1/query/work-items` - Multi-criteria work item search
- POST `/api/v1/query/documents` - Multi-criteria document search
- POST `/api/v1/query/audit-logs` - Multi-criteria audit log search

## Commits

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Dashboard schemas and service | e5739a9 | dashboard.py (schema), dashboard_service.py |
| 2 | Query schemas and service | 0d1d78e | query.py (schema), query_service.py |
| 3 | API routers and main.py registration | 9fc9e56 | dashboard.py (router), query.py (router), main.py |
| 4 | Tests (29 passing) | ac1fa6e | test_dashboard.py, test_query.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree editable install module resolution**
- **Found during:** Task 4
- **Issue:** Python's editable install (`pip install -e .`) resolves to the main repo's `src/`, not the worktree's `src/`. New modules (dashboard, query) aren't visible to pytest.
- **Fix:** Tests use `importlib.util.spec_from_file_location` to dynamically load worktree modules. Service functions tested directly instead of through HTTP layer.
- **Files modified:** tests/test_dashboard.py, tests/test_query.py
- **Commit:** ac1fa6e

## Verification

```
29 passed in 4.29s
```

All dashboard and query service functions tested with:
- Empty state (no data) returns
- Multi-criteria filtering
- Pagination
- State-based counting
- Date range filtering
- Bottleneck ordering

## Known Stubs

None. All service functions are fully implemented with real SQLAlchemy queries.

## Self-Check: PASSED

- All 8 created files verified on disk
- All 4 task commits (e5739a9, 0d1d78e, 9fc9e56, ac1fa6e) verified in git log
