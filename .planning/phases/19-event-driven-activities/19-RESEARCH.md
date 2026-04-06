# Phase 19: Event-Driven Activities - Research

**Researched:** 2026-04-06
**Domain:** Workflow engine event-driven activity type, event bus subscription, frontend designer integration
**Confidence:** HIGH

## Summary

Phase 19 adds an `EVENT` activity type to the workflow engine. When the engine encounters an EVENT activity during advancement, it leaves the activity in ACTIVE state (similar to how SUB_WORKFLOW activities wait for child completion). An event bus handler registered for the configured event types (`document.uploaded`, `lifecycle.changed`, `workflow.completed`) checks whether any active EVENT activity instances match the fired event, and if so, completes the activity and advances the workflow.

The existing codebase provides all infrastructure needed. The event bus (Phase 16) already supports `@event_bus.on("event_type")` handler registration with automatic dispatch after event persistence. The engine's `_advance_from_activity` already handles multiple activity types via a match block in the activation loop. Phase 18's sub-workflow pattern (activity stays ACTIVE, event handler calls `_advance_from_activity` on match) is the exact pattern EVENT activities should follow.

**Primary recommendation:** Add `EVENT` to the `ActivityType` enum, add `event_type_filter` and `event_filter_config` columns to `ActivityTemplate`, register wildcard event handlers for the three supported event types, and create an `EventNode` component in the frontend designer.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVTACT-01 | Admin can add an EVENT activity type in the workflow designer with event filter configuration | New `EVENT` enum value, `event_type_filter` + `event_filter_config` columns on ActivityTemplate, EventNode frontend component, PropertiesPanel event config section |
| EVTACT-02 | EVENT activities complete automatically when a matching domain event fires | Event bus handlers for `document.uploaded`, `lifecycle.changed`, `workflow.completed` that query active EVENT activity instances and call `_advance_from_activity` |
| EVTACT-03 | Supported event types include document.uploaded, lifecycle.changed, and workflow.completed | Three handlers registered via `@event_bus.on()`, each checking active EVENT activities with matching `event_type_filter` |
</phase_requirements>

## Standard Stack

No new libraries required. This phase uses only existing infrastructure:

| Component | Already Exists | Purpose |
|-----------|---------------|---------|
| EventBus (`event_bus.py`) | Yes | Handler registration and event dispatch |
| DomainEvent model | Yes | Persistent event storage with `event_type`, `entity_type`, `entity_id`, `payload` |
| `_advance_from_activity` | Yes | Engine advancement after activity completion |
| ActivityType enum | Yes (needs `EVENT` added) | Activity type classification |
| React Flow node types | Yes (5 types) | Visual designer node rendering |

## Architecture Patterns

### Pattern 1: Activity Type Dispatch in Engine (established)

The engine's `_advance_from_activity` method uses a match block at line ~593-636 of `engine_service.py` to handle different activity types when they are activated:

- `START/END`: Auto-complete immediately, append to queue
- `AUTO`: Leave ACTIVE, Celery Workflow Agent picks up later
- `SUB_WORKFLOW`: Leave ACTIVE, spawn child workflow; event handler resumes on child completion
- **`EVENT` (new)**: Leave ACTIVE, event bus handler completes on matching event

The EVENT type follows the SUB_WORKFLOW pattern exactly: the engine activates the activity but does NOT complete it or create work items. An event bus handler is responsible for completing it later.

```python
# In _advance_from_activity, add to the match block:
elif target_at.activity_type == ActivityType.EVENT:
    # Leave as ACTIVE -- event handler will complete when matching event fires
    pass
```

### Pattern 2: Event Handler Resumption (established by Phase 18)

The `_resume_parent_on_child_complete` handler in `event_handlers.py` demonstrates the pattern:
1. Receive a DomainEvent via `@event_bus.on("workflow.completed")`
2. Query for the relevant waiting entity (ActivityInstance in ACTIVE state)
3. Load the parent workflow + template with relations
4. Build `template_to_instance` mapping
5. Call `_advance_from_activity` to resume the workflow

EVENT activity handlers follow this same pattern but query for active EVENT ActivityInstances where the template's `event_type_filter` matches the fired event type.

```python
@event_bus.on("document.uploaded")
async def _complete_event_activities_on_document_uploaded(db: AsyncSession, event: DomainEvent) -> None:
    """Complete any EVENT activities waiting for document.uploaded."""
    await _try_complete_event_activities(db, event, "document.uploaded")

@event_bus.on("lifecycle.changed")
async def _complete_event_activities_on_lifecycle_changed(db: AsyncSession, event: DomainEvent) -> None:
    await _try_complete_event_activities(db, event, "lifecycle.changed")

@event_bus.on("workflow.completed")
async def _complete_event_activities_on_workflow_completed(db: AsyncSession, event: DomainEvent) -> None:
    await _try_complete_event_activities(db, event, "workflow.completed")
```

The shared `_try_complete_event_activities` function:
1. Query all ActivityInstances with state=ACTIVE where the linked ActivityTemplate has `activity_type=EVENT` and `event_type_filter` matches
2. Optionally check `event_filter_config` against event payload (e.g., specific document_id, lifecycle state)
3. For each match, load the workflow, template, and advance

### Pattern 3: ActivityTemplate Column Extension (established by Phase 18)

Phase 18 added `sub_template_id` and `variable_mapping` to ActivityTemplate. EVENT activities need:

| Column | Type | Purpose |
|--------|------|---------|
| `event_type_filter` | `String(255)`, nullable | Which event type this EVENT activity listens for (e.g., `document.uploaded`) |
| `event_filter_config` | `JSON`, nullable | Optional filter criteria on event payload (e.g., `{"entity_id": "{{doc_id}}"}` or `{"lifecycle_state": "approved"}`) |

These columns are nullable and only meaningful when `activity_type == EVENT`.

### Pattern 4: Frontend Node Component (established)

Each activity type has a dedicated React Flow node component following the pattern:
- `src/components/nodes/{Type}Node.tsx` -- visual rendering
- Registered in `src/components/nodes/index.ts` nodeTypes map
- Type-specific config in `PropertiesPanel.tsx` (conditional render block)
- Node defaults in `Canvas.tsx` NODE_DEFAULTS

### Recommended Changes

```
Backend:
  src/app/models/enums.py             # Add EVENT to ActivityType
  src/app/models/workflow.py           # Add event_type_filter + event_filter_config to ActivityTemplate
  src/app/schemas/template.py          # Add fields to Create/Update/Response schemas
  src/app/services/engine_service.py   # Add EVENT case in _advance_from_activity
  src/app/services/event_handlers.py   # Add 3 event handlers + shared _try_complete function
  src/app/services/template_service.py # Add MISSING_EVENT_TYPE validation rule
  alembic/versions/phase19_001_*.py    # Migration: enum value + columns

Frontend:
  frontend/src/types/designer.ts       # Add 'event' to activityType union, add eventTypeFilter + eventFilterConfig
  frontend/src/components/nodes/EventNode.tsx    # New node component
  frontend/src/components/nodes/index.ts         # Register EventNode
  frontend/src/components/designer/Canvas.tsx    # Add NODE_DEFAULTS entry
  frontend/src/components/designer/PropertiesPanel.tsx  # Event config section

Tests:
  tests/test_event_activities.py       # New test file
```

### Anti-Patterns to Avoid

- **Polling for events:** Do NOT use a Celery Beat task to poll for matching events. The event bus handler pattern is synchronous with event emission, which is simpler and more immediate.
- **Generic wildcard handler:** Do NOT register a single `*` handler for all events and filter inside. Register one handler per supported event type for clarity and performance.
- **Complex filter expressions at v1:** EVTACT-04 (complex filter expressions) is explicitly deferred. Keep `event_filter_config` as simple key-value matching against event payload, not a full expression evaluator.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Event subscription | Custom pub/sub system | Existing `EventBus.on()` decorator | Already built, tested, and used by Phase 16/18 |
| Workflow advancement | Custom state machine | Existing `_advance_from_activity` | Handles tokens, joins, routing, lifecycle hooks |
| Activity state management | Manual state updates | Existing state transition enforcement | ACTIVITY_TRANSITIONS set prevents invalid transitions |

## Common Pitfalls

### Pitfall 1: Race condition -- event fires before activity is activated
**What goes wrong:** A domain event fires in the same transaction that starts the workflow, but the EVENT activity hasn't been activated yet (it's still DORMANT because the engine hasn't advanced to it).
**Why it happens:** Events are dispatched synchronously within the same `db.flush()` call chain.
**How to avoid:** The handler queries for `ActivityState.ACTIVE` EVENT instances. If none are active yet, the event simply has no matching listeners -- this is correct behavior. The activity will wait for the NEXT matching event.
**Warning signs:** Test expects first event to complete the activity but it doesn't.

### Pitfall 2: Multiple EVENT activities matching the same event
**What goes wrong:** Two different workflow instances (or two parallel branches in the same workflow) both have EVENT activities waiting for `document.uploaded`. A single document upload completes both.
**Why it happens:** The handler queries all active EVENT activities with matching filter.
**How to avoid:** This is actually correct behavior -- if both activities are legitimately waiting for the same event, both should complete. But if specificity is needed, the `event_filter_config` should filter by entity_id or other payload attributes.
**Warning signs:** Unexpected workflow advancement in unrelated workflows.

### Pitfall 3: Forgetting to handle the EVENT type in template validation
**What goes wrong:** An EVENT activity without `event_type_filter` passes validation and causes a silent no-op at runtime.
**How to avoid:** Add a `MISSING_EVENT_TYPE` validation rule in `template_service.py::validate_template()`, following the pattern of `MISSING_METHOD` for AUTO and `MISSING_SUB_TEMPLATE` for SUB_WORKFLOW.

### Pitfall 4: Variable substitution in event_filter_config
**What goes wrong:** Admin configures `event_filter_config: {"entity_id": "{{doc_id}}"}` expecting the engine to substitute the process variable value at runtime.
**Why it happens:** Simple JSON comparison won't resolve template variables.
**How to avoid:** For v1, support only literal values in `event_filter_config`. Variable substitution in filters is the kind of complexity that belongs in deferred EVTACT-04. Document this limitation.

### Pitfall 5: workflow.completed handler double-duty
**What goes wrong:** The existing `_resume_parent_on_child_complete` handler already listens for `workflow.completed`. Adding an EVENT activity handler for the same event type means both fire.
**Why it happens:** EventBus dispatches to ALL registered handlers for an event type.
**How to avoid:** This is fine -- both handlers run independently. The sub-workflow handler checks `parent_workflow_id` and returns early if not a sub-workflow. The EVENT activity handler checks for active EVENT activities. They don't conflict.

## Code Examples

### Adding EVENT to ActivityType enum

```python
# src/app/models/enums.py
class ActivityType(str, enum.Enum):
    START = "start"
    END = "end"
    MANUAL = "manual"
    AUTO = "auto"
    SUB_WORKFLOW = "sub_workflow"
    EVENT = "event"  # New
```

### ActivityTemplate columns

```python
# src/app/models/workflow.py -- ActivityTemplate class
event_type_filter: Mapped[str | None] = mapped_column(String(255), nullable=True)
event_filter_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

### Engine dispatch (in _advance_from_activity)

```python
elif target_at.activity_type == ActivityType.EVENT:
    # Leave as ACTIVE -- event bus handler will complete
    # when a matching domain event fires.
    # No work items created, no Celery task dispatched.
    pass
```

### Event handler pattern

```python
# src/app/services/event_handlers.py

async def _try_complete_event_activities(
    db: AsyncSession, event: DomainEvent, event_type: str
) -> None:
    """Find active EVENT activities matching this event and complete them."""
    # Query all active EVENT activity instances with matching event_type_filter
    result = await db.execute(
        select(ActivityInstance)
        .join(ActivityTemplate, ActivityInstance.activity_template_id == ActivityTemplate.id)
        .join(WorkflowInstance, ActivityInstance.workflow_instance_id == WorkflowInstance.id)
        .where(
            ActivityInstance.state == ActivityState.ACTIVE,
            ActivityTemplate.activity_type == ActivityType.EVENT,
            ActivityTemplate.event_type_filter == event_type,
            WorkflowInstance.state == WorkflowState.RUNNING,
        )
    )
    active_event_ais = list(result.scalars().all())

    for ai in active_event_ais:
        # Optional: check event_filter_config against event payload
        template_result = await db.execute(
            select(ActivityTemplate).where(ActivityTemplate.id == ai.activity_template_id)
        )
        at = template_result.scalar_one()
        if at.event_filter_config and event.payload:
            if not _matches_filter(at.event_filter_config, event.payload):
                continue

        # Load workflow + template for advancement
        wf_result = await db.execute(
            select(WorkflowInstance).where(WorkflowInstance.id == ai.workflow_instance_id)
        )
        workflow = wf_result.scalar_one()

        tmpl_result = await db.execute(
            select(ProcessTemplate)
            .options(
                selectinload(ProcessTemplate.activity_templates),
                selectinload(ProcessTemplate.flow_templates),
                selectinload(ProcessTemplate.process_variables),
            )
            .where(ProcessTemplate.id == workflow.process_template_id)
        )
        template = tmpl_result.scalar_one()

        # Build template_to_instance mapping
        ai_result = await db.execute(
            select(ActivityInstance).where(
                ActivityInstance.workflow_instance_id == workflow.id
            )
        )
        all_instances = list(ai_result.scalars().all())
        template_to_instance = {inst.activity_template_id: inst for inst in all_instances}

        # Load instance variables
        pv_result = await db.execute(
            select(ProcessVariable).where(
                ProcessVariable.workflow_instance_id == workflow.id,
                ProcessVariable.is_deleted == False,
            )
        )
        instance_variables = list(pv_result.scalars().all())

        # Advance the workflow
        from app.services.engine_service import _advance_from_activity
        await _advance_from_activity(
            db, workflow, ai, template, template_to_instance,
            user_id="system",
            instance_variables=instance_variables,
        )

    await db.flush()


def _matches_filter(filter_config: dict, payload: dict) -> bool:
    """Simple key-value match: all keys in filter_config must match payload values."""
    for key, expected in filter_config.items():
        actual = payload.get(key)
        if str(actual) != str(expected):
            return False
    return True
```

### Frontend EventNode

```typescript
// src/components/nodes/EventNode.tsx
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { Zap } from 'lucide-react';
import type { ActivityNodeData } from '../../types/designer';

type EventNodeType = Node<ActivityNodeData, 'eventNode'>;

export function EventNode({ data, selected }: NodeProps<EventNodeType>) {
  const eventHint = data.eventTypeFilter || 'No event configured';

  return (
    <div className={`min-w-[160px] min-h-[64px] ${
      selected ? 'ring-2 ring-primary ring-offset-2' : ''
    }`}>
      <div className="bg-amber-500 border-2 border-amber-600 text-white px-4 py-3 rounded">
        <div className="flex items-center gap-1.5">
          <Zap className="w-4 h-4 shrink-0" />
          <div className="font-semibold text-sm truncate">{data.name}</div>
        </div>
        <div className="text-sm opacity-70 truncate">{eventHint}</div>
      </div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
```

### Alembic migration pattern

```python
def upgrade() -> None:
    bind = op.get_bind()

    # Add EVENT to ActivityType enum
    if bind.dialect.name != "sqlite":
        op.execute("ALTER TYPE activitytype ADD VALUE IF NOT EXISTS 'event'")

    # Add event columns to activity_templates
    op.add_column("activity_templates",
        sa.Column("event_type_filter", sa.String(255), nullable=True))
    op.add_column("activity_templates",
        sa.Column("event_filter_config", sa.JSON(), nullable=True))
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_event_activities.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVTACT-01 | EVENT activity template creation with event_type_filter | unit | `pytest tests/test_event_activities.py::test_create_event_activity -x` | Wave 0 |
| EVTACT-01 | Template validation rejects EVENT without event_type_filter | unit | `pytest tests/test_event_activities.py::test_validate_event_missing_filter -x` | Wave 0 |
| EVTACT-02 | EVENT activity completes on matching document.uploaded event | integration | `pytest tests/test_event_activities.py::test_event_activity_completes_on_document_uploaded -x` | Wave 0 |
| EVTACT-02 | EVENT activity completes on matching lifecycle.changed event | integration | `pytest tests/test_event_activities.py::test_event_activity_completes_on_lifecycle_changed -x` | Wave 0 |
| EVTACT-02 | EVENT activity completes on matching workflow.completed event | integration | `pytest tests/test_event_activities.py::test_event_activity_completes_on_workflow_completed -x` | Wave 0 |
| EVTACT-02 | EVENT activity does NOT complete on non-matching event | integration | `pytest tests/test_event_activities.py::test_event_activity_ignores_non_matching_event -x` | Wave 0 |
| EVTACT-03 | All three event types are supported | integration | `pytest tests/test_event_activities.py -k "document_uploaded or lifecycle_changed or workflow_completed" -x` | Wave 0 |
| EVTACT-03 | EVENT activity with filter_config matches selectively | integration | `pytest tests/test_event_activities.py::test_event_filter_config_matching -x` | Wave 0 |
| ALL | EVENT activity does not block parallel branches | integration | `pytest tests/test_event_activities.py::test_event_activity_parallel_non_blocking -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_event_activities.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_event_activities.py` -- covers EVTACT-01, EVTACT-02, EVTACT-03
- Framework install: already configured in pyproject.toml

## Project Constraints (from CLAUDE.md)

- FastAPI backend with SQLAlchemy 2.0 async, PostgreSQL, Alembic migrations
- Event bus already built (Phase 16) with `@event_bus.on()` handler pattern
- React 19 + TypeScript + Vite + React Flow for frontend designer
- Celery for background tasks (not needed here -- EVENT activities use synchronous event bus handlers)
- All activity types follow the established engine dispatch pattern in `_advance_from_activity`

## Open Questions

1. **Event filter variable substitution**
   - What we know: `event_filter_config` stores JSON filter criteria
   - What's unclear: Whether process variable references (e.g., `{{doc_id}}`) should be resolved at runtime
   - Recommendation: For v1, support only literal values. EVTACT-04 (complex filter expressions) is deferred.

2. **Event replay for missed events**
   - What we know: If an EVENT activity is activated AFTER a matching event already fired, it will wait forever
   - What's unclear: Whether to scan historical events when an EVENT activity activates
   - Recommendation: Skip for v1 (EVTACT-05 is deferred). Document the constraint that events must fire after the EVENT activity is active.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/app/services/event_bus.py` -- EventBus implementation
- Codebase inspection: `src/app/services/event_handlers.py` -- existing handler patterns (sub-workflow resume)
- Codebase inspection: `src/app/services/engine_service.py` lines 593-636 -- activity type dispatch
- Codebase inspection: `src/app/models/enums.py` -- ActivityType enum
- Codebase inspection: `alembic/versions/phase18_001_sub_workflows.py` -- migration pattern for new activity type
- Codebase inspection: `frontend/src/components/nodes/SubWorkflowNode.tsx` -- node component pattern
- Codebase inspection: `frontend/src/components/designer/PropertiesPanel.tsx` -- activity config pattern

### Secondary (MEDIUM confidence)
- REQUIREMENTS.md -- EVTACT-01 through EVTACT-03 definitions and deferred items

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing infrastructure
- Architecture: HIGH -- follows established patterns from Phase 18 (sub-workflow) exactly
- Pitfalls: HIGH -- patterns are well understood from existing event handler code

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable -- internal codebase patterns)
