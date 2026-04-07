---
phase: 24-infrastructure-wiring-event-bus
plan: 01
subsystem: infra
tags: [fastapi, celery, sqlalchemy, event-bus, routers, notifications]

requires:
  - phase: 23-digital-signatures
    provides: "Existing router/model infrastructure to extend"
provides:
  - "5 missing routers mounted (notifications, events, renditions, virtual_documents, retention)"
  - "Event handlers registered at startup via lifespan import"
  - "Notification Celery task registered with beat schedule"
  - "WorkItem escalation columns (is_escalated, deadline_warning_sent)"
  - "ActivityTemplate deadline columns (warning_threshold_hours, escalation_action)"
  - "All 8 new model classes exported from app.models"
affects: [24-02, 24-03, notifications, events, renditions, retention, virtual-documents]

tech-stack:
  added: []
  patterns:
    - "Router mounting pattern: import + include_router with api_v1_prefix"
    - "Event handler registration via import side-effect in lifespan"
    - "Beat schedule entry pattern for periodic Celery tasks"

key-files:
  created: []
  modified:
    - src/app/main.py
    - src/app/celery_app.py
    - src/app/models/workflow.py
    - src/app/models/__init__.py

key-decisions:
  - "Mount all 5 routers with settings.api_v1_prefix for consistency"
  - "Event handlers imported in lifespan startup block (decorators register at import time)"
  - "Deadline check interval set to 60 seconds per plan specification"

patterns-established:
  - "Lifespan event handler registration: import module with noqa for side-effect registration"

requirements-completed: [NOTIF-01, NOTIF-02, NOTIF-03, NOTIF-04, NOTIF-05, NOTIF-06, EVENT-01, TIMER-01, TIMER-03, TIMER-04, SUBWF-03, EVTACT-02, EVTACT-03, REND-03, REND-04, RET-01, RET-02, RET-04]

duration: 2min
completed: 2026-04-07
---

# Phase 24 Plan 01: Infrastructure Wiring Summary

**Mounted 5 missing routers, registered event handlers at startup, wired Celery notification task with beat schedule, added 4 missing ORM columns, and exported 8 model classes**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-07T02:34:16Z
- **Completed:** 2026-04-07T02:36:13Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Mounted notifications, events, renditions, virtual_documents, and retention routers in main.py
- Imported event_handlers module in lifespan for decorator-based handler registration
- Added app.tasks.notification to Celery include list with check-approaching-deadlines beat schedule (60s)
- Added warning_threshold_hours and escalation_action columns to ActivityTemplate
- Added is_escalated and deadline_warning_sent columns to WorkItem
- Exported Notification, DomainEvent, Rendition, VirtualDocument, VirtualDocumentChild, RetentionPolicy, DocumentRetention, LegalHold from app.models

## Task Commits

Each task was committed atomically:

1. **Task 1: Mount missing routers and import event handlers in main.py** - `8c1ee1c` (feat)
2. **Task 2: Register notification task in Celery and add missing model columns** - `947a320` (feat)

## Files Created/Modified
- `src/app/main.py` - Added 5 router imports, 5 include_router calls, event_handlers import in lifespan
- `src/app/celery_app.py` - Added notification task to include list and beat schedule entry
- `src/app/models/workflow.py` - Added 4 ORM columns across ActivityTemplate and WorkItem
- `src/app/models/__init__.py` - Added 8 model class imports and __all__ entries

## Decisions Made
- Mounted all 5 routers using settings.api_v1_prefix for consistency with existing pattern
- Event handlers imported in lifespan startup (not at module level) to ensure app is configured first
- Beat schedule interval of 60 seconds for deadline checking per plan specification

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All routers now reachable via API endpoints
- Event handlers will fire on domain events at runtime
- Celery workers will discover notification tasks
- Ready for 24-02 (Alembic migration) and 24-03 (integration smoke tests)

## Self-Check: PASSED

- All 4 modified files exist on disk
- Commit 8c1ee1c (Task 1) found in git log
- Commit 947a320 (Task 2) found in git log

---
*Phase: 24-infrastructure-wiring-event-bus*
*Completed: 2026-04-07*
