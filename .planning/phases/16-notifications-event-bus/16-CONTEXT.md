# Phase 16: Notifications & Event Bus - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a durable domain event bus and notification system. The event bus persists events in a PostgreSQL table and emits via Redis pub/sub for real-time consumers. Notifications are created by event handlers and delivered in-app (REST API + SSE push) and via email (fastapi-mail). The frontend gets a notification bell in the sidebar header with unread count badge and a dropdown list with mark-read controls.

</domain>

<decisions>
## Implementation Decisions

### Event Bus Architecture
- Use a PostgreSQL `domain_events` table as the durable event store (not Redis-only — messages survive restarts)
- Emit events via a lightweight `event_bus.emit()` helper that inserts to DB and publishes to Redis pub/sub channel
- Event types: `document.uploaded`, `document.checked_in`, `lifecycle.changed`, `workflow.started`, `workflow.completed`, `workflow.halted`, `workitem.assigned`, `workitem.delegated`, `workitem.completed`
- Event payload: JSON with entity_id, entity_type, actor_id, timestamp, and type-specific data

### Notification Model & Storage
- `Notification` model extending BaseModel: user_id (FK), type (enum), title, message, entity_type, entity_id, is_read, read_at
- NotificationType enum: TASK_ASSIGNED, TASK_DELEGATED, DEADLINE_APPROACHING, WORKFLOW_COMPLETED, DOCUMENT_UPLOADED
- Notifications created by event handlers (not directly by business logic) — decoupled from workflow engine

### Notification Delivery
- In-app: REST API (GET /notifications, PATCH /notifications/{id}/read, PATCH /notifications/read-all)
- Real-time push: SSE endpoint (GET /notifications/stream) similar to existing dashboard SSE pattern
- Email: Use fastapi-mail with Jinja2 templates for task assignment and deadline notifications
- Email is async via Celery task (don't block API requests)

### Frontend UI
- Notification bell icon (lucide-react Bell) in SidebarUserMenu area
- Unread count badge (red circle with number)
- Dropdown popover with notification list (latest 20), mark-read button, "View all" link
- SSE connection from useEffect for real-time badge updates
- Toast notification via Sonner when new notification arrives while app is open

### Claude's Discretion
- Exact SSE reconnection strategy and heartbeat interval
- Email template styling and layout
- Notification retention/cleanup policy (if any)
- Whether to batch mark-read or individual only

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- SSE streaming pattern in dashboard.py (_sse_generator, _validate_sse_token)
- send_email auto method in auto_methods/builtin.py (SMTP config already exists)
- Sonner toast library already installed and configured in frontend
- BaseModel with soft delete, audit columns in models/base.py
- EnvelopeResponse schema for consistent API responses

### Established Patterns
- Async services with AsyncSession parameter
- Celery tasks with asyncio.run() wrapper and create_task_session_factory()
- String enums (str, enum.Enum) stored as VARCHAR
- UUID primary keys with uuid4 default
- Alembic migrations named phase{N}_{seq}

### Integration Points
- Router registration in main.py via include_router()
- Celery task include list in celery_app.py
- Beat schedule in celery_app.py for periodic tasks
- SidebarUserMenu.tsx for bell icon placement
- Redis already configured as Celery broker (pub/sub channel available)

</code_context>

<specifics>
## Specific Ideas

- Event bus is foundational — phases 17-20 all emit or consume domain events
- Notification bell goes next to the user avatar in the sidebar user menu
- Email uses existing SMTP settings from config.py (smtp_host, smtp_port, etc.)
- Follow existing dashboard SSE pattern for notification streaming

</specifics>

<deferred>
## Deferred Ideas

- Notification preferences (opt-in/out per type/channel) — deferred to future requirement NOTIF-07
- Push notifications via browser API — deferred to NOTIF-08
- WebSocket replacement for SSE — not needed for this milestone

</deferred>
