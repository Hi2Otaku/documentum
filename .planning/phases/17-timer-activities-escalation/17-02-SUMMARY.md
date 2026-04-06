---
phase: 17-timer-activities-escalation
plan: 02
subsystem: workflow-engine
tags: [celery, deadlines, escalation, notifications, timer]

requires:
  - phase: 17-01
    provides: "ActivityTemplate deadline columns (expected_duration_hours, escalation_action, warning_threshold_hours) and WorkItem fields (due_date, priority, is_escalated, deadline_warning_sent)"
provides:
  - "_compute_due_date helper wired into all 7 WorkItem constructor sites in engine_service.py"
  - "Fully implemented deadline checker Celery task with overdue detection and approaching-deadline warnings"
  - "_escalate_work_item with priority_bump, reassign, and notify escalation actions"
  - "Dedup flags (is_escalated, deadline_warning_sent) prevent repeated escalation/warnings"
affects: [17-timer-activities-escalation, dashboard, inbox]

tech-stack:
  added: []
  patterns:
    - "_compute_due_date pattern: centralized due_date calculation from activity template config"
    - "Deadline checker pattern: periodic Celery Beat task queries overdue + approaching items via joined query"
    - "Escalation action dispatch: strategy pattern with priority_bump/reassign/notify"

key-files:
  created: []
  modified:
    - "src/app/services/engine_service.py"
    - "src/app/tasks/notification.py"
    - "src/app/services/template_service.py"
    - "src/tests/test_timer_escalation.py"

key-decisions:
  - "Default warning threshold is 25% of expected_duration_hours when warning_threshold_hours is not set"
  - "Priority bump decreases priority by 2, clamped at minimum 1"
  - "Reassign escalation falls back to notify if no workflow supervisor is configured"

patterns-established:
  - "Joined query pattern: WorkItem -> ActivityInstance -> ActivityTemplate for deadline checking"
  - "Session factory mock pattern: _FakeFactory/_FakeSessionCM classes for testing Celery async tasks"

requirements-completed: [TIMER-02, TIMER-03, TIMER-04, NOTIF-03]

duration: 9min
completed: 2026-04-06
---

# Phase 17 Plan 02: Deadline Enforcement and Escalation Summary

**Due date computation wired into all 7 WorkItem creation sites; deadline checker finds overdue items for priority_bump/reassign/notify escalation and sends approaching-deadline warning notifications every 5 minutes via Celery Beat.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-06T16:32:59Z
- **Completed:** 2026-04-06T16:42:17Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

### Task 1: Wire due_date computation into engine service WorkItem creation
- Added `_compute_due_date(activity_template)` helper that returns `now + timedelta(hours=expected_duration_hours)` or `None`
- Wired `due_date=_compute_due_date(target_at)` into all 7 WorkItem constructor sites:
  - Queue performer, sequential performer, runtime selection, standard performer
  - Sequential next-performer (complete flow), sequential reject (previous performer)
  - Reject flow re-routing work items
- **Commit:** c9de1ff

### Task 2: Implement deadline checker and escalation logic in Celery task
- Replaced placeholder `_check_deadlines_async` with full implementation:
  - Approaching deadline warnings: queries active work items within warning threshold, creates notifications, sets `deadline_warning_sent=True`
  - Overdue escalation: queries overdue items, dispatches `_escalate_work_item`, sets `is_escalated=True`
- `_escalate_work_item` supports three actions:
  - `priority_bump`: decreases priority by 2 (clamped at 1)
  - `reassign`: moves work item to workflow supervisor (falls back to notify if none)
  - `notify`: creates escalation notification only
- Fixed `template_service.add_activity` to pass deadline fields to ActivityTemplate constructor (Rule 1 bug fix -- fields existed in schema but weren't persisted)
- 5 passing tests covering API config, due_date computation, overdue detection, priority bump, and approaching deadline notification
- **Commit:** 5304377

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed template_service.add_activity not passing deadline fields**
- **Found during:** Task 2 (test_activity_template_deadline_config failed)
- **Issue:** `template_service.add_activity()` was not passing `expected_duration_hours`, `escalation_action`, `warning_threshold_hours` to the ActivityTemplate constructor, even though the schema and model supported them
- **Fix:** Added the three deadline fields to the ActivityTemplate constructor call in `template_service.py`
- **Files modified:** src/app/services/template_service.py
- **Commit:** 5304377

## Known Stubs

None -- all functionality is fully wired.

## Verification Results

- `grep -c "due_date=_compute_due_date" src/app/services/engine_service.py` = 7
- `grep -c "def _escalate_work_item" src/app/tasks/notification.py` = 1
- `grep -c "def _check_deadlines_async" src/app/tasks/notification.py` = 1
- `grep -c "No deadline checking configured" src/app/tasks/notification.py` = 0 (placeholder removed)
- `python -m pytest src/tests/test_timer_escalation.py -x -q` = 5 passed

## Self-Check: PASSED
