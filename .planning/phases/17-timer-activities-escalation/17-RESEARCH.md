# Phase 17: Timer Activities & Escalation - Research

**Researched:** 2026-04-06
**Domain:** Workflow timer/deadline enforcement, Celery Beat periodic tasks, escalation logic
**Confidence:** HIGH

## Summary

Phase 17 adds deadline enforcement to the workflow engine. Activity templates gain a `deadline_duration_hours` field (already partially modeled as `expected_duration_hours` on `ActivityTemplate`). When a workflow creates a work item for a timed activity, the engine calculates `due_date = now + duration`. A Celery Beat task (placeholder already exists at `check_approaching_deadlines`) periodically queries for overdue work items and triggers escalation actions: priority bump, reassignment, or notification.

The codebase is well-prepared for this phase. `WorkItem.due_date` already exists as a nullable DateTime column. `ActivityTemplate.expected_duration_hours` already exists as a nullable Float column. The notification infrastructure (event bus, `create_notification()`, SSE pub/sub, email templates including `deadline_approaching.html`) is fully operational from Phase 16. The Celery Beat schedule already has the `check-approaching-deadlines` entry running every 300 seconds. The frontend inbox already displays `due_date` in `InboxDetailPanel`. The primary work is: (1) adding escalation configuration to activity templates, (2) computing `due_date` at work-item creation time, (3) implementing the deadline checker logic, (4) adding escalation actions, and (5) adding deadline fields to the designer UI.

**Primary recommendation:** Extend the existing `ActivityTemplate` model with escalation config columns (`escalation_action`, `warning_threshold_hours`), wire `due_date` computation into all `WorkItem()` constructor sites in `engine_service.py`, and implement `_check_deadlines_async()` to query overdue items and dispatch escalation actions.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None -- discuss phase was skipped per autonomous YOLO mode. All decisions at Claude's discretion.

### Claude's Discretion
All implementation choices are at Claude's discretion. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
None -- discuss phase skipped.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NOTIF-03 | User receives in-app notification when a work item deadline is approaching | Notification service + email template already exist; deadline checker task needs real implementation |
| TIMER-01 | Admin can configure deadline duration on activity templates in workflow designer | `expected_duration_hours` exists on model; designer PropertiesPanel needs deadline + escalation fields |
| TIMER-02 | Work items automatically receive due dates based on activity template deadline configuration | 7 `WorkItem()` constructor sites in engine_service.py need `due_date` calculation |
| TIMER-03 | Celery Beat periodically checks for overdue work items and triggers escalation | Beat schedule entry exists (300s); placeholder `_check_deadlines_async()` needs real query logic |
| TIMER-04 | Overdue work items are automatically escalated (priority bump, reassignment, or notification) | Escalation actions need new config on ActivityTemplate + action dispatcher in task |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech stack:** FastAPI + SQLAlchemy 2.0 async + Celery 5.6.x + Redis + PostgreSQL
- **Database-backed Beat polling for all timers -- never use Celery ETA tasks** (locked decision from STATE.md)
- **Frontend:** React 19 + TypeScript + Vite + shadcn/ui + React Flow designer
- **Testing:** pytest + pytest-asyncio + httpx AsyncClient, SQLite in-memory for tests
- **Linting:** Ruff
- **GSD workflow enforcement:** All changes through GSD commands

## Standard Stack

No new libraries needed. This phase uses exclusively existing stack components:

### Core (already installed)
| Library | Version | Purpose | Role in Phase 17 |
|---------|---------|---------|-------------------|
| Celery | 5.6.x | Beat scheduler | Runs `check_approaching_deadlines` every 300s |
| SQLAlchemy | 2.0.48 | ORM | Activity template + work item model changes |
| Alembic | 1.18.x | Migrations | New columns on `activity_templates` |
| FastAPI | 0.135.x | API | Template CRUD endpoints already handle activity updates |
| Pydantic | 2.12.x | Schemas | Extend activity template schemas with escalation config |

### No New Dependencies
This phase requires zero new Python or npm packages. All functionality builds on existing infrastructure.

## Architecture Patterns

### Existing Infrastructure to Leverage

```
src/app/
  models/workflow.py          # ActivityTemplate.expected_duration_hours (exists)
                              # WorkItem.due_date (exists, nullable DateTime)
  services/engine_service.py  # 7 WorkItem() constructor sites (lines ~596-1104)
  services/notification_service.py  # create_notification() with Redis pub/sub
  services/event_handlers.py  # Event-driven notification pattern
  tasks/notification.py       # check_approaching_deadlines (placeholder)
                              # send_notification_email (working)
  celery_app.py               # Beat schedule (300s for deadline check)
  templates/email/deadline_approaching.html  # Email template (exists)
  schemas/template.py         # ActivityTemplateCreate/Update/Response
frontend/src/
  components/designer/PropertiesPanel.tsx  # Node properties editor
  types/designer.ts           # ActivityNodeData interface
  hooks/useSaveTemplate.ts    # Save hook (sends activity data to API)
  api/templates.ts            # addActivity/updateActivity API calls
```

### Pattern 1: Due Date Calculation at Work Item Creation

**What:** When `engine_service.py` creates a `WorkItem`, check whether the activity template has `expected_duration_hours` set. If so, compute `due_date = utcnow() + timedelta(hours=expected_duration_hours)`.

**When to use:** Every `WorkItem()` constructor call in `engine_service.py`.

**Approach:** Create a helper function that all 7 WorkItem constructor sites call:

```python
from datetime import datetime, timedelta, timezone

def _compute_due_date(activity_template: ActivityTemplate) -> datetime | None:
    """Calculate work item due date from activity template deadline config."""
    if activity_template.expected_duration_hours is not None:
        return datetime.now(timezone.utc) + timedelta(
            hours=activity_template.expected_duration_hours
        )
    return None
```

The 7 WorkItem creation sites are at approximately these locations in engine_service.py:
1. Line ~596: Queue performer work item
2. Line ~617: Sequential performer work items
3. Line ~630: Runtime selection work items
4. Line ~651: Standard performer work items
5. Line ~863: Sequential next-performer work item
6. Line ~1034: Reject flow previous-performer work item
7. Line ~1098: Reject re-routing work items

### Pattern 2: Escalation Configuration on Activity Template

**What:** Add `escalation_action` (enum: `priority_bump`, `reassign`, `notify`, or `null`) and optionally a `warning_threshold_hours` (float, nullable) to `ActivityTemplate`. The warning threshold determines when "approaching deadline" notifications fire (e.g., 2 hours before due_date).

**Model changes (activity_templates table):**
```python
# New columns on ActivityTemplate
escalation_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
warning_threshold_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
```

**Why not a separate table:** The escalation config is 1:1 with activity templates and only 2 columns. A separate table adds join complexity for no benefit. If multi-level escalation chains are needed later (TIMER-07, deferred), that can be a separate `escalation_rules` table.

### Pattern 3: Deadline Checker Celery Task

**What:** Replace the placeholder `_check_deadlines_async()` with real logic.

**Algorithm:**
1. Query active work items (state IN `available`, `acquired`, `delegated`) where `due_date IS NOT NULL`
2. Split into two groups:
   - **Approaching:** `due_date - warning_threshold <= now < due_date` AND not already notified
   - **Overdue:** `due_date <= now` AND not already escalated
3. For approaching items: create `deadline_approaching` notification (NOTIF-03)
4. For overdue items: execute escalation action from the activity template config

**Deduplication:** Add `is_escalated` boolean column on `WorkItem` (default false) to prevent repeated escalation. For warning notifications, track via a `deadline_warning_sent` boolean.

```python
# New columns on WorkItem
is_escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
deadline_warning_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

### Pattern 4: Escalation Actions

Three escalation action types, matching the requirements:

```python
async def _escalate_work_item(
    db: AsyncSession, work_item: WorkItem, activity_template: ActivityTemplate
) -> None:
    action = activity_template.escalation_action
    if action == "priority_bump":
        work_item.priority = max(1, work_item.priority - 2)  # Lower number = higher priority
    elif action == "reassign":
        # Reassign to supervisor of the workflow instance
        workflow = work_item.activity_instance.workflow_instance
        if workflow.supervisor_id:
            work_item.performer_id = workflow.supervisor_id
    elif action == "notify":
        # Just send notification (no state change)
        pass
    
    work_item.is_escalated = True
    
    # Always create notification for escalation
    await create_notification(
        db,
        user_id=work_item.performer_id,
        title="Work item overdue - escalated",
        message=f"...",
        notification_type="deadline_escalated",
        entity_type="work_item",
        entity_id=work_item.id,
    )
```

### Pattern 5: Designer UI Extension

**What:** Add deadline and escalation fields to the PropertiesPanel for manual and auto activity nodes.

**Fields to add:**
- "Deadline Duration (hours)" -- numeric input, maps to `expected_duration_hours`
- "Escalation Action" -- dropdown: None / Priority Bump / Reassign / Notify
- "Warning Before Deadline (hours)" -- numeric input, maps to `warning_threshold_hours`

**Data flow:**
1. `ActivityNodeData` interface gets `expectedDurationHours`, `escalationAction`, `warningThresholdHours`
2. `PropertiesPanel` renders inputs for these fields
3. `useSaveTemplate.ts` save hook already sends all node data fields to `addActivity`/`updateActivity`
4. `templates.ts` API functions need the new fields in their request types
5. Backend `ActivityTemplateCreate`/`Update`/`Response` schemas need the new fields

### Anti-Patterns to Avoid
- **Celery ETA tasks for deadlines:** STATE.md explicitly says "Database-backed Beat polling for all timers -- never use Celery ETA tasks." The polling approach is already in place.
- **Separate timer table:** Overengineering for v1.2 scope. The `expected_duration_hours` + escalation columns on `ActivityTemplate` is sufficient.
- **Stateless deadline checker:** Without `is_escalated` / `deadline_warning_sent` flags, the checker would repeatedly escalate/notify every 5 minutes. Always track escalation state.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deadline notification delivery | Custom pub/sub | Existing `create_notification()` + Redis pub/sub | Already handles SSE delivery, email dispatch, and persistence |
| Periodic deadline scanning | Custom scheduler/cron | Existing Celery Beat entry (300s) | Already configured and running |
| Email for deadline alerts | Custom SMTP | Existing `send_notification_email` task + `deadline_approaching.html` template | Template already exists from Phase 16 |
| Due date display in inbox | New UI component | Existing `InboxDetailPanel` already shows `due_date` | Already renders date when non-null |

## Common Pitfalls

### Pitfall 1: Missing WorkItem Constructor Sites
**What goes wrong:** Due date not set on some work items because not all 7 constructor sites in `engine_service.py` are updated.
**Why it happens:** Work items are created in multiple code paths (queue, sequential, runtime_selection, standard, sequential-next, reject-previous, reject-reroute).
**How to avoid:** Use a helper function `_compute_due_date(activity_template)` and grep for `WorkItem(` to ensure every site passes `due_date=_compute_due_date(target_at)`.
**Warning signs:** Some work items have `due_date=None` even when the activity template has `expected_duration_hours` set.

### Pitfall 2: Repeated Escalation on Every Poll Cycle
**What goes wrong:** The 5-minute checker bumps priority or sends notifications repeatedly for the same overdue item.
**Why it happens:** No state tracking on whether escalation already occurred.
**How to avoid:** Add `is_escalated` and `deadline_warning_sent` boolean columns. Filter them in the query: `WHERE is_escalated = FALSE`.
**Warning signs:** Users receive dozens of duplicate "overdue" notifications.

### Pitfall 3: Timezone Handling
**What goes wrong:** Due dates computed in local time vs UTC, causing premature or late escalation.
**Why it happens:** `datetime.now()` without timezone vs `datetime.now(timezone.utc)`.
**How to avoid:** All datetime calculations use `datetime.now(timezone.utc)`. The database column is already `DateTime(timezone=True)`. Celery app is configured with `timezone="UTC"`.
**Warning signs:** Deadlines fire at unexpected times.

### Pitfall 4: Schema/API Mismatch
**What goes wrong:** Frontend sends new fields but backend ignores them (or vice versa).
**Why it happens:** Must update: Pydantic schemas (Create/Update/Response), API function types in `templates.ts`, `ActivityNodeData` interface, `useSaveTemplate` hook.
**How to avoid:** Trace the full data flow: Designer UI -> Zustand store -> save hook -> API client -> FastAPI endpoint -> Pydantic schema -> SQLAlchemy model -> Alembic migration.
**Warning signs:** Deadline fields not persisting across template save/reload.

### Pitfall 5: Celery Task Session Management
**What goes wrong:** Database errors in the deadline checker task.
**Why it happens:** Celery tasks run in a separate process. Must use `create_task_session_factory()` pattern (not the FastAPI request session).
**How to avoid:** Follow the established pattern from `_send_email_async` and `_aggregate_async`: `session_factory = create_task_session_factory()`, then `async with session_factory() as session:`.
**Warning signs:** `RuntimeError: no running event loop` or `pool is being used by another event loop`.

## Code Examples

### Due Date Computation Helper
```python
# Source: Codebase pattern from engine_service.py
from datetime import datetime, timedelta, timezone

def _compute_due_date(activity_template: ActivityTemplate) -> datetime | None:
    if activity_template.expected_duration_hours is not None:
        return datetime.now(timezone.utc) + timedelta(
            hours=activity_template.expected_duration_hours
        )
    return None
```

### Updated WorkItem Constructor Pattern
```python
# Every WorkItem() call site needs due_date:
work_item = WorkItem(
    activity_instance_id=target_ai.id,
    performer_id=perf_id,
    state=WorkItemState.AVAILABLE,
    due_date=_compute_due_date(target_at),  # NEW
    created_by=user_id,
)
```

### Deadline Checker Query Pattern
```python
# Source: Follows existing task patterns in tasks/notification.py
from sqlalchemy import select, and_
from datetime import datetime, timezone

now = datetime.now(timezone.utc)

# Overdue, not yet escalated
overdue_stmt = (
    select(WorkItem)
    .join(ActivityInstance, WorkItem.activity_instance_id == ActivityInstance.id)
    .join(ActivityTemplate, ActivityInstance.activity_template_id == ActivityTemplate.id)
    .where(
        WorkItem.due_date <= now,
        WorkItem.is_escalated == False,
        WorkItem.state.in_([WorkItemState.AVAILABLE, WorkItemState.ACQUIRED, WorkItemState.DELEGATED]),
        WorkItem.is_deleted == False,
    )
)
```

### Designer UI Deadline Field
```tsx
{/* Deadline Duration (hours) - for manual and auto nodes */}
{(data.activityType === 'manual' || data.activityType === 'auto') && (
  <div className="space-y-3">
    <h4 className="text-sm font-semibold text-muted-foreground">Timer & Escalation</h4>
    <div>
      <label className="text-sm font-medium" htmlFor="deadline-hours">
        Deadline Duration (hours)
      </label>
      <input
        id="deadline-hours"
        type="number"
        min="0"
        step="0.5"
        className="mt-1 w-full rounded border px-3 py-2 text-sm"
        value={data.expectedDurationHours ?? ''}
        onChange={(e) =>
          updateNodeData(nodeId, {
            expectedDurationHours: e.target.value ? parseFloat(e.target.value) : null,
          })
        }
      />
    </div>
  </div>
)}
```

### Alembic Migration Pattern
```python
# Source: Follows existing pattern from phase16_001_events_notifications.py
def upgrade() -> None:
    op.add_column('activity_templates',
        sa.Column('escalation_action', sa.String(50), nullable=True))
    op.add_column('activity_templates',
        sa.Column('warning_threshold_hours', sa.Float(), nullable=True))
    op.add_column('work_items',
        sa.Column('is_escalated', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('work_items',
        sa.Column('deadline_warning_sent', sa.Boolean(), nullable=False, server_default='false'))
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | pyproject.toml |
| Quick run command | `python -m pytest src/tests/ -x -q` |
| Full suite command | `python -m pytest src/tests/ --cov=app` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TIMER-01 | Activity template accepts deadline/escalation config via API | unit | `python -m pytest src/tests/test_timer_escalation.py::test_activity_template_deadline_config -x` | Wave 0 |
| TIMER-02 | Work item gets due_date when activity template has deadline | unit | `python -m pytest src/tests/test_timer_escalation.py::test_work_item_due_date_computed -x` | Wave 0 |
| TIMER-03 | Deadline checker finds overdue items | unit | `python -m pytest src/tests/test_timer_escalation.py::test_deadline_checker_finds_overdue -x` | Wave 0 |
| TIMER-04 | Escalation bumps priority / reassigns / notifies | unit | `python -m pytest src/tests/test_timer_escalation.py::test_escalation_priority_bump -x` | Wave 0 |
| NOTIF-03 | Warning notification sent before deadline | unit | `python -m pytest src/tests/test_timer_escalation.py::test_approaching_deadline_notification -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest src/tests/test_timer_escalation.py -x -q`
- **Per wave merge:** `python -m pytest src/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/tests/test_timer_escalation.py` -- covers TIMER-01 through TIMER-04, NOTIF-03

## Open Questions

1. **Warning threshold default**
   - What we know: `warning_threshold_hours` is per-activity template. If null, no warning notification fires.
   - What's unclear: Should there be a global default (e.g., 2 hours before deadline)?
   - Recommendation: If `warning_threshold_hours` is null but `expected_duration_hours` is set, default to 25% of the deadline duration (i.e., warn at 75% elapsed). This avoids silent deadlines.

2. **Reassignment target for escalation**
   - What we know: `WorkflowInstance.supervisor_id` exists and is the natural escalation target.
   - What's unclear: What if supervisor_id is null?
   - Recommendation: Fall back to notification-only if no supervisor. Log a warning.

3. **Priority bump magnitude**
   - What we know: Priority is an integer where lower = higher priority (default 5).
   - What's unclear: How much to bump?
   - Recommendation: Decrease by 2 (e.g., 5 -> 3), clamped at 1. Simple and visible.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/app/models/workflow.py` -- WorkItem.due_date already exists, ActivityTemplate.expected_duration_hours already exists
- Codebase inspection: `src/app/tasks/notification.py` -- Placeholder `check_approaching_deadlines` ready for implementation
- Codebase inspection: `src/app/celery_app.py` -- Beat schedule entry at 300s
- Codebase inspection: `src/app/services/engine_service.py` -- 7 WorkItem constructor sites identified
- Codebase inspection: `src/app/services/notification_service.py` -- create_notification with Redis pub/sub
- Codebase inspection: `frontend/src/components/designer/PropertiesPanel.tsx` -- Node properties pattern
- Codebase inspection: `frontend/src/hooks/useSaveTemplate.ts` -- Save flow sends activity data fields
- STATE.md decision: "Database-backed Beat polling for all timers -- never use Celery ETA tasks"

### Secondary (MEDIUM confidence)
- STATE.md: "Deadline beat task is a placeholder until Phase 17 adds WorkItem.due_date"
- STATE.md: "NOTIF-03 deferred to Phase 17 (requires WorkItem.due_date)"

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, all existing infrastructure
- Architecture: HIGH - all patterns derived from existing codebase inspection
- Pitfalls: HIGH - identified from actual code structure (7 constructor sites, dedup needs)

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable -- no external dependency changes expected)
