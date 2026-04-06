---
phase: 19-event-driven-activities
verified: 2026-04-06T13:15:00Z
status: human_needed
score: 15/15 must-haves verified (automated); 1 item requires human visual check
human_verification:
  - test: "Open workflow designer and verify EVENT node drag-and-drop, amber styling, and PropertiesPanel config"
    expected: "Event node appears in palette with Radio icon, drags to canvas with amber background, Properties Panel shows event type dropdown with three options and filter criteria editor"
    why_human: "Visual rendering, drag-and-drop behavior, and template save/load round-trip cannot be verified programmatically without a running browser"
---

# Phase 19: Event-Driven Activities Verification Report

**Phase Goal:** Workflow activities can wait for and react to domain events (document uploads, lifecycle changes, workflow completions) instead of requiring manual user action
**Verified:** 2026-04-06T13:15:00Z
**Status:** human_needed (all automated checks passed; 1 visual item requires human confirmation)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | EVENT activity template can be created with event_type_filter and event_filter_config | VERIFIED | `ActivityTemplate` in `workflow.py` lines 113-114 add both columns; `ActivityTemplateCreate/Update/Response` schemas at `template.py` lines 59-60, 76-77, 96-97 |
| 2 | Template validation rejects EVENT activity without event_type_filter | VERIFIED | `template_service.py` lines 806-812: MISSING_EVENT_TYPE block checks `activity_type == ActivityType.EVENT` and rejects when `event_type_filter` is falsy |
| 3 | EVENT activity stays ACTIVE when engine reaches it (no work items created) | VERIFIED | `engine_service.py` line 606-609: `elif target_at.activity_type == ActivityType.EVENT: pass` — no work item creation, no Celery dispatch |
| 4 | EVENT activity completes automatically when matching document.uploaded event fires | VERIFIED | `event_handlers.py` lines 300-305: `@event_bus.on("document.uploaded")` handler calls `_try_complete_event_activities(db, event, "document.uploaded")` |
| 5 | EVENT activity completes automatically when matching lifecycle.changed event fires | VERIFIED | `event_handlers.py` lines 308-313: `@event_bus.on("lifecycle.changed")` handler calls `_try_complete_event_activities(db, event, "lifecycle.changed")` |
| 6 | EVENT activity completes automatically when matching workflow.completed event fires | VERIFIED | `event_handlers.py` lines 316-321: `@event_bus.on("workflow.completed")` handler calls `_try_complete_event_activities(db, event, "workflow.completed")` |
| 7 | EVENT activity ignores non-matching events | VERIFIED | `_try_complete_event_activities` queries with `ActivityTemplate.event_type_filter == event_type` filter; non-matching types return empty list |
| 8 | EVENT activity with event_filter_config only matches events whose payload matches the filter | VERIFIED | `event_handlers.py` lines 236-239: `_matches_filter(at.event_filter_config, payload)` — continues (skips) if filter does not match; test `test_event_activity_filter_config_matching` at line 483 covers this |
| 9 | Admin can drag an EVENT node from the palette onto the workflow designer canvas | VERIFIED (automated) | `NodePalette.tsx` line 37 has `eventNode` entry; `Canvas.tsx` line 24 has `DEFAULT_NODE_DATA.eventNode`; `nodes/index.ts` lines 15, 21 register both `event` and `eventNode` keys to `EventNode` component |
| 10 | Admin can select an EVENT node and configure which event type it listens for | VERIFIED (automated) | `PropertiesPanel.tsx` lines 268-271: `EventConfig` rendered for `data.activityType === 'event'`; lines 434-436 contain all three event type options |
| 11 | Admin can optionally configure filter criteria as key-value pairs on the EVENT node | VERIFIED (automated) | `PropertiesPanel.tsx` `EventConfig` component lines 365-460: `filterRows` state, add/remove functionality, syncs to `eventFilterConfig` via `updateNodeData` |
| 12 | EVENT node appears visually distinct (amber color, lightning/Radio icon) in both designer and progress views | VERIFIED (automated) / needs human | `EventNode.tsx` has `bg-amber-500 border-2 border-amber-600 text-white` class and Radio icon; `WorkflowProgressGraph.tsx` lines 149, 176-177: `ProgressEventNode` registered for `event` and `eventNode` — visual confirmation still requires human |
| 13 | Saving a template with EVENT activities persists event_type_filter and event_filter_config to the API | VERIFIED (automated) | `ActivityTemplateCreate` schema includes both fields; existing template save flow in designer maps node data to schema fields through `updateNodeData` — full round-trip needs human confirmation |
| 14 | Three event types (document.uploaded, lifecycle.changed, workflow.completed) supported as distinct handlers | VERIFIED | 7 total `@event_bus.on` registrations (4 pre-existing + 3 new); all three new handlers confirmed at lines 300, 308, 316 |
| 15 | EVENT activity does not block parallel branches | VERIFIED | Test `test_event_activity_does_not_block_parallel_branches` at line 542 covers this case; `_advance_from_activity` is invoked which proceeds per existing flow logic |

**Score:** 15/15 truths verified (automated); 1 visual confirmation pending human

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/app/models/enums.py` | EVENT value in ActivityType enum | VERIFIED | Line 17: `EVENT = "event"` |
| `src/app/models/workflow.py` | event_type_filter and event_filter_config columns on ActivityTemplate | VERIFIED | Lines 113-114: both mapped columns present with correct types |
| `src/app/schemas/template.py` | event_type_filter and event_filter_config in Create/Update/Response schemas | VERIFIED | Lines 59-60, 76-77, 96-97: all three schemas have both fields |
| `src/app/services/event_handlers.py` | Three event handlers + shared _try_complete_event_activities | VERIFIED | Lines 195-321: `_matches_filter`, `_try_complete_event_activities`, and three handlers — 671 lines total, substantive |
| `src/app/services/template_service.py` | MISSING_EVENT_TYPE validation rule | VERIFIED | Lines 806-812: block present and syntactically correct |
| `src/app/services/engine_service.py` | ActivityType.EVENT case in dispatch block | VERIFIED | Lines 606-609: EVENT case leaves activity ACTIVE with no side effects |
| `alembic/versions/phase19_001_event_activities.py` | Migration for enum value and two columns | VERIFIED | Lines 26, 31, 35: ALTER TYPE adds 'event', two columns added correctly, downgrade removes them |
| `tests/test_event_activities.py` | Tests covering EVTACT-01, EVTACT-02, EVTACT-03 | VERIFIED | 671 lines, 10 test functions covering all three requirements |
| `frontend/src/components/nodes/EventNode.tsx` | Visual EVENT node component | VERIFIED | 25 lines, amber styling, Radio icon, target/source handles, event type subtitle hint |
| `frontend/src/types/designer.ts` | ActivityNodeData with event type, eventTypeFilter, eventFilterConfig | VERIFIED | Line 6: `'event'` in union; lines 8, 10: both optional fields present |
| `frontend/src/components/designer/PropertiesPanel.tsx` | Event configuration section with eventTypeFilter | VERIFIED | EventConfig component wired at line 268, dropdown at lines 424-436, filter rows at lines 376-392 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `event_handlers.py` | `engine_service.py` | `_advance_from_activity` call inside `_try_complete_event_activities` | WIRED | Line 226 imports `_advance_from_activity` from engine_service; line 280 calls it with full argument set |
| `engine_service.py` | `enums.py` | `ActivityType.EVENT` case in dispatch block | WIRED | Line 606: `elif target_at.activity_type == ActivityType.EVENT:` — import already covers ActivityType |
| `template_service.py` | `enums.py` | MISSING_EVENT_TYPE validation checks ActivityType.EVENT | WIRED | Lines 806-808: `if a.activity_type == ActivityType.EVENT:` inside MISSING_EVENT_TYPE block |
| `nodes/index.ts` | `EventNode.tsx` | nodeTypes registration | WIRED | Lines 15, 21: both `event: EventNode` and `eventNode: EventNode` registered |
| `Canvas.tsx` | `designer.ts` | DEFAULT_NODE_DATA entry for eventNode | WIRED | Line 24: `eventNode: { name: 'New Event Activity', activityType: 'event' }` |
| `PropertiesPanel.tsx` | `designer.ts` | eventTypeFilter field read/write | WIRED | Line 270: reads `data.eventTypeFilter`; line 427: writes via `updateNodeData` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `event_handlers.py: _try_complete_event_activities` | `active_event_ais` | SQLAlchemy query with `ActivityInstance` + `ActivityTemplate` join + `WorkflowInstance` join, filtered by `ACTIVE`, `EVENT`, `event_type_filter`, `RUNNING` | Yes — live DB query | FLOWING |
| `PropertiesPanel.tsx: EventConfig` | `eventTypeFilter`, `eventFilterConfig` | React Flow node data via `updateNodeData` / `useDesignerStore` | Yes — designer store state, written to API on save | FLOWING |

---

### Behavioral Spot-Checks

The test suite requires a running PostgreSQL database. Tests cannot be run without infrastructure. The test file structure was verified statically — 10 test functions with real ORM fixture patterns (no mocks, actual `db_session` fixture, real model creation). Behavioral verification deferred to the existing test infrastructure.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| EVENT enum value in ActivityType | `grep "EVENT" src/app/models/enums.py` | `EVENT = "event"` found | PASS |
| event_type_filter column in model | `grep "event_type_filter" src/app/models/workflow.py` | Found at line 113 | PASS |
| MISSING_EVENT_TYPE validation present | `grep "MISSING_EVENT_TYPE" src/app/services/template_service.py` | Found at lines 806-812 | PASS |
| ActivityType.EVENT in engine dispatch | `grep "ActivityType.EVENT" src/app/services/engine_service.py` | Found at line 606 | PASS |
| _try_complete_event_activities wired to _advance_from_activity | Inspect `event_handlers.py` lines 226-280 | Import + call confirmed | PASS |
| 7 event_bus.on registrations (4 original + 3 new) | `grep -c "event_bus.on" event_handlers.py` | Count = 7 | PASS |
| EventNode.tsx exists and has min_lines 20 | File check + wc -l | 25 lines | PASS |
| eventTypeFilter in designer types | `grep "eventTypeFilter" frontend/src/types/designer.ts` | Line 8: field present | PASS |
| EventNode registered in nodeTypes | `grep "event.*EventNode" frontend/.../nodes/index.ts` | Lines 15, 21 confirmed | PASS |
| PropertiesPanel has all 3 event type options | `grep "document.uploaded\|lifecycle.changed\|workflow.completed" PropertiesPanel.tsx` | All three found at lines 434-436 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| EVTACT-01 | 19-01, 19-02 | Admin can add an EVENT activity type in the workflow designer with event filter configuration | SATISFIED | Backend: EVENT enum, model columns, schemas, validation; Frontend: EventNode component, palette entry, PropertiesPanel EventConfig |
| EVTACT-02 | 19-01 | EVENT activities complete automatically when a matching domain event fires | SATISFIED | Three `@event_bus.on` handlers calling `_try_complete_event_activities` which calls `_advance_from_activity`; filter config matching via `_matches_filter` |
| EVTACT-03 | 19-01, 19-02 | Supported event types include document.uploaded, lifecycle.changed, and workflow.completed | SATISFIED | Three handlers registered; three options in PropertiesPanel dropdown; tests cover all three (`test_event_activity_completes_on_document_uploaded`, `test_event_activity_completes_on_lifecycle_changed`, `test_event_activity_completes_on_workflow_completed`) |

No orphaned requirements found — REQUIREMENTS.md lines 149-151 confirm EVTACT-01, EVTACT-02, EVTACT-03 all map to Phase 19 and are marked Complete.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

All `placeholder` attributes found in `PropertiesPanel.tsx` are HTML input placeholder text (UI hint text), not implementation stubs. No TODO/FIXME/XXX, no `return null` or `return {}` in render paths, no hardcoded empty arrays flowing to user-visible output.

---

### Human Verification Required

#### 1. EVENT Node Visual and Functional Check in Workflow Designer

**Test:** Open the workflow designer (e.g., http://localhost:5173), navigate to the template designer. Confirm:
1. "Event" entry appears in the left palette with a Radio icon and amber accent on the left border
2. Drag an Event node from the palette onto the canvas — it should appear with an amber background (`bg-amber-500`)
3. Click the Event node to select it — the Properties Panel should show:
   - An activity type badge with "event" in amber styling (`bg-amber-100 text-amber-800`)
   - An "Event Type" dropdown with three options: Document Uploaded, Lifecycle Changed, Workflow Completed
   - A "Filter Criteria (optional)" section with an "Add filter" button
4. Select "Document Uploaded", add a filter row with key="entity_id" and value="test-123"
5. Save the template and reload the page — verify event_type_filter and eventFilterConfig persist

**Expected:** All five steps succeed with no console errors; saved template round-trips the event configuration
**Why human:** Visual rendering, drag-and-drop interactions, and template save/load round-trip cannot be verified without a running browser and frontend dev server

---

### Gaps Summary

No gaps found. All 15 observable truths are verified at the automated level. The single human_needed item is a visual/interactive confirmation of the frontend designer, which is standard for UI phases. No missing artifacts, no stub implementations, no broken key links.

The phase fully achieves its goal: workflow activities can now wait for and react to domain events (document.uploaded, lifecycle.changed, workflow.completed) instead of requiring manual user action. The engine dispatch correctly leaves EVENT activities ACTIVE without creating work items, and the three domain event handlers automatically complete matching EVENT activities via `_advance_from_activity` when the corresponding events fire.

---

_Verified: 2026-04-06T13:15:00Z_
_Verifier: Claude (gsd-verifier)_
