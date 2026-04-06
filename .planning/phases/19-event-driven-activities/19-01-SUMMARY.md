---
phase: 19-event-driven-activities
plan: 01
subsystem: engine
tags: [event-driven, activity-type, event-bus, domain-events, workflow-engine]

# Dependency graph
requires:
  - phase: 16-notifications-event-bus
    provides: Domain event bus with persistent storage and handler registration
  - phase: 18-sub-workflows
    provides: ENGINE dispatch pattern for new ActivityTypes, _advance_from_activity
provides:
  - EVENT activity type enum value
  - event_type_filter and event_filter_config columns on ActivityTemplate
  - Engine dispatch for EVENT activities (stays ACTIVE, no work items)
  - Three event bus handlers completing EVENT activities on domain events
  - MISSING_EVENT_TYPE template validation rule
affects: [20-document-renditions, workflow-designer-ui]

# Tech tracking
tech-stack:
  added: []
  patterns: [event-driven activity completion via domain event bus handlers]

key-files:
  created:
    - alembic/versions/phase19_001_event_activities.py
    - tests/test_event_activities.py
  modified:
    - src/app/models/enums.py
    - src/app/models/workflow.py
    - src/app/schemas/template.py
    - src/app/services/engine_service.py
    - src/app/services/event_handlers.py
    - src/app/services/template_service.py

key-decisions:
  - "EVENT activities stay ACTIVE with no work items -- event bus handlers advance them"
  - "Three separate event handlers (document.uploaded, lifecycle.changed, workflow.completed) sharing _try_complete_event_activities helper"
  - "workflow.completed handler coexists with sub-workflow _resume_parent handler -- both register independently"
  - "_matches_filter uses string comparison for payload matching"

patterns-established:
  - "Event-driven activity pattern: engine leaves ACTIVE, event handler calls _advance_from_activity"
  - "_try_complete_event_activities shared handler queries ACTIVE EVENT activities with matching event_type_filter"

requirements-completed: [EVTACT-01, EVTACT-02, EVTACT-03]

# Metrics
duration: 14min
completed: 2026-04-06
---

# Phase 19 Plan 01: Event-Driven Activities Summary

**EVENT activity type with engine dispatch and 3 domain event handlers auto-completing activities on document.uploaded, lifecycle.changed, and workflow.completed events**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-06T12:31:15Z
- **Completed:** 2026-04-06T12:44:52Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- EVENT enum value added to ActivityType with event_type_filter and event_filter_config model columns
- Engine dispatch leaves EVENT activities ACTIVE without creating work items -- event bus handlers complete them
- Three event bus handlers auto-complete matching EVENT activities for document.uploaded, lifecycle.changed, and workflow.completed events
- Filter config support for narrowing event matching to specific payload attributes
- MISSING_EVENT_TYPE validation rejects EVENT activities without event_type_filter
- 10 integration tests covering all 3 EVTACT requirements

## Task Commits

Each task was committed atomically:

1. **Task 1: Model, migration, schemas, and enum for EVENT activity type** - `8e5a23e` (feat)
2. **Task 2: Engine dispatch and event bus handlers for EVENT activities** - `eb1513d` (feat)

## Files Created/Modified
- `src/app/models/enums.py` - Added EVENT = "event" to ActivityType enum
- `src/app/models/workflow.py` - Added event_type_filter (String) and event_filter_config (JSON) columns to ActivityTemplate
- `src/app/schemas/template.py` - Added event_type_filter and event_filter_config to Create/Update/Response schemas
- `alembic/versions/phase19_001_event_activities.py` - Migration adding enum value and two columns
- `src/app/services/template_service.py` - Added MISSING_EVENT_TYPE validation rule
- `src/app/services/engine_service.py` - Added EVENT case in _advance_from_activity dispatch
- `src/app/services/event_handlers.py` - Added _try_complete_event_activities, _matches_filter, and 3 event handlers
- `tests/test_event_activities.py` - 10 integration tests for EVTACT-01, EVTACT-02, EVTACT-03

## Decisions Made
- EVENT activities stay ACTIVE with no work items created -- the event bus handlers handle completion
- Three separate @event_bus.on() handlers for each supported event type, all delegating to shared _try_complete_event_activities helper
- The workflow.completed EVENT handler coexists with the sub-workflow _resume_parent_on_child_complete handler -- both register for the same event independently
- _matches_filter uses string comparison (str(actual) == str(expected)) for flexible payload matching

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- EVENT activity type is fully functional in the engine
- Designer UI support for EVENT nodes (event_type_filter configuration panel) needed in a separate plan if required
- All existing sub-workflow and workflow tests continue to pass

---
*Phase: 19-event-driven-activities*
*Completed: 2026-04-06*

## Self-Check: PASSED

All 8 files found. Commits 8e5a23e (Task 1) and eb1513d (Task 2) verified. 10/10 tests passing.
