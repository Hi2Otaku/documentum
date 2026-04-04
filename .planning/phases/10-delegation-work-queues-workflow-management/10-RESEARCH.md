# Phase 10: Delegation, Work Queues & Workflow Management - Research

**Researched:** 2026-04-04
**Domain:** Workflow engine extensions (delegation, queues, admin control, audit query)
**Confidence:** HIGH

## Summary

Phase 10 adds three major feature areas to the existing workflow engine: (1) user delegation so unavailable users' tasks auto-route to a delegate, (2) work queues for shared task pools where any qualified member can claim work, and (3) admin workflow control operations (halt/resume/abort/restart) plus a queryable audit trail.

The codebase is well-structured with established patterns. All three feature areas build directly on existing infrastructure: the User model needs two new fields, PerformerType needs a QUEUE value, engine_service's `resolve_performers` needs a queue case, inbox_service's acquire/release pattern is reused for queue claims, and the engine's `WORKFLOW_TRANSITIONS` map already defines the RUNNING<->HALTED and FAILED->DORMANT transitions needed for admin control. The AuditLog model already has all needed columns (entity_type, entity_id, action, user_id, timestamp) with proper indexes for the query endpoint.

**Primary recommendation:** Build incrementally in three layers: (1) delegation model + engine integration, (2) work queue model + CRUD + engine integration, (3) admin workflow control endpoints + audit query endpoint. Each layer has clear boundaries and can be tested independently.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Toggle + single delegate -- User sets `is_available=false` and designates one delegate user via `PUT /api/v1/users/me/availability`. New work items auto-route to the delegate. Existing items stay with the original user. Toggle back when available.
- **D-02:** Add `is_available` (boolean, default true) and `delegate_id` (nullable FK to users) fields on the User model.
- **D-03:** Engine's performer resolution checks availability before assigning work items. If user is unavailable and has a delegate, the work item goes to the delegate instead. Audit trail logs "delegated from X to Y".
- **D-04:** New `WorkQueue` model with id, name, description, created_at. Many-to-many `WorkQueueMember` join table (queue_id, user_id) for qualified members.
- **D-05:** New `PerformerType.QUEUE` enum value. When an activity's performer_type is QUEUE, performer_id references the queue. Engine creates ONE shared work item visible to all queue members.
- **D-06:** Claim via existing `POST /inbox/{id}/acquire` -- locks item to claiming user. Release via `POST /inbox/{id}/release`. Prevents double-work.
- **D-07:** Queue CRUD endpoints: `POST/GET/PUT/DELETE /api/v1/queues/`, with member management (`POST/DELETE /api/v1/queues/{id}/members`). Admin-only.
- **D-08:** Action endpoints on workflow resource: halt, resume, abort, restart with specified state transitions.
- **D-09:** Each operation validates current state, transitions atomically, and logs to audit trail. Admin-only (superuser check).
- **D-10:** Filtered workflow list: `GET /api/v1/workflows/` with query params: state, template_id, created_by, date range. Admin-only enhanced view.
- **D-11:** `GET /api/v1/audit/` with query params: user_id, workflow_id, document_id, action_type, date_from, date_to. Paginated. Admin-only.

### Claude's Discretion
- WorkQueue model details (additional fields if needed)
- SUSPENDED work item state implementation (new enum value vs reuse existing)
- Restart behavior details (what gets cleared, whether to preserve variables)
- Inbox query modifications for queue-based items (how queue members see shared items)
- Alembic migration strategy for new models/fields

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| USER-05 | User can mark themselves as unavailable and designate a delegate | D-01, D-02: User model fields + availability endpoint |
| INBOX-08 | If performer is unavailable, work item automatically routes to delegated user | D-03: Engine performer resolution delegation check |
| QUEUE-01 | Admin can create work queues and assign qualified users | D-04, D-07: WorkQueue model + CRUD endpoints |
| QUEUE-02 | Activities can be assigned to a work queue instead of a specific user | D-05: PerformerType.QUEUE + engine integration |
| QUEUE-03 | Any qualified user in the queue can claim a task | D-05, D-06: Shared work item + acquire pattern |
| QUEUE-04 | Claimed tasks are locked to the claiming user until released or completed | D-06: Reuse existing acquire/release in inbox_service |
| MGMT-01 | Admin can halt a running workflow (pause execution) | D-08: POST /workflows/{id}/halt |
| MGMT-02 | Admin can resume a halted workflow | D-08: POST /workflows/{id}/resume |
| MGMT-03 | Admin can abort a workflow (terminate, mark as Failed) | D-08: POST /workflows/{id}/abort |
| MGMT-04 | Admin can view all running workflow instances with current state and active activity | D-10: Enhanced GET /workflows/ with filters |
| MGMT-05 | Admin can restart a failed workflow from Dormant state | D-08: POST /workflows/{id}/restart |
| AUDIT-05 | Admin can query audit trail by user, workflow, document, date range, or action type | D-11: GET /api/v1/audit/ with query params |
</phase_requirements>

## Architecture Patterns

### Recommended Project Structure (new/modified files)

```
src/app/
  models/
    user.py           # MODIFY: add is_available, delegate_id fields
    enums.py           # MODIFY: add PerformerType.QUEUE, WorkItemState.SUSPENDED
    workflow.py        # MODIFY: add WorkQueue, WorkQueueMember models
  schemas/
    user.py            # MODIFY: add AvailabilityUpdate schema, extend UserResponse
    queue.py           # NEW: WorkQueue CRUD schemas
    workflow.py        # MODIFY: add admin workflow list response schema
    audit.py           # MODIFY: add query params schema
  services/
    engine_service.py  # MODIFY: resolve_performers for QUEUE, delegation check
    inbox_service.py   # MODIFY: inbox query includes queue-based items
    queue_service.py   # NEW: WorkQueue CRUD + member management
    workflow_mgmt_service.py  # NEW: halt/resume/abort/restart logic
  routers/
    users.py           # MODIFY: add PUT /users/me/availability
    queues.py          # NEW: queue CRUD + member endpoints
    workflows.py       # MODIFY: add halt/resume/abort/restart + enhanced list
    audit.py           # NEW: audit query endpoint
tests/
  test_delegation.py   # NEW
  test_queues.py       # NEW
  test_workflow_mgmt.py # NEW
  test_audit_query.py  # NEW
alembic/versions/
  phase10_001_delegation_queues.py  # NEW
```

### Pattern 1: Delegation Check in Performer Resolution

**What:** Before assigning a work item, check if the target user is unavailable and has a delegate. If so, redirect to the delegate.
**When to use:** Every time `resolve_performers` returns user IDs, apply delegation check before creating work items.
**Example:**
```python
# In engine_service.py, after resolve_performers returns user_ids
async def _apply_delegation(
    db: AsyncSession,
    user_ids: list[uuid.UUID],
    audit_user_id: str,
) -> list[uuid.UUID]:
    """Replace unavailable users with their delegates."""
    if not user_ids:
        return user_ids
    
    from app.models.user import User
    result = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users = {u.id: u for u in result.scalars().all()}
    
    resolved = []
    for uid in user_ids:
        user = users.get(uid)
        if user and not user.is_available and user.delegate_id:
            resolved.append(user.delegate_id)
            await create_audit_record(
                db,
                entity_type="work_item",
                entity_id="",  # filled by caller
                action="work_item_delegated",
                user_id=audit_user_id,
                after_state={
                    "original_performer": str(uid),
                    "delegated_to": str(user.delegate_id),
                },
            )
        else:
            resolved.append(uid)
    return resolved
```

### Pattern 2: Queue Performer Resolution

**What:** When performer_type is QUEUE, create one shared work item with performer_id=NULL, visible to all queue members.
**When to use:** In the engine's work item creation path when activity has PerformerType.QUEUE.
**Example:**
```python
# In resolve_performers, add QUEUE case:
case "queue":
    # Return empty list -- queue items use special creation path
    # The caller creates ONE work item with performer_id=None
    # and a queue_id reference
    return []
```

The key insight is that queue work items differ from normal items: they have no specific performer_id until claimed. The inbox query must be modified to also show items belonging to queues the user is a member of.

### Pattern 3: Admin Workflow Control (Atomic State Transitions)

**What:** Each admin action validates current state, transitions atomically, updates related work items, and audits.
**When to use:** For halt/resume/abort/restart endpoints.
**Example:**
```python
async def halt_workflow(
    db: AsyncSession, workflow_id: uuid.UUID, admin_id: str
) -> WorkflowInstance:
    result = await db.execute(
        select(WorkflowInstance)
        .with_for_update()  # Row-level lock
        .where(WorkflowInstance.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if workflow is None:
        raise ValueError("Workflow not found")
    
    _enforce_workflow_transition(workflow.state, WorkflowState.HALTED)
    workflow.state = WorkflowState.HALTED
    
    # Suspend active work items
    wi_result = await db.execute(
        select(WorkItem)
        .join(ActivityInstance)
        .where(
            ActivityInstance.workflow_instance_id == workflow_id,
            WorkItem.state == WorkItemState.AVAILABLE,
        )
    )
    for wi in wi_result.scalars().all():
        wi.state = WorkItemState.SUSPENDED
    
    await create_audit_record(...)
    await db.flush()
    return workflow
```

### Pattern 4: Inbox Query Extension for Queue Items

**What:** Modify `get_inbox_items` to include items from queues the user belongs to, in addition to items directly assigned.
**When to use:** When building the inbox query WHERE clause.
**Example:**
```python
# Extend the base WHERE conditions in get_inbox_items:
from app.models.workflow import WorkQueue, WorkQueueMember

# Items either assigned directly to user OR belong to a queue user is member of
conditions = [
    WorkItem.is_deleted == False,
    or_(
        WorkItem.performer_id == uuid.UUID(user_id),  # Direct assignment
        and_(
            WorkItem.queue_id.isnot(None),              # Queue item
            WorkItem.performer_id.is_(None),             # Not yet claimed
            WorkItem.queue_id.in_(
                select(WorkQueueMember.queue_id).where(
                    WorkQueueMember.user_id == uuid.UUID(user_id)
                )
            ),
        ),
    ),
]
```

### Anti-Patterns to Avoid
- **Delegation chains:** Do NOT follow delegation transitively (A delegates to B who delegates to C). Only follow one level. The delegate must be available, or the item stays with the original user. This prevents infinite loops.
- **Modifying existing work items on delegation toggle:** When a user toggles unavailable, do NOT reassign their existing work items. Only new items get delegated per D-01.
- **Creating multiple work items for queue activities:** Create exactly ONE work item with performer_id=NULL. Do not create one per queue member (that is the GROUP pattern, not QUEUE).
- **Mixing halt logic into engine advancement:** Keep admin workflow control in a separate service (workflow_mgmt_service.py). The engine service handles normal advancement; management operations are distinct admin actions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent claim safety | Custom locking mechanism | SQLAlchemy `with_for_update()` (already used in acquire) | Row-level DB locking is battle-tested; custom locks have race conditions |
| Paginated query building | Manual OFFSET/LIMIT with count | Existing pattern from inbox_service (subquery count + offset/limit) | Already proven in codebase, consistent API |
| State machine transitions | Custom if/else chains | Existing `WORKFLOW_TRANSITIONS` set + `_enforce_workflow_transition` | Already defined in engine_service, reuse for consistency |
| Admin auth check | Custom permission logic | Existing `get_current_active_admin` dependency | Already used across admin endpoints |

**Key insight:** Almost every infrastructure pattern needed by this phase already exists in the codebase. The primary work is extending existing models and services, not building new infrastructure.

## Common Pitfalls

### Pitfall 1: Queue Work Item Visibility in Inbox
**What goes wrong:** Queue items have performer_id=NULL until claimed. The inbox query filters by `performer_id == current_user.id`, so queue items are invisible.
**Why it happens:** The existing inbox query assumes every item has a specific performer.
**How to avoid:** Add an OR condition to the inbox query: show items where performer_id matches OR where item has a queue_id and user is a queue member. Add a `queue_id` nullable FK column to WorkItem.
**Warning signs:** Queue members see empty inboxes despite active queue work items.

### Pitfall 2: SUSPENDED Work Item State and Enum Migration
**What goes wrong:** Adding SUSPENDED to WorkItemState enum requires database migration. SQLite (test DB) handles enums as strings so it works in tests, but PostgreSQL uses actual ENUM types that must be altered.
**Why it happens:** PostgreSQL enums are immutable by default; adding a value requires ALTER TYPE.
**How to avoid:** Use Alembic's `op.execute("ALTER TYPE workitemstate ADD VALUE 'suspended'")` in the migration. Test with both SQLite and PostgreSQL to catch this.
**Warning signs:** Migration fails on PostgreSQL but passes in SQLite tests.

### Pitfall 3: Delegation Audit Trail Missing Context
**What goes wrong:** Audit record for delegation doesn't include which workflow/activity triggered it, making it hard to trace.
**Why it happens:** Delegation happens deep in performer resolution where workflow context is available but not passed to audit.
**How to avoid:** Pass workflow_instance_id and activity details through to the delegation audit record. Use the `details` field on AuditLog for context.
**Warning signs:** Audit query returns delegation records with no way to correlate to specific workflows.

### Pitfall 4: Restart Clearing Too Much or Too Little
**What goes wrong:** Restarting a FAILED workflow either preserves stale state (causing re-execution bugs) or clears too much (losing document attachments).
**Why it happens:** Unclear what "restart from Dormant" means for activity instances, work items, execution tokens, and variables.
**How to avoid:** Restart should: (1) set workflow state to DORMANT, (2) reset all activity instances to DORMANT, (3) delete all work items and execution tokens, (4) preserve process variables and workflow packages (documents). The user starts the workflow again normally.
**Warning signs:** Restarted workflows have orphan work items or missing document attachments.

### Pitfall 5: Halt Not Suspending Acquired Items
**What goes wrong:** When halting a workflow, only AVAILABLE items are suspended. ACQUIRED items remain claimable/completable, allowing the workflow to advance while "halted."
**Why it happens:** The halt logic only looks at AVAILABLE state, missing ACQUIRED items.
**How to avoid:** Halt should suspend BOTH available and acquired work items. Resume should restore them to their previous states. Track the pre-halt state in a JSON field or use the audit trail to reconstruct.
**Warning signs:** Users can still complete tasks in halted workflows.

### Pitfall 6: Acquire Authorization for Queue Items
**What goes wrong:** The existing `acquire_work_item` checks `performer_id == user_id` for authorization. Queue items have performer_id=NULL, so nobody can acquire them.
**Why it happens:** Authorization logic assumes direct assignment.
**How to avoid:** For queue items (where queue_id is set), check queue membership instead of performer_id match. The acquire function should verify the user is a member of the item's queue.
**Warning signs:** Queue members get "Not authorized" errors when trying to claim queue items.

## Code Examples

### User Model Extension
```python
# In src/app/models/user.py - add to User class
is_available: Mapped[bool] = mapped_column(
    Boolean, default=True, nullable=False, server_default="true"
)
delegate_id: Mapped[uuid.UUID | None] = mapped_column(
    Uuid(), ForeignKey("users.id"), nullable=True
)
```

### WorkQueue Model
```python
# In src/app/models/workflow.py or separate queue.py
class WorkQueue(BaseModel):
    __tablename__ = "work_queues"
    
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    members: Mapped[list["User"]] = relationship(
        secondary="work_queue_members", backref="work_queues"
    )

work_queue_members = Table(
    "work_queue_members",
    BaseModel.metadata,
    Column("queue_id", Uuid(), ForeignKey("work_queues.id"), primary_key=True),
    Column("user_id", Uuid(), ForeignKey("users.id"), primary_key=True),
)
```

### WorkItem Extension for Queue Reference
```python
# Add to WorkItem model
queue_id: Mapped[uuid.UUID | None] = mapped_column(
    Uuid(), ForeignKey("work_queues.id"), nullable=True
)
```

### SUSPENDED Enum Value
```python
# In enums.py, add to WorkItemState:
SUSPENDED = "suspended"
```

### Work Item State Transitions Extension
```python
# Add to WORK_ITEM_TRANSITIONS in engine_service.py:
(WorkItemState.AVAILABLE, WorkItemState.SUSPENDED),   # Halt
(WorkItemState.ACQUIRED, WorkItemState.SUSPENDED),    # Halt
(WorkItemState.SUSPENDED, WorkItemState.AVAILABLE),   # Resume
```

### Availability Endpoint Schema
```python
# In schemas/user.py
class AvailabilityUpdate(BaseModel):
    is_available: bool
    delegate_id: uuid.UUID | None = None
```

### Audit Query Endpoint
```python
# In routers/audit.py
@router.get("", response_model=EnvelopeResponse[list[AuditLogResponse]])
async def query_audit(
    user_id: str | None = Query(None),
    workflow_id: str | None = Query(None),
    document_id: str | None = Query(None),
    action_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Query audit trail with filters. Admin only."""
    # Build dynamic WHERE clauses based on provided params
    conditions = []
    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    if workflow_id:
        # entity_type='workflow' AND entity_id=workflow_id
        # OR details contain workflow reference
        conditions.append(AuditLog.entity_id == workflow_id)
    if document_id:
        conditions.append(AuditLog.entity_id == document_id)
    if action_type:
        conditions.append(AuditLog.action == action_type)
    if date_from:
        conditions.append(AuditLog.timestamp >= date_from)
    if date_to:
        conditions.append(AuditLog.timestamp <= date_to)
    ...
```

## Discretion Recommendations

### SUSPENDED Work Item State
**Recommendation:** Add `SUSPENDED = "suspended"` as a new WorkItemState enum value rather than reusing an existing state. Reasons:
1. SUSPENDED has distinct semantics: it means "halted by admin," not "completed" or "delegated."
2. When resuming, suspended items must return to their pre-halt state (AVAILABLE or ACQUIRED). Using a different state makes this distinction clear.
3. Track the pre-halt state by storing it in the audit trail's `before_state` field during halt, then reading it back during resume.

### Restart Behavior
**Recommendation:** Restart (FAILED -> DORMANT) should:
- Reset all activity instances to DORMANT state
- Delete all existing work items (they are stale from the failed run)
- Delete all execution tokens (stale)
- PRESERVE process variables (user may want to adjust before re-running)
- PRESERVE workflow packages (document attachments stay)
- After restart, the admin or supervisor calls the normal start mechanism to re-run

### Inbox Query for Queue Items
**Recommendation:** Add `queue_id` nullable FK to the WorkItem model. Modify `get_inbox_items` with an OR condition:
- Show items where `performer_id == current_user_id` (existing behavior)
- OR items where `queue_id IS NOT NULL AND performer_id IS NULL AND queue_id IN (user's queue memberships)`
- Queue items should display with a visual indicator (e.g., include `queue_name` in response)

### WorkQueue Model Additional Fields
**Recommendation:** Keep it minimal per D-04, just add `is_active` boolean for soft-disable capability:
```python
is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

### Alembic Migration Strategy
**Recommendation:** Single migration file `phase10_001_delegation_queues.py` containing:
1. Add `is_available` and `delegate_id` columns to users table
2. Create `work_queues` table
3. Create `work_queue_members` join table
4. Add `queue_id` column to work_items table
5. Add `SUSPENDED` value to workitemstate enum
6. Add `QUEUE` value to performertype enum

All in one migration since these changes are deployed together. Use `op.execute` for PostgreSQL enum alterations.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `tests/conftest.py` (session-scoped fixtures, SQLite in-memory) |
| Quick run command | `cd src && python -m pytest tests/ -x -q` |
| Full suite command | `cd src && python -m pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| USER-05 | Toggle availability + set delegate | integration | `cd src && python -m pytest tests/test_delegation.py::test_set_availability -x` | No - Wave 0 |
| INBOX-08 | Auto-route to delegate | integration | `cd src && python -m pytest tests/test_delegation.py::test_delegation_routing -x` | No - Wave 0 |
| QUEUE-01 | Queue CRUD + member management | integration | `cd src && python -m pytest tests/test_queues.py::test_queue_crud -x` | No - Wave 0 |
| QUEUE-02 | Activity assigned to queue | integration | `cd src && python -m pytest tests/test_queues.py::test_queue_performer -x` | No - Wave 0 |
| QUEUE-03 | Queue member claims task | integration | `cd src && python -m pytest tests/test_queues.py::test_queue_claim -x` | No - Wave 0 |
| QUEUE-04 | Claimed task locked | integration | `cd src && python -m pytest tests/test_queues.py::test_queue_lock -x` | No - Wave 0 |
| MGMT-01 | Halt workflow | integration | `cd src && python -m pytest tests/test_workflow_mgmt.py::test_halt -x` | No - Wave 0 |
| MGMT-02 | Resume workflow | integration | `cd src && python -m pytest tests/test_workflow_mgmt.py::test_resume -x` | No - Wave 0 |
| MGMT-03 | Abort workflow | integration | `cd src && python -m pytest tests/test_workflow_mgmt.py::test_abort -x` | No - Wave 0 |
| MGMT-04 | List workflows with filters | integration | `cd src && python -m pytest tests/test_workflow_mgmt.py::test_list_filtered -x` | No - Wave 0 |
| MGMT-05 | Restart failed workflow | integration | `cd src && python -m pytest tests/test_workflow_mgmt.py::test_restart -x` | No - Wave 0 |
| AUDIT-05 | Query audit trail | integration | `cd src && python -m pytest tests/test_audit_query.py::test_audit_query -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd src && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd src && python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_delegation.py` -- covers USER-05, INBOX-08
- [ ] `tests/test_queues.py` -- covers QUEUE-01 through QUEUE-04
- [ ] `tests/test_workflow_mgmt.py` -- covers MGMT-01 through MGMT-05
- [ ] `tests/test_audit_query.py` -- covers AUDIT-05

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual delegation via admin reassignment | Self-service availability toggle | This phase | Users manage their own delegation |
| Per-user task assignment only | Work queue pools | This phase | Enables shared workload distribution |
| No admin workflow control | Halt/resume/abort/restart | This phase | Production workflow management capability |

## Open Questions

1. **Pre-halt state tracking for resume**
   - What we know: When halting, AVAILABLE and ACQUIRED items become SUSPENDED. When resuming, they need to return to their previous state.
   - What's unclear: Whether to track pre-halt state in a new column on WorkItem or reconstruct from audit trail.
   - Recommendation: Use the audit trail `before_state` field. The halt operation records each item's previous state. Resume reads the most recent halt audit record to restore. This avoids a new column and uses existing infrastructure.

2. **Queue items in inbox detail view**
   - What we know: `get_inbox_item_detail` checks `performer_id == user_id` for authorization.
   - What's unclear: How to authorize access to unclaimed queue items for the detail view.
   - Recommendation: For unclaimed queue items, check queue membership instead. After claiming, the normal performer_id check works.

## Project Constraints (from CLAUDE.md)

- **Tech stack:** Python/FastAPI backend, SQLAlchemy 2.0 async ORM, PostgreSQL
- **Testing:** pytest with aiosqlite in-memory for tests (no Docker required)
- **Service layer pattern:** Routers delegate to service functions; services handle business logic and audit
- **Audit:** All mutations logged via `create_audit_record` in same transaction
- **Admin auth:** `get_current_active_admin` dependency for admin-only endpoints
- **Response format:** `EnvelopeResponse` wrapper with `PaginationMeta` for paginated endpoints
- **Enums:** Use lowercase naming convention for enum type names in PostgreSQL
- **Models:** Dialect-agnostic (sqlalchemy.Uuid, JSON not JSONB) for SQLite test compatibility
- **Migrations:** Alembic manual migrations when Docker/PostgreSQL unavailable
- **Error pattern:** Service layer raises ValueError; router maps to HTTP 400

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis (all source files listed in Canonical References)
- `src/app/services/engine_service.py` -- WORKFLOW_TRANSITIONS, resolve_performers, state machine
- `src/app/services/inbox_service.py` -- acquire/release pattern with row-level locking
- `src/app/models/enums.py` -- all current enum values
- `src/app/models/workflow.py` -- WorkItem, WorkflowInstance models
- `src/app/models/user.py` -- User model structure
- `src/app/models/audit.py` -- AuditLog model with indexes
- `src/app/schemas/common.py` -- EnvelopeResponse, PaginationMeta patterns

### Secondary (MEDIUM confidence)
- Alembic migration patterns from `alembic/versions/` -- PostgreSQL enum extension strategy

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed, all existing stack
- Architecture: HIGH -- extends established codebase patterns with clear integration points
- Pitfalls: HIGH -- identified from direct code analysis of existing patterns and edge cases

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable, internal codebase patterns)
