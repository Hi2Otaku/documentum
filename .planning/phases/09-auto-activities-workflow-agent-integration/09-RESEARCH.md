# Phase 9: Auto Activities, Workflow Agent & Integration - Research

**Researched:** 2026-04-04
**Domain:** Celery task queue, async-to-sync bridging, auto-method registry pattern, workflow automation
**Confidence:** HIGH

## Summary

Phase 9 introduces automated workflow activities that execute Python methods without human intervention, driven by a Celery-based Workflow Agent. The core technical challenge is bridging the project's async SQLAlchemy database layer with Celery's synchronous task execution model. All models, services, and enums needed for AUTO activities already exist in the codebase -- the `ActivityType.AUTO` enum, `ActivityTemplate.method_name` field, and the engine's advancement loop are all in place. The engine currently skips AUTO activities (treating them like START/END by not creating work items, but also not executing any method). The work is to: (1) build a decorator-based method registry, (2) create the `celery_app` module referenced by Docker Compose, (3) wire Celery beat to poll for AUTO activities, (4) execute registered methods with proper DB session management, and (5) add admin retry/skip endpoints.

INTG-02 and INTG-03 (external API start/complete/reject) are already implemented via existing endpoints (`POST /api/v1/workflows/` and `POST /inbox/{id}/complete`, `POST /inbox/{id}/reject`). INTG-01 is covered by the `call_external_api` built-in auto method. This reduces the integration scope to verifying existing endpoints work for external consumers (they already use JWT auth).

**Primary recommendation:** Use `asyncio.run()` or `asgiref.async_to_sync` inside each Celery task to bridge to the existing async service layer. Create a standalone `async_session_factory` call per task execution (not shared across tasks). The auto-method registry should be a simple module-level dict populated by decorators at import time.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Decorator-based registry -- methods decorated with `@auto_method('method_name')` are auto-discovered at startup. Method name stored in activity template's `method_name` field maps to the registered function.
- **D-02:** `ActivityContext` object passed to each method providing access to: process variables (read/write), attached documents, workflow instance, current activity, database session. Methods are async.
- **D-03:** Four built-in auto methods ship with v1: `send_email`, `change_lifecycle_state`, `modify_acl`, `call_external_api`
- **D-04:** Celery beat periodic task polling every 10 seconds. Scans for activity instances in RUNNING state with type=AUTO, dispatches each as an individual Celery task. Scales via worker count.
- **D-05:** Configurable timeout per method, default 60 seconds. Max 3 retries with exponential backoff (10s, 30s, 90s). After max retries, mark activity as FAILED and log error. Workflow halts at the failed activity.
- **D-06:** Create `celery_app` module (referenced in Docker Compose but not yet implemented). Configure Celery with Redis broker (already in Docker Compose).
- **D-07:** API endpoints only (no UI): `POST /api/v1/workflows/{id}/activities/{id}/retry` and `POST /api/v1/workflows/{id}/activities/{id}/skip`
- **D-08:** Error details (exception message, traceback, attempt count, timestamps) stored in activity instance or a new execution log table.
- **D-09:** INTG-02 and INTG-03 already implemented. No new REST endpoints needed for external workflow start/complete/reject.
- **D-10:** INTG-01 covered by `call_external_api` built-in auto method.
- **D-11:** No new authentication mechanism -- external systems use existing JWT auth.

### Claude's Discretion
- Celery task configuration details (queues, prefetch, acks_late)
- ActivityContext implementation details
- Email configuration approach (SMTP settings, dev mode logging)
- Execution log table schema vs storing in existing audit trail
- Auto method module organization (single file vs directory)
- How to prevent duplicate execution (idempotency/locking on poll)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTO-01 | Auto activities execute Python methods without human intervention | Decorator-based registry + engine integration to dispatch AUTO activities to Celery |
| AUTO-02 | Workflow Agent continuously scans for auto activities to execute | Celery beat periodic task every 10s polling ACTIVE AUTO activity instances |
| AUTO-03 | Auto activities can: send emails, change lifecycle state, modify ACLs, call external APIs | Four built-in auto methods reusing lifecycle_service and acl_service |
| AUTO-04 | Workflow Agent logs execution results and handles errors (retry, fail) | Execution log table + Celery retry with exponential backoff |
| AUTO-05 | Failed auto activities can be retried or skipped by administrator | Two new API endpoints: retry and skip |
| INTG-01 | Auto activities can call external REST APIs (webhook-based) | `call_external_api` built-in method using httpx |
| INTG-02 | External systems can trigger workflow start via REST API | Already implemented: `POST /api/v1/workflows/` |
| INTG-03 | External systems can complete/reject work items via REST API | Already implemented: `POST /inbox/{id}/complete`, `POST /inbox/{id}/reject` |

</phase_requirements>

## Standard Stack

### Core (already in pyproject.toml)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Celery | 5.6.3 (installed) | Task queue / worker / beat scheduler | Already a project dependency; Docker Compose already defines celery-worker and celery-beat services |
| Redis | 6.4.0 (installed, redis-py) | Celery broker + result backend | Already running in Docker Compose, already a project dependency |
| httpx | 0.28.x (installed as dev dep) | HTTP client for `call_external_api` method | Already used in tests; async-native, production-grade HTTP client |

### Supporting (may need adding)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28.x | Production HTTP calls from auto methods | Move from dev-only to main dependency if `call_external_api` needs it at runtime |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.run() in tasks | asgiref.async_to_sync | asgiref adds a dependency; asyncio.run() is stdlib and sufficient for one-shot async calls in sync Celery tasks |
| Execution log table | Storing in audit_log | Dedicated table allows structured queries (attempt count, error trace, timestamps) while audit trail stays append-only narrative; recommend dedicated table |

## Architecture Patterns

### Recommended Project Structure
```
src/app/
  celery_app.py          # Celery app instance + beat_schedule config
  auto_methods/
    __init__.py           # Registry dict + @auto_method decorator
    context.py            # ActivityContext dataclass
    builtin.py            # send_email, change_lifecycle_state, modify_acl, call_external_api
  tasks/
    __init__.py
    auto_activity.py      # poll_auto_activities (beat) + execute_auto_activity (task)
  models/
    execution_log.py      # AutoActivityLog model (new)
  routers/
    activities.py         # retry/skip endpoints (new, or add to workflows.py)
```

### Pattern 1: Decorator-Based Method Registry
**What:** A module-level dictionary maps method names to async callables. A `@auto_method('name')` decorator registers functions at import time.
**When to use:** Any system that needs a pluggable set of named handlers discoverable at startup.
**Example:**
```python
# src/app/auto_methods/__init__.py
from typing import Callable, Awaitable
from app.auto_methods.context import ActivityContext

_registry: dict[str, Callable[[ActivityContext], Awaitable[dict | None]]] = {}

def auto_method(name: str):
    """Decorator to register an auto activity method."""
    def decorator(func: Callable[[ActivityContext], Awaitable[dict | None]]):
        _registry[name] = func
        return func
    return decorator

def get_auto_method(name: str) -> Callable[[ActivityContext], Awaitable[dict | None]] | None:
    return _registry.get(name)

def list_auto_methods() -> list[str]:
    return list(_registry.keys())

# Import builtins to trigger registration
import app.auto_methods.builtin  # noqa: F401, E402
```

### Pattern 2: Async-to-Sync Bridge in Celery Tasks
**What:** Celery tasks are synchronous. The project's services are async. Bridge with `asyncio.run()`.
**When to use:** Every Celery task that needs database access or calls async auto methods.
**Example:**
```python
# src/app/tasks/auto_activity.py
import asyncio
from celery import shared_task
from app.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3)
def execute_auto_activity(self, activity_instance_id: str, workflow_instance_id: str):
    """Execute a single auto activity method."""
    asyncio.run(_execute_async(activity_instance_id, workflow_instance_id, self))

async def _execute_async(activity_instance_id: str, workflow_instance_id: str, task):
    from app.core.database import async_session_factory
    async with async_session_factory() as session:
        try:
            # ... load activity, resolve method, build context, execute, advance
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Pattern 3: Database Session per Task (Not Shared)
**What:** Each Celery task creates its own async session via `async_session_factory()`. No session sharing between tasks.
**When to use:** Always. Celery tasks run in separate processes/threads.
**Critical detail:** The `async_session_factory` from `app.core.database` creates sessions from the shared engine. However, in Celery workers, the engine is created at module import time when the worker starts. This is fine because SQLAlchemy's `create_async_engine` uses connection pooling per-process, and Celery workers are separate processes.

### Pattern 4: Idempotent Polling with SELECT FOR UPDATE SKIP LOCKED
**What:** The beat task polls for AUTO activities to execute. To prevent duplicate dispatch when multiple beat instances or overlapping poll cycles occur, use database-level locking.
**When to use:** The periodic poll task.
**Example:**
```python
# In the poll task:
async def _poll_auto_activities():
    from app.core.database import async_session_factory
    async with async_session_factory() as session:
        result = await session.execute(
            select(ActivityInstance)
            .join(ActivityTemplate)
            .where(
                ActivityInstance.state == ActivityState.ACTIVE,
                ActivityTemplate.activity_type == ActivityType.AUTO,
            )
            .with_for_update(skip_locked=True)
        )
        activities = result.scalars().all()
        for ai in activities:
            # Mark as "queued" or dispatch Celery task
            execute_auto_activity.delay(str(ai.id), str(ai.workflow_instance_id))
        await session.commit()
```
**Note:** SQLite (used in tests) does not support `SKIP LOCKED`. Test code must handle this gracefully or skip the locking in test mode.

### Pattern 5: ActivityContext as Async Helper
**What:** A dataclass wrapping DB session, workflow instance, activity instance, process variables, and document references. Provides convenience methods for reading/writing variables.
**When to use:** Passed to every auto method.
**Example:**
```python
@dataclass
class ActivityContext:
    db: AsyncSession
    workflow_instance: WorkflowInstance
    activity_instance: ActivityInstance
    activity_template: ActivityTemplate
    variables: dict[str, Any]  # name -> value
    document_ids: list[uuid.UUID]
    user_id: str  # "system" for auto activities

    async def get_variable(self, name: str) -> Any:
        return self.variables.get(name)

    async def set_variable(self, name: str, value: Any) -> None:
        # Update in-memory and DB
        ...
```

### Anti-Patterns to Avoid
- **Sharing DB sessions across Celery tasks:** Each task must create its own session. Sessions are not thread-safe or process-safe.
- **Using `asyncio.get_event_loop()` in Celery tasks:** There is no running loop in a Celery worker. Use `asyncio.run()` which creates a new loop.
- **Polling with `SELECT ... WHERE state='ACTIVE'` without locking:** Risk of duplicate execution if poll interval overlaps with execution time.
- **Storing Celery task results in Redis for workflow state:** Use the database as source of truth. Redis result backend is optional and only for debugging.
- **Running Celery beat with multiple instances:** Beat should be a singleton. Multiple beat processes will fire duplicate periodic tasks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Periodic task scheduling | Custom cron/timer threads | Celery Beat `beat_schedule` | Handles timezone, missed runs, persistence |
| Task retry with backoff | Manual retry loops | Celery `autoretry_for` + `retry_backoff` | Built-in exponential backoff, max retries, dead letter |
| HTTP client for webhooks | `urllib` / raw `requests` | `httpx.AsyncClient` | Already in project, async-native, timeout support, connection pooling |
| Task result tracking | Custom status table | Celery's task state + dedicated execution log | Celery tracks PENDING/STARTED/SUCCESS/FAILURE natively |

**Key insight:** Celery provides all the retry, scheduling, and task lifecycle primitives needed. The custom code should focus on the domain-specific parts: method registry, ActivityContext, engine integration.

## Common Pitfalls

### Pitfall 1: Celery Task Can't See Async Models
**What goes wrong:** Celery tasks import SQLAlchemy models, but the async engine isn't initialized in the worker process.
**Why it happens:** The Celery worker imports the app module but doesn't run FastAPI's lifespan. The engine from `app.core.database` is created at import time from settings, so it works -- but the `seed_admin` and MinIO startup won't run.
**How to avoid:** The `celery_app.py` module should import `app.core.database` to ensure the engine is created. No lifespan hooks are needed because Celery workers don't serve HTTP.
**Warning signs:** `OperationalError: no such engine` or connection refused errors in worker logs.

### Pitfall 2: SQLite SKIP LOCKED Not Supported in Tests
**What goes wrong:** Tests use SQLite (aiosqlite) which doesn't support `FOR UPDATE SKIP LOCKED`.
**Why it happens:** The project's test infra uses in-memory SQLite for speed.
**How to avoid:** Make the locking conditional: `if dialect != 'sqlite'` or catch `OperationalError` and fall back to non-locked query. Or simply skip locking in the poll task when in test mode, since tests don't have concurrent workers.
**Warning signs:** `sqlite3.OperationalError: near "FOR": syntax error`

### Pitfall 3: Engine Advancement After Auto Activity Completion
**What goes wrong:** After an auto method executes successfully, the workflow doesn't advance to the next activity.
**Why it happens:** The current engine's `_advance_from_activity` handles START/END auto-completion, but there's no code path for AUTO activities. The task must explicitly call the advancement logic after the method completes.
**How to avoid:** After a successful auto method execution, call `_advance_from_activity` (or a public wrapper) with the completed activity instance. This is the same pattern used by `complete_work_item` but without a work item.
**Warning signs:** Workflow stuck at a completed AUTO activity with no next activity activated.

### Pitfall 4: Circular Import with Engine Service
**What goes wrong:** `auto_methods/builtin.py` imports `lifecycle_service` and `acl_service`, while `engine_service` may need to import auto method utilities.
**Why it happens:** The engine needs to know about auto methods for dispatching, and auto methods need services.
**How to avoid:** Use lazy imports (already the project pattern -- see `engine_service.py` line 236, 376). The auto method registry is independent of the engine. The engine integration point is in the Celery task, not in `engine_service.py` directly.
**Warning signs:** `ImportError: cannot import name '...' (most likely due to a circular import)`

### Pitfall 5: Celery Worker Using Wrong Database URL
**What goes wrong:** Celery worker connects to a different database or fails to connect.
**Why it happens:** Docker Compose environment variables are set for the celery-worker service, but local development might not have them.
**How to avoid:** The `celery_app.py` should import `app.core.config.settings` which reads from env vars. Docker Compose already defines DATABASE_URL for celery-worker. For local dev, use a `.env` file.
**Warning signs:** Worker starts but tasks fail with connection errors.

### Pitfall 6: asyncio.run() Fails If Loop Already Running
**What goes wrong:** `asyncio.run()` raises `RuntimeError: This event loop is already running` in some test scenarios.
**Why it happens:** Some test frameworks or Celery test utilities run their own event loop.
**How to avoid:** For production, `asyncio.run()` is fine since Celery workers don't have an event loop. For tests, mock the Celery task and test the async function directly (don't test through the sync wrapper).
**Warning signs:** `RuntimeError` in test output when testing Celery tasks.

## Code Examples

### Celery App Configuration
```python
# src/app/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "documentum",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.auto_activity"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,          # Re-deliver task if worker crashes mid-execution
    worker_prefetch_multiplier=1, # Don't prefetch; auto activities may be long-running
    beat_schedule={
        "poll-auto-activities": {
            "task": "app.tasks.auto_activity.poll_auto_activities",
            "schedule": 10.0,  # Every 10 seconds (D-04)
        },
    },
)
```

### Execution Log Model
```python
# src/app/models/execution_log.py
import uuid
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel

class AutoActivityLog(BaseModel):
    __tablename__ = "auto_activity_logs"

    activity_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("activity_instances.id"), nullable=False, index=True
    )
    method_name: Mapped[str] = mapped_column(String(255), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "success", "error", "timeout"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

### Built-in Auto Method: change_lifecycle_state
```python
# src/app/auto_methods/builtin.py
from app.auto_methods import auto_method
from app.auto_methods.context import ActivityContext

@auto_method("change_lifecycle_state")
async def change_lifecycle_state(ctx: ActivityContext) -> dict | None:
    """Transition attached documents to a new lifecycle state.
    
    Reads target_state from process variables or activity template's method config.
    Reuses existing lifecycle_service.transition_lifecycle_state.
    """
    from app.models.enums import LifecycleState
    from app.services.lifecycle_service import transition_lifecycle_state
    
    target_state_str = await ctx.get_variable("target_lifecycle_state")
    if not target_state_str:
        raise ValueError("Process variable 'target_lifecycle_state' not set")
    
    target_state = LifecycleState(target_state_str)
    results = []
    for doc_id in ctx.document_ids:
        await transition_lifecycle_state(ctx.db, doc_id, target_state, ctx.user_id)
        results.append({"document_id": str(doc_id), "new_state": target_state_str})
    
    return {"transitions": results}
```

### Engine Integration Point
```python
# In engine_service.py _advance_from_activity, the AUTO handling block:
# Currently the code only handles START/END and MANUAL.
# Need to add after line ~507:

elif target_at.activity_type == ActivityType.AUTO:
    # Don't auto-complete; leave as ACTIVE for Celery to pick up
    # The poll task will find this and dispatch execution
    pass
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Celery 4.x with AMQP (RabbitMQ) | Celery 5.x with Redis broker | Celery 5.0 (2020) | Redis is simpler to deploy; project already uses Redis |
| Sync SQLAlchemy in tasks | asyncio.run() + async SQLAlchemy | SQLAlchemy 2.0 (2023) | Allows reusing async services without rewriting them sync |
| task.retry() manual calls | autoretry_for + retry_backoff | Celery 4.2+ | Declarative retry config, less boilerplate |

## Open Questions

1. **ActivityInstance state for "queued but not yet executed"**
   - What we know: Currently ActivityState has DORMANT, ACTIVE, PAUSED, COMPLETE, ERROR. When the engine activates an AUTO activity, it becomes ACTIVE. The poll task picks it up and dispatches a Celery task.
   - What's unclear: Should there be a distinction between "ACTIVE and awaiting poll" vs "ACTIVE and currently executing"? Adding a new state (e.g., RUNNING) would require a migration and state transition updates.
   - Recommendation: Keep ACTIVE for both states. Use the execution log table to track whether execution is in progress. The `SKIP LOCKED` pattern prevents double-dispatch. Simpler than adding a new enum value.

2. **Timeout enforcement mechanism**
   - What we know: D-05 specifies configurable timeout per method, default 60 seconds.
   - What's unclear: Celery's `task_time_limit` kills the worker process (hard timeout). `task_soft_time_limit` raises `SoftTimeLimitExceeded` which can be caught.
   - Recommendation: Use `soft_time_limit` per task invocation via `execute_auto_activity.apply_async(soft_time_limit=timeout)`. Catch `SoftTimeLimitExceeded` in the task, log timeout, and retry or fail.

3. **SMTP configuration for send_email**
   - What we know: D-03 says "SMTP or log in dev mode".
   - Recommendation: Add SMTP settings to `Settings` class with defaults that enable dev-mode logging (e.g., `smtp_host: str = ""`, when empty, log email instead of sending). Use Python's `smtplib`/`aiosmtplib` for actual sending. Keep it simple -- no email template engine.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Celery | Task queue (AUTO-01, AUTO-02) | Yes | 5.6.3 | -- |
| Redis (redis-py) | Celery broker | Yes | 6.4.0 | -- |
| Redis server | Celery broker runtime | Via Docker only | 7.x | Must run Docker Compose |
| httpx | call_external_api method | Yes (dev dep) | 0.28.x | Move to main deps |
| PostgreSQL | Production DB + SKIP LOCKED | Via Docker only | 16+ | SQLite for tests (no SKIP LOCKED) |

**Missing dependencies with no fallback:**
- None -- all core dependencies are installed.

**Missing dependencies with fallback:**
- httpx is currently dev-only; needs to be moved to main dependencies for `call_external_api` runtime use.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_auto_activities.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTO-01 | Auto method registry discovers decorated methods; engine dispatches AUTO activity | unit + integration | `pytest tests/test_auto_activities.py::test_auto_method_registry -x` | No -- Wave 0 |
| AUTO-02 | Poll task finds ACTIVE AUTO activities and dispatches Celery tasks | unit | `pytest tests/test_auto_activities.py::test_poll_dispatches_auto -x` | No -- Wave 0 |
| AUTO-03 | Built-in methods (lifecycle, ACL, email, external API) execute correctly | unit | `pytest tests/test_auto_activities.py::test_builtin_methods -x` | No -- Wave 0 |
| AUTO-04 | Execution log records success/failure; retry with backoff on error | unit | `pytest tests/test_auto_activities.py::test_execution_logging -x` | No -- Wave 0 |
| AUTO-05 | Admin can retry failed activity (resets state) and skip (marks complete, advances) | integration | `pytest tests/test_auto_activities.py::test_retry_skip_endpoints -x` | No -- Wave 0 |
| INTG-01 | call_external_api method sends HTTP POST with workflow context | unit | `pytest tests/test_auto_activities.py::test_call_external_api -x` | No -- Wave 0 |
| INTG-02 | External systems start workflows via REST API | integration | `pytest tests/test_workflows.py::test_start_workflow -x` | Yes -- existing |
| INTG-03 | External systems complete/reject via REST API | integration | `pytest tests/test_inbox.py -x` | Yes -- existing |

### Sampling Rate
- **Per task commit:** `pytest tests/test_auto_activities.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_auto_activities.py` -- covers AUTO-01 through AUTO-05, INTG-01
- [ ] `src/app/models/execution_log.py` -- new model needs to be importable in tests
- [ ] Alembic migration for `auto_activity_logs` table (manual, as per Phase 3 pattern)

## Sources

### Primary (HIGH confidence)
- Project codebase analysis: `engine_service.py`, `lifecycle_service.py`, `acl_service.py`, `celery_app` references in `docker-compose.yml`
- Celery 5.6 official docs: [Periodic Tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html) -- beat_schedule configuration
- Celery 5.6 official docs: [Task retry](https://docs.celeryq.dev/en/stable/userguide/tasks.html) -- autoretry_for, retry_backoff

### Secondary (MEDIUM confidence)
- [Celery Tasks: SQLAlchemy Session Handling](https://celery.school/sqlalchemy-session-celery-tasks) -- session-per-task pattern
- [Using Async SQLAlchemy Inside Sync Celery Tasks](https://dev.to/kevinnadar22/using-async-sqlalchemy-inside-sync-celery-tasks-3eg4) -- asyncio.run() bridge pattern

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and configured in Docker Compose
- Architecture: HIGH -- patterns are well-established (decorator registry, Celery beat, async bridge) and codebase patterns are clear
- Pitfalls: HIGH -- identified from direct codebase analysis (SQLite test limitation, engine integration gap, circular imports)

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable domain, no fast-moving dependencies)
