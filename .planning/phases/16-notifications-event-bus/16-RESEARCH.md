# Phase 16: Notifications & Event Bus - Research

**Researched:** 2026-04-06
**Domain:** Domain event bus, in-app notifications, email notifications, SSE real-time push
**Confidence:** HIGH

## Summary

Phase 16 builds two foundational subsystems: (1) a durable domain event bus backed by PostgreSQL with Redis pub/sub for real-time fan-out, and (2) a notification system that creates, stores, delivers (in-app + email), and streams notifications to users. The event bus is critical infrastructure -- phases 17-20 all depend on it for timer escalation, sub-workflow completion, and event-driven activities.

The existing codebase already has established patterns for every building block: SSE streaming (dashboard.py), Celery tasks with async wrappers (auto_activity.py), SMTP config (config.py), Sonner toasts (frontend), and the BaseModel with soft delete/audit columns. The implementation is straightforward application of these patterns to the new domain.

**Primary recommendation:** Build the event bus as a thin module (`src/app/services/event_bus.py`) with `emit()` that inserts to `domain_events` table and publishes to Redis pub/sub. Notification handlers subscribe to relevant event types and create `Notification` records. Email dispatch goes through a Celery task. Frontend gets a popover-based notification bell using the existing SSE pattern.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- PostgreSQL `domain_events` table as durable event store (not Redis-only)
- `event_bus.emit()` helper that inserts to DB and publishes to Redis pub/sub
- Event types: `document.uploaded`, `document.checked_in`, `lifecycle.changed`, `workflow.started`, `workflow.completed`, `workflow.halted`, `workitem.assigned`, `workitem.delegated`, `workitem.completed`
- Event payload: JSON with entity_id, entity_type, actor_id, timestamp, type-specific data
- Notification model extending BaseModel: user_id (FK), type (enum), title, message, entity_type, entity_id, is_read, read_at
- NotificationType enum: TASK_ASSIGNED, TASK_DELEGATED, DEADLINE_APPROACHING, WORKFLOW_COMPLETED, DOCUMENT_UPLOADED
- Notifications created by event handlers (not directly by business logic)
- REST API: GET /notifications, PATCH /notifications/{id}/read, PATCH /notifications/read-all
- SSE endpoint: GET /notifications/stream (follows existing dashboard SSE pattern)
- Email via fastapi-mail with Jinja2 templates for task assignment and deadline notifications
- Email is async via Celery task
- Notification bell icon (lucide-react Bell) in SidebarUserMenu area
- Unread count badge (red circle with number)
- Dropdown popover with notification list (latest 20), mark-read button, "View all" link
- SSE connection from useEffect for real-time badge updates
- Toast notification via Sonner when new notification arrives

### Claude's Discretion
- Exact SSE reconnection strategy and heartbeat interval
- Email template styling and layout
- Notification retention/cleanup policy (if any)
- Whether to batch mark-read or individual only (decision: support both individual and bulk mark-read)

### Deferred Ideas (OUT OF SCOPE)
- NOTIF-07: Notification preferences (opt-in/out per type/channel)
- NOTIF-08: Push notifications via browser push API
- WebSocket replacement for SSE

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NOTIF-01 | User receives in-app notification when a work item is assigned | Event handler on `workitem.assigned` creates TASK_ASSIGNED notification |
| NOTIF-02 | User receives in-app notification when a task is delegated | Event handler on `workitem.delegated` creates TASK_DELEGATED notification |
| NOTIF-03 | User receives in-app notification when a deadline is approaching | Celery Beat periodic task checks work items with due_date approaching, emits `workitem.deadline_approaching` or creates notification directly |
| NOTIF-04 | User receives email notification for task assignment and deadline events | Celery task wrapping fastapi-mail sends email on TASK_ASSIGNED and DEADLINE_APPROACHING notifications |
| NOTIF-05 | User can view notification list with unread count badge in the UI | GET /notifications API + notification bell component with SSE-driven unread count |
| NOTIF-06 | User can mark notifications as read individually or in bulk | PATCH /notifications/{id}/read and PATCH /notifications/read-all endpoints |
| EVENT-01 | System emits domain events on document upload, lifecycle change, and workflow state transitions | event_bus.emit() calls inserted at document_service, lifecycle_service, engine_service |
| EVENT-02 | Events are persisted in a durable event table | DomainEvent model with PostgreSQL table, inserted on every emit() |

</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi-mail | 1.6.2 | Async email sending with Jinja2 templates | Already installed. Provides ConnectionConfig, MessageSchema, FastMail with async send_message(). Uses aiosmtplib under the hood. |
| redis (redis-py) | 6.4.0 | Redis pub/sub for real-time event fan-out | Already installed (Celery dependency). Use `redis.asyncio` for async pub/sub in SSE handlers. |
| SQLAlchemy | 2.0.x | DomainEvent and Notification models | Already the project ORM. Async sessions via asyncpg/aiosqlite. |
| Celery | 5.x | Email sending task + deadline check periodic task | Already configured with Beat scheduler. |
| sonner | 2.0.7 | Frontend toast notifications | Already installed and configured with `<Toaster />` in main.tsx. |
| lucide-react | 1.7.0 | Bell icon for notification indicator | Already installed. Use `Bell` icon. |

### New Dependencies Required
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @radix-ui/react-popover | latest | Notification dropdown popover | shadcn/ui Popover component for bell dropdown. Must be installed via `npx shadcn@latest add popover`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Redis pub/sub | PostgreSQL LISTEN/NOTIFY | PG LISTEN/NOTIFY also works but Redis is already the broker; using Redis keeps pub/sub concerns on one system. PG LISTEN/NOTIFY has payload size limits (8KB). |
| fastapi-mail | Raw smtplib (existing) | The existing send_email auto method uses raw smtplib. fastapi-mail adds Jinja2 template support and is already installed. Use fastapi-mail for notification emails. |
| SSE | WebSocket | SSE is simpler for one-way push (notifications are server-to-client only). Existing dashboard SSE pattern can be reused directly. |

**Installation:**
```bash
# Frontend only -- backend deps already installed
cd frontend && npx shadcn@latest add popover
```

## Architecture Patterns

### Recommended Project Structure
```
src/app/
  models/
    event.py          # DomainEvent model
    notification.py   # Notification model, NotificationType enum
  schemas/
    event.py          # DomainEventResponse schema
    notification.py   # NotificationResponse, NotificationList, MarkReadRequest
  services/
    event_bus.py      # emit(), subscribe(), get_events()
    notification_service.py  # create, list, mark_read, get_unread_count
  routers/
    notifications.py  # REST + SSE endpoints
    events.py         # Optional: GET /events for admin viewing
  tasks/
    notification.py   # send_notification_email Celery task, check_deadlines periodic task
  templates/
    email/
      task_assigned.html     # Jinja2 email template
      deadline_approaching.html

frontend/src/
  api/
    notifications.ts  # API client for notification endpoints
  hooks/
    useNotificationSSE.ts  # SSE hook (follows useDashboardSSE pattern)
  components/
    notifications/
      NotificationBell.tsx      # Bell icon + unread badge
      NotificationPopover.tsx   # Popover dropdown with list
      NotificationItem.tsx      # Single notification row
```

### Pattern 1: Event Bus - Emit with Dual Write
**What:** Every `emit()` call inserts to PostgreSQL (durability) and publishes to Redis pub/sub (real-time).
**When to use:** All domain events (workflow, document, lifecycle).
**Example:**
```python
# src/app/services/event_bus.py
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import DomainEvent

# Module-level Redis publish function (lazy-init)
_redis_client = None

async def _get_redis():
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        from app.core.config import settings
        _redis_client = aioredis.from_url(settings.redis_url)
    return _redis_client

async def emit(
    db: AsyncSession,
    event_type: str,
    entity_id: uuid.UUID,
    entity_type: str,
    actor_id: uuid.UUID | None = None,
    data: dict[str, Any] | None = None,
) -> DomainEvent:
    """Persist event to DB and publish to Redis pub/sub."""
    event = DomainEvent(
        event_type=event_type,
        entity_id=entity_id,
        entity_type=entity_type,
        actor_id=actor_id,
        data=data or {},
    )
    db.add(event)
    await db.flush()  # Get the ID assigned

    # Publish to Redis for real-time consumers (SSE)
    redis = await _get_redis()
    payload = json.dumps({
        "id": str(event.id),
        "event_type": event_type,
        "entity_id": str(entity_id),
        "entity_type": entity_type,
        "actor_id": str(actor_id) if actor_id else None,
        "data": data or {},
        "created_at": event.created_at.isoformat(),
    })
    await redis.publish("domain_events", payload)

    return event
```

### Pattern 2: Event Handler Registration (In-Process)
**What:** Notification creation triggered by event types, registered as simple async functions.
**When to use:** Decoupling business logic from notification creation.
**Example:**
```python
# In notification_service.py
from app.services import event_bus

async def handle_workitem_assigned(
    db: AsyncSession,
    event: DomainEvent,
) -> None:
    """Create notification when work item is assigned."""
    notification = Notification(
        user_id=event.data["performer_id"],
        type=NotificationType.TASK_ASSIGNED,
        title="New task assigned",
        message=f"You have been assigned to '{event.data.get('activity_name', 'a task')}'",
        entity_type="work_item",
        entity_id=event.entity_id,
    )
    db.add(notification)

    # Also dispatch email via Celery
    from app.tasks.notification import send_notification_email
    send_notification_email.delay(str(notification.id))
```

### Pattern 3: SSE Notification Stream (Follows Dashboard Pattern)
**What:** Per-user SSE stream that pushes new notifications via Redis pub/sub subscription.
**When to use:** Real-time notification badge updates.
**Example:**
```python
# In routers/notifications.py
async def _notification_sse_generator(user_id: uuid.UUID):
    """Subscribe to Redis pub/sub and yield notifications for this user."""
    redis = await _get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe("notifications")

    # Send initial unread count
    async with async_session_factory() as session:
        count = await notification_service.get_unread_count(session, user_id)
    yield f"event: unread_count\ndata: {json.dumps({'count': count})}\n\n"

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                if data.get("user_id") == str(user_id):
                    yield f"event: new_notification\ndata: {json.dumps(data)}\n\n"
    finally:
        await pubsub.unsubscribe("notifications")
        await pubsub.close()
```

### Pattern 4: Celery Email Task (Follows Existing async Pattern)
**What:** Celery task uses asyncio.run() wrapper to call fastapi-mail async send.
**When to use:** All notification emails.
**Example:**
```python
# src/app/tasks/notification.py
import asyncio
from app.celery_app import celery_app

@celery_app.task(name="app.tasks.notification.send_notification_email")
def send_notification_email(notification_id: str):
    """Send email for a notification. Uses asyncio.run() wrapper per project pattern."""
    asyncio.run(_send_email_async(notification_id))

async def _send_email_async(notification_id: str):
    from app.core.database import create_task_session_factory
    from app.models.notification import Notification
    from app.models.user import User
    # ... fetch notification, user email, render template, send via FastMail
```

### Anti-Patterns to Avoid
- **Emitting events directly in route handlers:** Always emit from service layer functions, never from routers. Routers call services; services call event_bus.emit().
- **Blocking email in request path:** Always dispatch email via Celery task. Never call FastMail.send_message() in an API handler.
- **Creating notifications without events:** All notifications must be created by event handlers, not scattered throughout business logic. This ensures the event bus is the single source of truth.
- **Using db.commit() inside emit():** Use db.flush() inside emit() to get the ID. Let the caller's transaction handle commit. This ensures event persistence is atomic with the business operation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Email sending | Raw smtplib with MIME | fastapi-mail (already installed) | Handles connection pooling, TLS, Jinja2 templates, async send |
| Notification popover UI | Custom dropdown with portal | shadcn/ui Popover (Radix) | Accessible, handles focus management, click-outside, positioning |
| SSE connection management | Custom EventSource wrapper | Follow existing useDashboardSSE pattern | Already battle-tested in the project, handles reconnection |
| Toast notifications | Custom toast system | Sonner (already installed) | Already configured globally, consistent with rest of app |
| Redis pub/sub | Custom message queue | redis.asyncio pubsub | Built-in, async iterator interface, handles reconnection |

**Key insight:** Every component of this phase has an existing pattern or installed library. The only new installation is the shadcn Popover component.

## Common Pitfalls

### Pitfall 1: SSE Authentication via Query Parameter
**What goes wrong:** EventSource API does not support custom headers. Cannot pass Bearer token.
**Why it happens:** Browser SSE API limitation.
**How to avoid:** Pass JWT token as query parameter (`?token=...`), exactly as the existing dashboard SSE endpoint does. Validate with `_validate_sse_token()` pattern from `dashboard.py`.
**Warning signs:** 401 errors on SSE connection.

### Pitfall 2: Redis Pub/Sub Message Loss on Disconnect
**What goes wrong:** If SSE client disconnects and reconnects, messages published during disconnection are lost (pub/sub is fire-and-forget).
**Why it happens:** Redis pub/sub has no message persistence or replay.
**How to avoid:** On SSE connect, send initial state (unread count) from database. Client can also poll GET /notifications on reconnect to catch up. The database is the source of truth; Redis pub/sub is just a real-time optimization.
**Warning signs:** Unread count not updating after network hiccup.

### Pitfall 3: Celery Task Session Factory
**What goes wrong:** Using the module-level `async_session_factory` in Celery tasks causes "Event loop is closed" errors.
**Why it happens:** Each `asyncio.run()` creates a new event loop; the module-level engine's connection pool is bound to the original loop.
**How to avoid:** Always use `create_task_session_factory()` inside Celery tasks, per established pattern in `auto_activity.py`.
**Warning signs:** `RuntimeError: Event loop is closed` in Celery worker logs.

### Pitfall 4: Transaction Atomicity with Event Emission
**What goes wrong:** Event is published to Redis but the DB transaction rolls back, creating phantom events.
**Why it happens:** Redis publish happens before transaction commit.
**How to avoid:** Use `db.flush()` (not commit) in `emit()`. The Redis publish is best-effort; if the transaction rolls back, the event won't be in the DB and consumers should treat DB as source of truth. For strict ordering, could defer Redis publish to after_commit hook, but this adds complexity that isn't needed here since the SSE consumer re-fetches from DB.
**Warning signs:** Notification appears momentarily then disappears.

### Pitfall 5: SSE Generator Cleanup on Client Disconnect
**What goes wrong:** Redis pubsub subscription leaks when client disconnects.
**Why it happens:** FastAPI SSE generator may not always get to the `finally` block on client disconnect.
**How to avoid:** Use try/finally in the generator. Add a heartbeat (`:heartbeat\n\n` comment every 15-30 seconds) to detect dead connections. Starlette's `StreamingResponse` will raise `asyncio.CancelledError` on disconnect, which triggers the finally block.
**Warning signs:** Growing number of Redis pubsub subscriptions over time.

### Pitfall 6: N+1 Queries in Notification List
**What goes wrong:** Loading notification list triggers separate query per notification for related data.
**Why it happens:** Lazy-loaded relationships.
**How to avoid:** Notification model is self-contained (no relationships to eagerly load). Keep title/message as denormalized strings, not references to other entities.
**Warning signs:** Slow notification list endpoint.

## Code Examples

### DomainEvent Model
```python
# src/app/models/event.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Uuid, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DomainEvent(Base):
    """Durable domain event store. Not using BaseModel (no soft delete needed)."""
    __tablename__ = "domain_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
```

### Notification Model
```python
# src/app/models/notification.py
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class NotificationType(str, enum.Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_DELEGATED = "task_delegated"
    DEADLINE_APPROACHING = "deadline_approaching"
    WORKFLOW_COMPLETED = "workflow_completed"
    DOCUMENT_UPLOADED = "document_uploaded"


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        String(50), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

### Notification SSE Hook (Frontend)
```typescript
// frontend/src/hooks/useNotificationSSE.ts
// Follows exact pattern of useDashboardSSE.ts
import { useState, useEffect, useRef, useCallback } from 'react';

export interface SSENotification {
  id: string;
  type: string;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: string | null;
  created_at: string;
}

type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

interface UseNotificationSSEResult {
  unreadCount: number;
  latestNotification: SSENotification | null;
  status: ConnectionStatus;
}

export function useNotificationSSE(): UseNotificationSSEResult {
  const [unreadCount, setUnreadCount] = useState(0);
  const [latestNotification, setLatestNotification] = useState<SSENotification | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const disconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearDisconnectTimer = useCallback(() => {
    if (disconnectTimerRef.current) {
      clearTimeout(disconnectTimerRef.current);
      disconnectTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setStatus('disconnected');
      return;
    }

    const url = `/api/v1/notifications/stream?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);

    es.onopen = () => {
      clearDisconnectTimer();
      setStatus('connected');
    };

    es.addEventListener('unread_count', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        setUnreadCount(data.count);
      } catch { /* ignore */ }
    });

    es.addEventListener('new_notification', (event: MessageEvent) => {
      try {
        const data: SSENotification = JSON.parse(event.data);
        setLatestNotification(data);
        setUnreadCount(prev => prev + 1);
      } catch { /* ignore */ }
    });

    es.onerror = () => {
      setStatus('reconnecting');
      clearDisconnectTimer();
      disconnectTimerRef.current = setTimeout(() => {
        setStatus('disconnected');
      }, 30_000);
    };

    return () => {
      es.close();
      clearDisconnectTimer();
    };
  }, [clearDisconnectTimer]);

  return { unreadCount, latestNotification, status };
}
```

### fastapi-mail Configuration
```python
# In notification.py Celery task
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

def _get_mail_config():
    from app.core.config import settings
    return ConnectionConfig(
        MAIL_USERNAME=settings.smtp_username,
        MAIL_PASSWORD=settings.smtp_password,
        MAIL_FROM=settings.smtp_from_email,
        MAIL_PORT=settings.smtp_port,
        MAIL_SERVER=settings.smtp_host,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=bool(settings.smtp_username),
        VALIDATE_CERTS=False,
        TEMPLATE_FOLDER="src/app/templates/email",
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| smtplib direct | fastapi-mail with aiosmtplib | Already migrated in deps | Use fastapi-mail for notification emails; keep existing smtplib auto_method for backward compat |
| Polling for notifications | SSE push + polling fallback | N/A (greenfield) | SSE for real-time, REST API for list/mark-read |
| Redis-only events | PostgreSQL + Redis dual write | N/A (greenfield) | Events survive restarts; Redis is real-time optimization only |

## Open Questions

1. **NOTIF-03 deadline check: where does due_date come from?**
   - What we know: WorkItem model does not currently have a `due_date` field. The CONTEXT.md mentions deadline notifications.
   - What's unclear: Phase 17 (Timer Activities) adds deadline configuration. NOTIF-03 may need a placeholder or the due_date field added in Phase 16.
   - Recommendation: Add a nullable `due_date` column to WorkItem in Phase 16's migration. The deadline check Celery Beat task can be a no-op until Phase 17 populates due dates. This avoids a migration dependency between phases.

2. **User email addresses**
   - What we know: The User model currently has `username` and `hashed_password` but no `email` field.
   - What's unclear: Email notifications need an email address to send to.
   - Recommendation: Add an optional `email` column to the User model in Phase 16's migration. If email is null, skip email notification for that user (dev mode graceful degradation).

3. **JSONB compatibility with SQLite tests**
   - What we know: Tests use SQLite in-memory. PostgreSQL JSONB type is not natively supported by SQLite.
   - What's unclear: Whether SQLAlchemy's JSONB type falls back gracefully in SQLite.
   - Recommendation: Use `from sqlalchemy import JSON` with a type decorator that uses JSONB on PostgreSQL and JSON on SQLite. Or simply use `JSON` type which works on both (SQLAlchemy handles this automatically -- `JSON` maps to `JSONB` on PostgreSQL when configured, but it is safer to use `JSON` in the model definition and let SQLAlchemy handle dialect differences).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pytest.ini (implicit, uses conftest.py) |
| Quick run command | `python -m pytest tests/test_notifications.py tests/test_events.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NOTIF-01 | Notification created on workitem.assigned event | unit | `python -m pytest tests/test_notifications.py::test_notification_on_assign -x` | Wave 0 |
| NOTIF-02 | Notification created on workitem.delegated event | unit | `python -m pytest tests/test_notifications.py::test_notification_on_delegate -x` | Wave 0 |
| NOTIF-03 | Notification created for approaching deadline | unit | `python -m pytest tests/test_notifications.py::test_deadline_notification -x` | Wave 0 |
| NOTIF-04 | Email task dispatched for assignment/deadline | unit | `python -m pytest tests/test_notifications.py::test_email_task_dispatched -x` | Wave 0 |
| NOTIF-05 | GET /notifications returns list with unread count | integration | `python -m pytest tests/test_notifications.py::test_list_notifications -x` | Wave 0 |
| NOTIF-06 | PATCH mark-read individual and bulk | integration | `python -m pytest tests/test_notifications.py::test_mark_read -x` | Wave 0 |
| EVENT-01 | Events emitted on document/lifecycle/workflow ops | integration | `python -m pytest tests/test_events.py::test_event_emission -x` | Wave 0 |
| EVENT-02 | Events persisted in domain_events table | unit | `python -m pytest tests/test_events.py::test_event_persistence -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_notifications.py tests/test_events.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_events.py` -- covers EVENT-01, EVENT-02
- [ ] `tests/test_notifications.py` -- covers NOTIF-01 through NOTIF-06

## Project Constraints (from CLAUDE.md)

- **Tech stack:** FastAPI backend, React 19 + TypeScript + Vite frontend
- **ORM:** SQLAlchemy 2.0 with async sessions (asyncpg for Postgres, aiosqlite for tests)
- **Task queue:** Celery with Redis broker
- **UI components:** shadcn/ui (Radix-based), Tailwind CSS 4.x
- **State management:** Zustand for UI state, TanStack Query for server state
- **Enum pattern:** `(str, enum.Enum)` stored as VARCHAR
- **Primary keys:** UUID with uuid4 default
- **Model base:** BaseModel with soft delete (is_deleted), audit columns (created_at, updated_at, created_by)
- **API pattern:** EnvelopeResponse wrapper for all responses
- **Migration naming:** `phase{N}_{seq}`
- **Celery task pattern:** asyncio.run() wrapper with create_task_session_factory()
- **SSE auth:** JWT token via query parameter
- **Router registration:** include_router() in main.py with api_v1_prefix

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/app/routers/dashboard.py` -- existing SSE pattern with _sse_generator and _validate_sse_token
- Codebase inspection: `src/app/tasks/auto_activity.py` -- Celery task pattern with asyncio.run() wrapper
- Codebase inspection: `src/app/core/config.py` -- SMTP settings already defined
- Codebase inspection: `src/app/models/base.py` -- BaseModel with soft delete pattern
- Codebase inspection: `src/app/celery_app.py` -- Beat schedule configuration pattern
- Codebase inspection: `frontend/src/hooks/useDashboardSSE.ts` -- SSE hook pattern with reconnection
- Codebase inspection: `frontend/src/components/layout/SidebarUserMenu.tsx` -- bell icon placement target

### Secondary (MEDIUM confidence)
- [fastapi-mail PyPI](https://pypi.org/project/fastapi-mail/) -- v1.6.2, ConnectionConfig + MessageSchema API
- [fastapi-mail examples](https://sabuhish.github.io/fastapi-mail/example/) -- Jinja2 template usage

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and verified in codebase
- Architecture: HIGH - follows established patterns from existing SSE, Celery, and model code
- Pitfalls: HIGH - documented from direct codebase analysis (session factory, SSE auth, pub/sub semantics)

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable domain, no rapidly changing dependencies)
