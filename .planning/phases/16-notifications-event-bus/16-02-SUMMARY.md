---
phase: "16"
plan: "02"
subsystem: notifications-event-bus
tags: [notifications-api, sse-stream, email-notifications, celery-tasks, events-admin]
dependency_graph:
  requires: [event-bus, notification-service]
  provides: [notification-sse, notification-email, events-api, deadline-beat-task]
  affects: [celery-app, main-app]
tech_stack:
  added: [fastapi-mail, redis-pubsub-sse]
  patterns: [sse-streaming, celery-email-task, beat-schedule]
key_files:
  created:
    - src/app/routers/events.py
    - src/app/schemas/event.py
    - src/app/tasks/notification.py
    - src/app/templates/email/task_assigned.html
    - src/app/templates/email/deadline_approaching.html
  modified:
    - src/app/routers/notifications.py
    - src/app/services/event_bus.py
    - src/app/celery_app.py
    - src/app/main.py
decisions:
  - "SSE token validation for notifications allows all active users (not just admins)"
  - "Redis pub/sub channel 'notifications' used for SSE real-time delivery"
  - "Deadline beat task is a placeholder until Phase 17 adds due_date to WorkItem"
metrics:
  duration: "3m"
  completed: "2026-04-06"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 4
---

# Phase 16 Plan 02: Notification API, SSE Stream, Email Tasks Summary

**One-liner:** REST/SSE notification endpoints with Redis pub/sub streaming, Celery email delivery via fastapi-mail, events admin API, and deadline beat task placeholder.

## What Was Built

### Notification REST + SSE Endpoints (Task 1)
- Enhanced `notifications.py` router with PATCH `/read-all` and PATCH `/{id}/read` endpoints
- Added SSE stream at `/notifications/stream` using Redis pub/sub on the `notifications` channel
- SSE token validation allows any active user (not admin-restricted like dashboard SSE)
- Heartbeat sent every 30 seconds to keep connections alive
- SSE emits `unread_count` and `new_notification` events filtered by user_id

### Events Admin API (Task 1)
- New `events.py` router at `/events` (admin-only)
- Supports filtering by `event_type` and `entity_id` with pagination
- Added `get_events()` query function to event_bus module
- Created `DomainEventResponse` Pydantic schema

### Celery Email Task (Task 2)
- `send_notification_email` task with fastapi-mail integration, 3 retries, 60s delay
- Maps notification types to email templates: task_assigned, task_delegated -> task_assigned.html; deadline_approaching -> deadline_approaching.html
- Gracefully skips when SMTP not configured or user has no email
- Uses project Celery pattern (create_task_session_factory for isolated event loops)

### Deadline Beat Task (Task 2)
- `check_approaching_deadlines` runs every 5 minutes via Celery Beat
- Placeholder implementation -- Phase 17 will add due_date to WorkItem
- Registered in beat_schedule alongside existing poll and metrics tasks

### Email Templates (Task 2)
- `task_assigned.html` -- styled notification for task assignment/delegation
- `deadline_approaching.html` -- orange-themed deadline warning
- Both use Jinja2 variables: {{ title }}, {{ username }}, {{ message }}

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | b757c4a | Notification SSE stream, events admin endpoint, router registration |
| 2 | 0c5e35a | Celery email task, deadline beat task, email templates |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Added get_events() to event_bus module**
- Plan referenced `event_bus.get_events()` but this function did not exist in the Plan 01 output
- Added module-level async function with event_type and entity_id filtering
- File modified: src/app/services/event_bus.py

**2. [Rule 2 - Existing] event_bus.emit() already wired by Plan 01**
- Plan Task 2 instructed wiring emit() into document/lifecycle/engine services
- These calls were already present from Plan 01 execution (verified: 1+1+5 calls)
- Skipped redundant wiring -- no changes needed

**3. [Rule 1 - Bug] Changed PUT to PATCH for mark-read endpoints**
- Plan 01 used PUT methods; Plan 02 spec requires PATCH (correct REST semantics)
- Updated both mark-read and mark-all-read to use @router.patch

## Known Stubs

| File | Line | Stub | Reason |
|------|------|------|--------|
| src/app/tasks/notification.py | 120-122 | check_approaching_deadlines logs "not configured" | Phase 17 adds WorkItem.due_date; cannot query deadlines yet |

## Self-Check: PASSED
