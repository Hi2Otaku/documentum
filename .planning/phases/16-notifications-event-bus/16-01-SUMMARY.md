---
phase: "16"
plan: "01"
subsystem: notifications-event-bus
tags: [event-bus, notifications, domain-events, in-app-notifications]
dependency_graph:
  requires: []
  provides: [event-bus, notification-service, notification-api, notification-ui]
  affects: [engine-service, document-service, lifecycle-service, sidebar]
tech_stack:
  added: []
  patterns: [event-bus-singleton, handler-registration-decorator, polling-unread-count]
key_files:
  created:
    - src/app/models/event.py
    - src/app/models/notification.py
    - src/app/services/event_bus.py
    - src/app/services/notification_service.py
    - src/app/services/event_handlers.py
    - src/app/routers/notifications.py
    - src/app/schemas/notification.py
    - alembic/versions/phase16_001_events_notifications.py
    - frontend/src/api/notifications.ts
    - frontend/src/components/layout/NotificationBell.tsx
  modified:
    - src/app/models/__init__.py
    - src/app/main.py
    - src/app/services/engine_service.py
    - src/app/services/document_service.py
    - src/app/services/lifecycle_service.py
    - frontend/src/components/layout/Sidebar.tsx
decisions:
  - "DomainEvent uses a minimal schema (not BaseModel) since events are append-only and never soft-deleted"
  - "EventBus is an in-process singleton with handler registration via @event_bus.on() decorator"
  - "Work item assignment events emitted after flush by querying new AVAILABLE work items, avoiding modification of 5+ creation points"
  - "NotificationBell polls every 30s for unread count rather than using WebSocket (adequate for v1.2)"
metrics:
  duration: 8m
  completed: "2026-04-06T15:38:00Z"
  tasks_completed: 5
  files_created: 10
  files_modified: 6
---

# Phase 16 Plan 01: Event Bus & In-App Notifications Summary

**Domain event bus with persistent storage and in-app notification system with bell UI**

## What Was Built

### Domain Event Infrastructure
- **DomainEvent model** (`src/app/models/event.py`): Append-only event record with event_type, entity_type, entity_id, actor_id, payload (JSON), created_at. Indexed on event_type, entity_type, and created_at.
- **EventBus service** (`src/app/services/event_bus.py`): In-process async event bus that persists events to the database and dispatches to registered handlers. Supports decorator-based registration (`@event_bus.on("event.type")`) and imperative subscription.

### Notification System
- **Notification model** (`src/app/models/notification.py`): Standard BaseModel with user_id, title, message, notification_type, is_read, entity_type, entity_id.
- **NotificationService** (`src/app/services/notification_service.py`): CRUD operations -- create, list (paginated with is_read filter), mark_read, mark_all_read, get_unread_count.
- **Event handlers** (`src/app/services/event_handlers.py`): Auto-create notifications on `work_item.assigned` and `work_item.delegated` events.

### API Endpoints
- `GET /api/v1/notifications/` -- paginated list with is_read filter
- `GET /api/v1/notifications/unread-count` -- unread badge count
- `PUT /api/v1/notifications/{id}/read` -- mark single as read
- `PUT /api/v1/notifications/mark-all-read` -- bulk mark as read

### Event Emission Points
- `workflow.started` -- on workflow instantiation
- `workflow.completed` -- when workflow reaches FINISHED state
- `work_item.assigned` -- for each new work item with a performer
- `work_item.completed` -- on work item completion
- `work_item.delegated` -- during delegation resolution
- `document.uploaded` -- on document upload
- `lifecycle.changed` -- on lifecycle state transition

### Frontend
- **NotificationBell component** with bell icon, unread count badge (destructive red), dropdown showing recent notifications with mark-read and mark-all-read.
- Integrated into desktop sidebar and mobile top bar.
- 30-second polling interval for unread count updates.

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **DomainEvent uses minimal schema**: Events are append-only (no soft-delete, no updated_at). Extends Base directly instead of BaseModel.
2. **In-process event bus**: Handlers run synchronously within the same database transaction, ensuring consistency. Future phases can add async dispatch if needed.
3. **Work item assignment event strategy**: Rather than modifying 5+ work item creation points in the engine, events are emitted after the final flush by querying new AVAILABLE work items.
4. **Polling over WebSocket for notifications**: 30-second TanStack Query polling is adequate for the current use case; avoids WebSocket complexity.

## Known Stubs

None -- all data flows are wired end-to-end.

## Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Domain Event model and event bus service | b20ccbd | event.py, notification.py, event_bus.py, migration |
| 2 | Notification service and event handlers | 896adf0 | notification_service.py, event_handlers.py, schemas |
| 3 | Notifications API router | 3ad47c1 | notifications.py router, main.py |
| 4 | Event emission integration | 8cd0e03 | engine_service.py, document_service.py, lifecycle_service.py |
| 5 | Notification bell UI | 75d99d9 | NotificationBell.tsx, notifications.ts, Sidebar.tsx |

## Self-Check: PASSED

All 10 created files verified. All 5 commit hashes verified.
