---
phase: 16-notifications-event-bus
verified: 2026-04-06T18:00:00Z
status: human_needed
score: 8/8 requirements verified
re_verification:
  previous_status: gaps_found
  previous_score: 6/8 requirements verified
  gaps_closed:
    - "NOTIF-04: send_notification_email.delay(str(notification.id)) now called in both _notify_work_item_assigned and _notify_work_item_delegated handlers in event_handlers.py (lines 40, 64)"
    - "NOTIF-05 real-time: await r.publish('notifications', payload) added in notification_service.create_notification() at line 64, after db.flush(); payload includes user_id for SSE generator filter"
    - "NOTIF-03 remapped: REQUIREMENTS.md table updated — NOTIF-03 row now shows Phase 17 / Pending; inline description annotated with deferral reason"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Notification Bell visual and real-time badge increment"
    expected: "Bell icon visible in expanded sidebar, popover opens on click, badge increments without page refresh when a work item is assigned, Sonner toast fires"
    why_human: "Visual rendering, SSE connection lifecycle, and Sonner toast behavior require a running browser"
  - test: "Mark-read interactions and badge clearing"
    expected: "Clicking a notification row transitions it from unread (blue dot + bold) to read styling; Mark all read clears all dots and removes bell badge"
    why_human: "CSS state transitions and badge clearing require browser rendering"
  - test: "SSE real-time new_notification push"
    expected: "After triggering a task assignment, a new_notification SSE event appears in the network tab within ~1 second followed by an updated unread_count event"
    why_human: "Live SSE event inspection requires running stack with Redis"
  - test: "Email delivery on task assignment"
    expected: "Celery worker executes send_notification_email task and delivers email rendered from task_assigned.html template to performer's address"
    why_human: "Requires running Celery worker and SMTP server (e.g., Mailpit) to inspect"
---

# Phase 16: Notifications & Event Bus Verification Report

**Phase Goal:** Users receive timely in-app and email notifications for workflow events, and the system has a durable event bus that all subsequent features build on
**Verified:** 2026-04-06T18:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (previous status: gaps_found, score 6/8)

## Re-Verification Summary

All three gaps from the initial verification have been closed. No regressions found on previously-passing items.

| Gap | Previous | Now | Fix Applied |
|-----|----------|-----|-------------|
| NOTIF-04: Email dispatch missing | FAILED | VERIFIED | `send_notification_email.delay(str(notification.id))` added in both handlers in `event_handlers.py` (lines 40, 64) |
| NOTIF-05 real-time: No Redis publisher | FAILED | VERIFIED | `await r.publish("notifications", payload)` added in `notification_service.create_notification()` (line 64) after `db.flush()` |
| NOTIF-03 orphaned in REQUIREMENTS.md | FAILED | VERIFIED | REQUIREMENTS.md table updated: NOTIF-03 row shows Phase 17 / Pending; inline description annotated with deferral reason |

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Domain events are persisted when workflow, document, and lifecycle state changes occur (EVENT-01, EVENT-02) | VERIFIED | `event_bus.emit()` in `engine_service.py` (5 sites), `document_service.py` (1), `lifecycle_service.py` (1); `DomainEvent` flushed to DB in `emit()`; migration creates `domain_events` table |
| 2 | User receives in-app notification when a work item is assigned (NOTIF-01) | VERIFIED | `@event_bus.on("work_item.assigned")` in `event_handlers.py` creates notification via `notification_service.create_notification()` |
| 3 | User receives in-app notification when a task is delegated (NOTIF-02) | VERIFIED | `@event_bus.on("work_item.delegated")` in `event_handlers.py` creates notification |
| 4 | User receives email for task assignment/delegation events (NOTIF-04) | VERIFIED | `send_notification_email.delay(str(notification.id))` dispatched in both handlers (lines 40, 64 of `event_handlers.py`) |
| 5 | SSE stream pushes new_notification events and updated unread count to connected clients in real-time | VERIFIED | `notification_service.create_notification()` publishes JSON payload (including `user_id`) to Redis `notifications` channel at line 64; SSE generator subscribes and filters by `user_id` at line 155; sends `new_notification` then re-queries DB for updated `unread_count` at lines 159-163 |
| 6 | User can view notification list with unread count badge (NOTIF-05) | VERIFIED | `GET /notifications`, `GET /notifications/unread-count` endpoints wired; `NotificationBell` renders badge via `useNotificationSSE`; integrated into `SidebarUserMenu` |
| 7 | User can mark notifications as read individually or in bulk (NOTIF-06) | VERIFIED | `PATCH /{id}/read` and `PATCH /read-all` endpoints implemented; `NotificationItem` calls `onMarkRead` on click; `NotificationPopover` has "Mark all read" with `useMutation` |
| 8 | NOTIF-03 correctly deferred to Phase 17 in REQUIREMENTS.md | VERIFIED | REQUIREMENTS.md table: NOTIF-03 row shows Phase 17 / Pending; inline description annotated "deferred to Phase 17 — requires WorkItem.due_date" |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/app/models/event.py` | DomainEvent SQLAlchemy model | VERIFIED | DomainEvent with event_type, entity_type, entity_id, actor_id, payload (JSON), created_at |
| `src/app/models/notification.py` | Notification SQLAlchemy model | VERIFIED | Notification with user_id, title, message, notification_type, is_read, entity_type, entity_id |
| `src/app/services/event_bus.py` | EventBus with emit() and get_events() | VERIFIED | Singleton event_bus, emit() persists + dispatches handlers |
| `src/app/services/notification_service.py` | CRUD + Redis publish for notifications | VERIFIED | create_notification publishes to Redis after db.flush(); list, unread-count, mark-read, mark-all-read all present |
| `src/app/services/event_handlers.py` | Event-driven notification creation + email dispatch | VERIFIED | Handlers for work_item.assigned and work_item.delegated; both dispatch send_notification_email.delay() |
| `src/app/routers/notifications.py` | REST + SSE endpoints | VERIFIED | GET /, GET /unread-count, PATCH /{id}/read, PATCH /read-all, GET /stream all present and wired |
| `src/app/routers/events.py` | Admin event query endpoint | VERIFIED | GET / with filters, admin-only auth |
| `src/app/tasks/notification.py` | Celery email task + deadline beat task | VERIFIED | send_notification_email is reachable via .delay() calls in event_handlers.py; check_approaching_deadlines is intentional Phase 17 placeholder |
| `src/app/templates/email/task_assigned.html` | Jinja2 email template | VERIFIED | Contains {{ title }}, {{ username }}, {{ message }} |
| `src/app/templates/email/deadline_approaching.html` | Jinja2 email template | VERIFIED | Contains {{ title }}, {{ username }}, {{ message }}, orange heading |
| `src/app/schemas/notification.py` | Pydantic response schemas | VERIFIED | NotificationResponse, NotificationListResponse, UnreadCountResponse with from_attributes |
| `src/app/schemas/event.py` | Pydantic DomainEventResponse | VERIFIED | DomainEventResponse with all fields, from_attributes |
| `alembic/versions/phase16_001_events_notifications.py` | DB migration | VERIFIED | Creates domain_events and notifications tables |
| `frontend/src/api/notifications.ts` | API client functions | VERIFIED | fetchNotifications, fetchUnreadCount, markNotificationRead, markAllNotificationsRead |
| `frontend/src/hooks/useNotificationSSE.ts` | SSE hook | VERIFIED | useNotificationSSE with EventSource, unread_count and new_notification listeners, reconnect logic |
| `frontend/src/components/notifications/NotificationBell.tsx` | Bell icon with badge | VERIFIED | Bell icon, unread badge, useNotificationSSE, Sonner toast on new_notification, dedup via ref |
| `frontend/src/components/notifications/NotificationPopover.tsx` | Notification dropdown | VERIFIED | Popover with useQuery(fetchNotifications), useMutation for mark-read and mark-all-read |
| `frontend/src/components/notifications/NotificationItem.tsx` | Single notification row | VERIFIED | Renders title, message, time-ago, blue dot for unread, click-to-mark-read |
| `frontend/src/components/ui/popover.tsx` | shadcn Popover component | VERIFIED | Popover, PopoverTrigger, PopoverContent exports present |
| `frontend/src/components/layout/SidebarUserMenu.tsx` | Bell integrated in sidebar | VERIFIED | NotificationBell imported, rendered with !isCollapsed guard |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/app/main.py` | `src/app/routers/notifications.py` | include_router | WIRED | Line 94 |
| `src/app/main.py` | `src/app/routers/events.py` | include_router | WIRED | Line 95 |
| `src/app/main.py` | `src/app/services/event_handlers.py` | lifespan import | WIRED | Line 45: `import app.services.event_handlers  # noqa: F401` |
| `src/app/routers/notifications.py` | `src/app/services/notification_service.py` | service calls | WIRED | list_notifications, get_unread_count, mark_read, mark_all_read all called |
| `src/app/services/engine_service.py` | `src/app/services/event_bus.py` | emit() | WIRED | 5 call sites: workflow.started, workflow.completed, work_item.delegated, work_item.assigned, work_item.completed |
| `src/app/services/document_service.py` | `src/app/services/event_bus.py` | emit() | WIRED | document.uploaded |
| `src/app/services/lifecycle_service.py` | `src/app/services/event_bus.py` | emit() | WIRED | lifecycle.changed |
| `src/app/services/event_handlers.py` | `src/app/tasks/notification.py` | send_notification_email.delay() | WIRED | Lines 39-40 and 63-64 — both handlers dispatch after notification creation |
| `src/app/services/notification_service.py` | Redis 'notifications' channel | r.publish() | WIRED | Line 64 — publishes JSON payload with user_id after db.flush() |
| SSE generator in `src/app/routers/notifications.py` | Redis 'notifications' channel | pubsub.subscribe() + user_id filter | WIRED | Lines 134, 155 — subscribes and routes per user; re-queries unread count at lines 159-163 |
| `frontend/src/components/notifications/NotificationBell.tsx` | `frontend/src/hooks/useNotificationSSE.ts` | useNotificationSSE() | WIRED | Line 9: `const { unreadCount, latestNotification } = useNotificationSSE()` |
| `frontend/src/components/notifications/NotificationPopover.tsx` | `frontend/src/api/notifications.ts` | useQuery/useMutation | WIRED | fetchNotifications, markNotificationRead, markAllNotificationsRead all used |
| `frontend/src/components/layout/SidebarUserMenu.tsx` | `frontend/src/components/notifications/NotificationBell.tsx` | component render | WIRED | !isCollapsed guard confirmed |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `NotificationBell.tsx` | unreadCount (initial) | useNotificationSSE SSE unread_count event — SSE generator queries `get_unread_count()` on connect | Yes — DB query at SSE generator line 128 | FLOWING |
| `NotificationBell.tsx` | unreadCount (incremental) | SSE unread_count event triggered after each Redis message — generator re-queries `get_unread_count()` at lines 159-163 | Yes — fresh DB query per notification | FLOWING |
| `NotificationBell.tsx` | latestNotification (toast trigger) | SSE new_notification event from Redis publish in `create_notification()` at line 64 | Yes — Redis payload populated from flushed Notification object | FLOWING |
| `NotificationPopover.tsx` | notifications list | useQuery fetchNotifications GET /notifications `list_notifications()` DB query | Yes — paginated DB query | FLOWING |
| SSE generator user_id filter | data.user_id | JSON payload from `create_notification()` includes `"user_id": str(user_id)` at notification_service.py line 56 | Yes — matches the authenticated user's UUID | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED — all relevant spot-checks require a running Docker stack (FastAPI + PostgreSQL + Redis + Celery). The fixed gaps (dispatch call sites and Redis publish) are directly visible in source and verified by static inspection.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EVENT-01 | 16-01, 16-02 | System emits domain events on document upload, lifecycle change, workflow transitions | SATISFIED | event_bus.emit() in engine_service (5), document_service (1), lifecycle_service (1) |
| EVENT-02 | 16-01 | Events persisted in durable event table | SATISFIED | DomainEvent model + migration + db.flush() in emit() |
| NOTIF-01 | 16-01 | In-app notification on work item assigned | SATISFIED | @event_bus.on("work_item.assigned") creates notification |
| NOTIF-02 | 16-01 | In-app notification on task delegated | SATISFIED | @event_bus.on("work_item.delegated") creates notification |
| NOTIF-03 | Phase 17 (remapped) | Notification when work item deadline approaching | CORRECTLY DEFERRED | REQUIREMENTS.md table shows Phase 17 / Pending; check_approaching_deadlines is intentional placeholder; not a Phase 16 gap |
| NOTIF-04 | 16-02 | Email notification for task assignment and deadline events | SATISFIED | send_notification_email.delay() dispatched in both event handlers |
| NOTIF-05 | 16-01, 16-02, 16-03 | View notification list with unread count badge | SATISFIED | REST endpoints + SSE endpoint + NotificationBell all wired; Redis publish path now complete |
| NOTIF-06 | 16-01, 16-02, 16-03 | Mark notifications read individually or in bulk | SATISFIED | PATCH endpoints + frontend useMutation calls verified |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/app/tasks/notification.py` | check_approaching_deadlines body | Logs "not configured yet", no DB query | Info | Intentional Phase 17 placeholder — WorkItem.due_date not yet modeled; documented |

No blocker anti-patterns remain. The previously-blocker patterns (missing .delay() call, missing Redis publish) are resolved.

### Human Verification Required

#### 1. Notification Bell Visual and Real-Time Badge Increment

**Test:** Start the full stack, log in, ensure the sidebar is expanded. Verify the bell icon appears next to the user menu. Trigger a workflow that assigns a work item to the logged-in user. Verify the unread badge increments without a page refresh and a Sonner toast appears within ~1 second.
**Expected:** Bell visible in sidebar, badge increments in real-time, toast fires on assignment
**Why human:** Visual rendering, SSE connection lifecycle, and Sonner toast behavior require a running browser

#### 2. Mark-Read Interactions and Badge Clearing

**Test:** With at least one unread notification in the popover, click a notification row and verify it transitions from bold/blue-dot to read styling. Then click "Mark all read" and verify all items transition and the bell badge disappears.
**Expected:** Individual mark-read and bulk mark-all-read both update styles and clear badge
**Why human:** CSS state transitions and badge clearing require browser rendering

#### 3. SSE Real-Time new_notification Push

**Test:** Open the app in a browser with the network tab open. Confirm the SSE connection to `/api/v1/notifications/stream` is established (status 200, content-type text/event-stream). Trigger a task assignment, then verify a `new_notification` SSE event appears in the network tab within ~1 second followed by an updated `unread_count` event.
**Expected:** Two SSE events per assignment: new_notification then unread_count
**Why human:** Live SSE event inspection requires a running stack with Redis

#### 4. Email Delivery on Task Assignment

**Test:** With Celery worker and SMTP server (e.g., Mailpit) running, trigger a workflow that assigns a work item. Check the Celery worker log for task execution and the SMTP inbox for the received email. Verify the email renders the task_assigned.html template with correct title and username.
**Expected:** Email delivered to performer's address within ~5 seconds of assignment; template rendered correctly
**Why human:** Email delivery requires running Celery worker and SMTP server inspection

### Gaps Summary

No gaps remain. All three previously-identified gaps are closed:

**Gap 1 (NOTIF-04 — email dispatch):** `send_notification_email.delay(str(notification.id))` is now called at lines 40 and 64 of `event_handlers.py`, immediately after the in-app notification is created and flushed. The import is done inline to avoid circular imports.

**Gap 2 (NOTIF-05 real-time — Redis publisher):** `notification_service.create_notification()` now publishes a JSON payload to the Redis `notifications` channel after `db.flush()`. The payload includes all fields required by the frontend (`id`, `user_id`, `title`, `message`, `notification_type`, `entity_type`, `entity_id`, `created_at`). The SSE generator's per-user filter at line 155 correctly routes by `user_id`. After forwarding the `new_notification` event, the generator re-queries the DB for a fresh `unread_count` and sends that as a separate event, keeping the badge accurate.

**Gap 3 (NOTIF-03 — REQUIREMENTS.md mapping):** REQUIREMENTS.md has been updated. The NOTIF-03 table row now reads Phase 17 / Pending, and the inline description includes the deferral annotation. No Phase 16 plan claims NOTIF-03; the requirement is correctly tracked for Phase 17.

All automated verification checks pass. Remaining open items are human-only: visual rendering, real-time SSE confirmation in a browser, and email delivery inspection.

---

_Verified: 2026-04-06T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
