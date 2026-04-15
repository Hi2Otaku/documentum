---
phase: 39-advanced-join-semantics
plan: 01
subsystem: workflow-engine
tags: [join-semantics, concurrency, celery, sqlalchemy, for-update]

requires:
  - phase: 38-workflow-versioning
    provides: template family versioning and migration chain
provides:
  - N-of-M join type firing at configurable threshold
  - Cancelling join that cancels remaining branches on fire
  - Timeout join polled by Celery Beat task
  - FOR UPDATE row-level locking preventing duplicate join activation
affects: [39-02, workflow-designer, engine-service]

tech-stack:
  added: []
  patterns: [FOR UPDATE locking on token queries, Celery beat polling for timeout joins]

key-files:
  created:
    - alembic/versions/phase39_001_advanced_joins.py
    - src/app/tasks/join_timeout.py
    - tests/test_join_semantics.py
  modified:
    - src/app/models/enums.py
    - src/app/models/workflow.py
    - src/app/services/engine_service.py
    - src/app/celery_app.py
    - src/app/schemas/template.py

key-decisions:
  - "FOR UPDATE locking on token count query with SQLite fallback for tests"
  - "Cancelling join defaults threshold to 1 when join_threshold is not set"
  - "Timeout join uses AND_JOIN logic for normal firing; Celery task force-fires on expiry"

patterns-established:
  - "Dialect-aware locking: skip FOR UPDATE on SQLite, apply on PostgreSQL"
  - "join_timeout_started_at set on first token arrival, not on activity creation"

requirements-completed: [JOIN-01, JOIN-02, JOIN-03, JOIN-04]

duration: 6min
completed: 2026-04-15
---

# Phase 39 Plan 01: Advanced Join Semantics Summary

**N-of-M, cancelling, and timeout join types with FOR UPDATE race-condition prevention and Celery beat timeout polling**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-15T06:05:48Z
- **Completed:** 2026-04-15T06:11:34Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Extended TriggerType enum with 3 new join types and ActivityState with CANCELLED
- Rewrote _should_activate with SELECT FOR UPDATE locking and N-of-M/cancelling/timeout dispatch
- Created _cancel_remaining_branches helper that cancels DORMANT/ACTIVE activities on join fire
- Added Celery beat task polling every 15s for timed-out joins
- 7 tests covering all join types, threshold logic, and concurrency verification

## Task Commits

Each task was committed atomically:

1. **Task 1: DB migration, enum extensions, model columns** - `53e7dac` (feat)
2. **Task 2: Engine logic, Celery timeout task, concurrency tests** - `3c3fb9b` (feat)

## Files Created/Modified
- `src/app/models/enums.py` - Extended TriggerType (5 values) and ActivityState (CANCELLED)
- `src/app/models/workflow.py` - Added join_threshold, join_timeout_hours, join_timeout_started_at
- `src/app/schemas/template.py` - Added join_threshold and join_timeout_hours to Create/Update/Response schemas
- `alembic/versions/phase39_001_advanced_joins.py` - Migration for new columns and enum values
- `src/app/services/engine_service.py` - Rewrote _should_activate with FOR UPDATE and new join types
- `src/app/tasks/join_timeout.py` - Celery beat task for timeout join polling
- `src/app/celery_app.py` - Added check-join-timeouts to beat schedule
- `tests/test_join_semantics.py` - 7 tests for all join semantics
- `src/app/models/identity_provider.py` - Fixed JSONB to JSON for SQLite compatibility

## Decisions Made
- FOR UPDATE locking on token count query with SQLite fallback (dialect check) for test environments
- Cancelling join defaults threshold to 1 when join_threshold is None
- Timeout join normal firing uses AND_JOIN semantics; timeout expiry handled by Celery task
- Pydantic schemas extended for API compatibility (Rule 2: missing critical functionality)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added join_threshold and join_timeout_hours to Pydantic schemas**
- **Found during:** Task 1 (Model columns)
- **Issue:** Plan only specified model columns but not API schemas; API would not accept new fields
- **Fix:** Added join_threshold and join_timeout_hours to ActivityTemplateCreate, Update, and Response schemas
- **Files modified:** src/app/schemas/template.py
- **Verification:** Fields available in API contract
- **Committed in:** 53e7dac (Task 1 commit)

**2. [Rule 3 - Blocking] Fixed JSONB to JSON in identity_provider model**
- **Found during:** Task 2 (Running tests)
- **Issue:** identity_providers table uses PostgreSQL JSONB type which cannot be rendered by SQLite compiler, blocking all tests
- **Fix:** Changed JSONB to generic JSON type (compatible with both PostgreSQL and SQLite)
- **Files modified:** src/app/models/identity_provider.py
- **Verification:** All tests pass on SQLite
- **Committed in:** 3c3fb9b (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 blocking)
**Impact on plan:** Both auto-fixes essential for API completeness and test execution. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 5 join types functional in the engine
- Frontend workflow designer needs updating (Plan 02) to expose new join type options
- Celery beat schedule includes timeout polling

---
*Phase: 39-advanced-join-semantics*
*Completed: 2026-04-15*
