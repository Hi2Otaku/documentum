---
phase: 16-notifications-event-bus
plan: 04
subsystem: notifications
tags: [gap-closure, email, redis, sse, requirements]
dependency_graph:
  requires: [16-01, 16-02, 16-03]
  provides: [email-dispatch-wiring, redis-publish-wiring, notif-03-remap]
  affects: [notification-service, event-handlers, requirements-traceability]
tech_stack:
  added: []
  patterns: [lazy-redis-init, fire-and-forget-celery, redis-pubsub-for-sse]
key_files:
  created: []
  modified:
    - src/app/services/event_handlers.py
    - src/app/services/notification_service.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
decisions:
  - Redis publish placed in create_notification (covers all paths) rather than per-handler
  - Celery import inside handler function to avoid circular imports
  - NOTIF-03 deferred to Phase 17 rather than removed
metrics:
  duration: 2m
  completed: 2026-04-06
  tasks: 2
  files_modified: 4
---

# Phase 16 Plan 04: Gap Closure -- Email Dispatch, Redis Publish, NOTIF-03 Remap Summary

Wire email dispatch and Redis pub/sub publish into the notification creation pipeline, completing the end-to-end delivery chain for both email and SSE real-time notifications.

## What Was Done

### Task 1: Wire email dispatch and Redis publish into notification pipeline
**Commit:** `6889431`

**Part A -- Redis publish in notification_service.py:**
- Added `json` and `redis.asyncio` imports
- Added lazy-initialized `_redis_client` with `_get_redis()` async helper
- After `db.flush()` in `create_notification()`, added Redis publish to `"notifications"` channel with full notification payload (id, user_id, title, message, notification_type, entity_type, entity_id, created_at)
- Redis publish failure is caught and logged without breaking notification creation

**Part B -- Email dispatch in event_handlers.py:**
- Changed bare `await notification_service.create_notification(...)` to `notification = await ...` in both handlers
- Added `send_notification_email.delay(str(notification.id))` after notification creation in `_notify_work_item_assigned` and `_notify_work_item_delegated`
- Import placed inside function body to avoid circular imports

### Task 2: Remap NOTIF-03 from Phase 16 to Phase 17
**Commit:** `2596a18`

- Added deferral note to NOTIF-03 requirement: "*(deferred to Phase 17 -- requires WorkItem.due_date)*"
- Updated traceability table: NOTIF-03 phase changed from "Phase 16" to "Phase 17"
- Added NOTIF-03 to Phase 17 requirements list in ROADMAP.md

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None. All wiring is complete for the notification delivery pipeline.

## Decisions Made

1. **Redis publish in create_notification vs per-handler**: Placing Redis publish inside `create_notification()` ensures ALL notification creation paths (not just event handlers) trigger SSE delivery. This is more robust than duplicating publish calls in each handler.
2. **Celery import inside function**: The `from app.tasks.notification import send_notification_email` import is placed inside the handler function body to avoid circular import chains (Celery tasks import models which may trigger circular dependencies at module level).
3. **NOTIF-03 deferred, not removed**: NOTIF-03 (deadline approaching notification) depends on `WorkItem.due_date` which does not exist yet. Rather than removing it, we deferred it to Phase 17 where the timer/deadline infrastructure will be built.

## Verification Results

- `grep -c "send_notification_email.delay" event_handlers.py` = 2 (one per handler)
- `grep -c "publish" notification_service.py` = 2 (publish call + log message)
- `grep "NOTIF-03.*Phase 17" REQUIREMENTS.md` = match in traceability table
- `grep "NOTIF-03.*deferred" REQUIREMENTS.md` = match with deferral note
- `grep "NOTIF-03, TIMER-01" ROADMAP.md` = match in Phase 17 requirements

## Self-Check: PASSED

All files exist. All commits verified.
