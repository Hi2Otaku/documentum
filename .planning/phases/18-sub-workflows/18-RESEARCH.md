# Phase 18: Sub-Workflows - Research

**Researched:** 2026-04-06
**Domain:** Workflow engine sub-process orchestration, parent-child lifecycle management
**Confidence:** HIGH

## Summary

Phase 18 adds a new `SUB_WORKFLOW` activity type to the workflow engine. When execution reaches a SUB_WORKFLOW activity, the engine spawns a child workflow instance from a referenced template, maps variables from parent to child, and pauses the parent activity until the child completes. Completion is detected via the existing event bus (`workflow.completed` event) which triggers parent resumption. A depth limit enforced at template installation time prevents infinite recursion.

The existing codebase is well-structured for this extension. The `_advance_from_activity` loop in `engine_service.py` already dispatches by `ActivityType` (START/END auto-complete, AUTO leaves active for Celery, MANUAL creates work items). Adding a `SUB_WORKFLOW` branch follows the same pattern. The event bus (`event_bus.py`) already emits `workflow.completed` events. The `ActivityTemplate` model stores configuration in existing columns (`method_name` can be repurposed or a new column added for `sub_template_id`). The frontend designer already supports a palette of draggable node types and a properties panel that conditionally renders fields per activity type.

**Primary recommendation:** Add `SUB_WORKFLOW` to the `ActivityType` enum, add `sub_template_id` and `variable_mapping` columns to `ActivityTemplate`, add `parent_workflow_id`/`parent_activity_instance_id`/`nesting_depth` columns to `WorkflowInstance`, register a `workflow.completed` event handler that resumes the parent, enforce depth limits at template install, and add a new `SubWorkflowNode` to the frontend designer.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None -- discuss phase was skipped per user setting. All implementation choices are at Claude's discretion.

### Claude's Discretion
All implementation choices are at Claude's discretion -- discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
None -- discuss phase skipped.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SUBWF-01 | Admin can add a SUB_WORKFLOW activity type in the workflow designer that references another template | New ActivityType enum value, new ActivityTemplate columns (`sub_template_id`, `variable_mapping`), new SubWorkflowNode component in frontend, NodePalette entry |
| SUBWF-02 | When a SUB_WORKFLOW activity executes, a child workflow instance is spawned from the referenced template | New branch in `_advance_from_activity` for SUB_WORKFLOW type that calls `start_workflow` with parent linkage |
| SUBWF-03 | Parent workflow pauses at the SUB_WORKFLOW activity until the child workflow completes | SUB_WORKFLOW activity stays ACTIVE (like AUTO), event handler on `workflow.completed` resumes parent |
| SUBWF-04 | Variables can be mapped from parent to child workflow on spawn | `variable_mapping` JSON column on ActivityTemplate, engine reads mapping and passes as `initial_variables` to child `start_workflow` |
| SUBWF-05 | System enforces depth limits to prevent recursive sub-workflow chains | Validation at template install time (BFS/DFS through sub_template_id references), runtime depth check via `nesting_depth` on WorkflowInstance |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech stack**: FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL (async via asyncpg), Celery + Redis
- **Frontend**: React 19 + TypeScript + Vite + React Flow (@xyflow/react) + shadcn/ui + Tailwind
- **Testing**: pytest + pytest-asyncio + httpx (SQLite in-memory for tests)
- **Linting**: Ruff
- **Type checking**: mypy
- **GSD Workflow**: Must use GSD commands for file changes

## Standard Stack

No new libraries needed. This phase extends existing models, services, and frontend components using the established stack.

### Core (existing, no additions)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.48 | ORM for new columns and queries | Already used throughout |
| Alembic | 1.18.x | Migration for new columns | Standard migration tool |
| FastAPI | 0.135.x | API endpoints | Existing API layer |
| @xyflow/react | 12.10.x | New SubWorkflowNode in designer | Already used for workflow designer |

## Architecture Patterns

### Database Schema Changes

**ActivityTemplate additions:**
```python
# New columns on activity_templates table
sub_template_id: Mapped[uuid.UUID | None] = mapped_column(
    Uuid(), ForeignKey("process_templates.id"), nullable=True
)
variable_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)
# variable_mapping format: {"parent_var_name": "child_var_name", ...}
```

**WorkflowInstance additions:**
```python
# New columns on workflow_instances table
parent_workflow_id: Mapped[uuid.UUID | None] = mapped_column(
    Uuid(), ForeignKey("workflow_instances.id"), nullable=True
)
parent_activity_instance_id: Mapped[uuid.UUID | None] = mapped_column(
    Uuid(), ForeignKey("activity_instances.id"), nullable=True
)
nesting_depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
```

**ActivityType enum addition:**
```python
class ActivityType(str, enum.Enum):
    START = "start"
    END = "end"
    MANUAL = "manual"
    AUTO = "auto"
    SUB_WORKFLOW = "sub_workflow"  # NEW
```

### Pattern 1: SUB_WORKFLOW Dispatch in Engine Advancement Loop
**What:** When `_advance_from_activity` encounters a SUB_WORKFLOW activity, it spawns a child workflow and leaves the parent activity in ACTIVE state (similar to AUTO activities).
**When to use:** Every time a token activates a SUB_WORKFLOW activity.

```python
# In _advance_from_activity, after the existing AUTO and MANUAL branches:
elif target_at.activity_type == ActivityType.SUB_WORKFLOW:
    # 1. Resolve variable mapping
    variable_mapping = target_at.variable_mapping or {}
    child_initial_vars = {}
    for parent_var, child_var in variable_mapping.items():
        parent_val = var_context.get(parent_var)
        if parent_val is not None:
            child_initial_vars[child_var] = parent_val

    # 2. Check depth limit
    current_depth = getattr(workflow, 'nesting_depth', 0)
    MAX_DEPTH = 5  # configurable
    if current_depth >= MAX_DEPTH:
        target_ai.state = ActivityState.ERROR
        logger.error("Sub-workflow depth limit exceeded at depth %d", current_depth)
        continue

    # 3. Spawn child workflow
    child = await start_workflow(
        db,
        target_at.sub_template_id,
        user_id,
        initial_variables=child_initial_vars,
    )
    child.parent_workflow_id = workflow.id
    child.parent_activity_instance_id = target_ai.id
    child.nesting_depth = current_depth + 1
    # Parent activity stays ACTIVE -- will be resumed by event handler
```

### Pattern 2: Event-Driven Parent Resumption
**What:** An event handler on `workflow.completed` checks if the completed workflow has a parent, and if so, resumes the parent by advancing from the paused SUB_WORKFLOW activity.
**When to use:** Every time any workflow completes.

```python
@event_bus.on("workflow.completed")
async def _resume_parent_on_child_complete(db: AsyncSession, event: DomainEvent) -> None:
    """When a child workflow completes, resume its parent."""
    child_id = event.entity_id
    if child_id is None:
        return

    # Load child to check for parent linkage
    child = await db.execute(
        select(WorkflowInstance).where(WorkflowInstance.id == child_id)
    )
    child_wf = child.scalar_one_or_none()
    if child_wf is None or child_wf.parent_workflow_id is None:
        return  # Not a sub-workflow, nothing to do

    # Load parent activity instance
    parent_ai = await db.get(ActivityInstance, child_wf.parent_activity_instance_id)
    if parent_ai is None or parent_ai.state != ActivityState.ACTIVE:
        return  # Already completed or errored

    # Load parent workflow and advance
    parent_wf = await db.execute(
        select(WorkflowInstance).where(WorkflowInstance.id == child_wf.parent_workflow_id)
    )
    parent_workflow = parent_wf.scalar_one_or_none()
    if parent_workflow is None or parent_workflow.state != WorkflowState.RUNNING:
        return

    # Advance parent from the SUB_WORKFLOW activity
    # (load template, rebuild mappings, call _advance_from_activity)
```

### Pattern 3: Depth Limit Enforcement at Template Installation
**What:** During template validation/installation, traverse `sub_template_id` references to detect cycles and enforce maximum depth.
**When to use:** When `install_template` is called.

```python
async def _check_sub_workflow_depth(
    db: AsyncSession, template_id: UUID, visited: set[UUID] | None = None, depth: int = 0
) -> tuple[bool, str | None]:
    """BFS/DFS check for sub-workflow cycles and depth limits."""
    MAX_DEPTH = 5
    if depth > MAX_DEPTH:
        return False, f"Sub-workflow nesting exceeds depth limit of {MAX_DEPTH}"

    if visited is None:
        visited = set()
    if template_id in visited:
        return False, "Circular sub-workflow reference detected"
    visited.add(template_id)

    # Find all SUB_WORKFLOW activities in this template
    result = await db.execute(
        select(ActivityTemplate).where(
            ActivityTemplate.process_template_id == template_id,
            ActivityTemplate.activity_type == ActivityType.SUB_WORKFLOW,
            ActivityTemplate.is_deleted == False,
        )
    )
    sub_activities = result.scalars().all()

    for sa in sub_activities:
        if sa.sub_template_id:
            ok, msg = await _check_sub_workflow_depth(
                db, sa.sub_template_id, visited.copy(), depth + 1
            )
            if not ok:
                return False, msg

    return True, None
```

### Pattern 4: Frontend SubWorkflowNode
**What:** A new React Flow node component for the SUB_WORKFLOW activity type, with a properties panel section for selecting the referenced template and configuring variable mappings.
**When to use:** In the workflow designer canvas.

The node should:
- Have a distinct visual style (e.g., double-bordered rectangle or nested-workflow icon)
- Show the referenced template name
- Be added to `NodePalette` as a new draggable item
- Have a properties panel section with a template selector dropdown (fetching installed templates) and a variable mapping editor

### Recommended File Changes
```
src/
  app/
    models/
      enums.py              # Add SUB_WORKFLOW to ActivityType
      workflow.py            # Add sub_template_id, variable_mapping to ActivityTemplate
                            # Add parent_workflow_id, parent_activity_instance_id, nesting_depth to WorkflowInstance
    schemas/
      template.py           # Add sub_template_id, variable_mapping to Create/Update/Response schemas
      workflow.py            # Add parent_workflow_id, nesting_depth to WorkflowInstanceResponse
    services/
      engine_service.py     # SUB_WORKFLOW branch in _advance_from_activity
      template_service.py   # Depth check in validate_template and install_template
      event_handlers.py     # workflow.completed handler for parent resumption
    routers/
      templates.py          # No changes expected (generic CRUD)
    tasks/
      auto_activity.py      # Update poll query to exclude SUB_WORKFLOW (they are not auto activities)
  alembic/
    versions/
      phase18_001_sub_workflows.py  # Migration for new columns and enum value

frontend/
  src/
    types/
      workflow.ts           # Add 'sub_workflow' to ActivityType union
      designer.ts           # Add subTemplateId, variableMapping to ActivityNodeData
    components/
      nodes/
        SubWorkflowNode.tsx # NEW: Visual node for sub-workflow activities
        index.ts            # Register SubWorkflowNode
      designer/
        NodePalette.tsx     # Add sub_workflow palette item
        PropertiesPanel.tsx # Add sub-workflow config section (template selector, variable mapping)
    stores/
      designerStore.ts      # Add subWorkflowNode to DEFAULT_NODE_DATA
    api/
      templates.ts          # May need endpoint for listing installed templates for selector
```

### Anti-Patterns to Avoid
- **Recursive function calls for advancement:** The engine uses an iterative queue-based loop (`_advance_from_activity`). Do NOT make recursive calls. The child workflow is started as a separate `start_workflow` call, which has its own advancement loop.
- **Polling for child completion:** Do NOT add a Celery beat task to poll for child workflow completion. Use the event bus (`workflow.completed`) for immediate, event-driven resumption.
- **Storing parent reference only in payload:** Parent-child linkage must be in dedicated database columns (not just event payload), so queries for "find all child workflows of X" are efficient and reliable.
- **Modifying WorkflowState for pause:** Do NOT change the parent workflow's state to HALTED. The parent remains RUNNING; only the SUB_WORKFLOW activity instance stays ACTIVE until the child completes. This matches how AUTO activities work.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Child completion detection | Custom polling task | Event bus `workflow.completed` handler | Already emitted in `complete_work_item` when workflow finishes; zero latency |
| Template cycle detection | Ad-hoc string matching | Graph traversal (BFS/DFS) on `sub_template_id` references | Must detect transitive cycles (A->B->C->A) not just direct self-references |
| Variable mapping UI | Custom form builder | Simple key-value pair editor | Parent and child template variables are known at design time; a mapping table suffices |

## Common Pitfalls

### Pitfall 1: Enum Migration on PostgreSQL
**What goes wrong:** Adding a new value to a PostgreSQL enum type requires `ALTER TYPE ... ADD VALUE`, not a standard column alter. Alembic does not auto-generate this.
**Why it happens:** PostgreSQL enums are separate types, not just column constraints.
**How to avoid:** Use `op.execute("ALTER TYPE activitytype ADD VALUE IF NOT EXISTS 'sub_workflow'")` in the Alembic migration. Must be outside a transaction block on PostgreSQL (use `autocommit` connection or `op.execute` with `execution_options`).
**Warning signs:** Migration fails with "cannot add enum value within transaction."

### Pitfall 2: Child Workflow Fails or Errors
**What goes wrong:** If the child workflow enters FAILED state, the parent SUB_WORKFLOW activity stays ACTIVE forever with no way to recover.
**Why it happens:** Only `workflow.completed` is handled; `workflow.failed` is not.
**How to avoid:** Also handle the child failure case. Options: (a) mark parent SUB_WORKFLOW activity as ERROR, (b) emit a notification to the supervisor. Per STATE.md blocker note: "Sub-workflow failure propagation semantics (auto-fail vs allow retry) -- product decision." Recommendation: mark parent activity as ERROR on child failure, allowing retry via existing retry mechanism.
**Warning signs:** Parent workflow stuck with an ACTIVE SUB_WORKFLOW activity that never completes.

### Pitfall 3: Event Handler Transaction Scope
**What goes wrong:** The `workflow.completed` event handler runs within the same database session/transaction as the `complete_work_item` call. If the parent resumption advancement loop fails, it could roll back the child completion.
**Why it happens:** The event bus dispatches handlers synchronously in the same session.
**How to avoid:** Keep the event handler lightweight -- just load parent, mark activity complete, and call `_advance_from_activity`. If there is concern about transaction scope, the handler can dispatch a Celery task for async resumption. However, the existing pattern (used by notification handlers) works in-process, and the advancement loop is designed to be safe within a transaction.
**Warning signs:** Child workflow completion rolls back when parent advancement hits an error.

### Pitfall 4: Auto Activity Poller Picks Up SUB_WORKFLOW Activities
**What goes wrong:** The `poll_auto_activities` task queries for `ActivityState.ACTIVE` + `ActivityType.AUTO`. If the query is not properly filtered, it might try to execute SUB_WORKFLOW activities as auto methods.
**Why it happens:** SUB_WORKFLOW activities are also in ACTIVE state while waiting for the child.
**How to avoid:** The existing poller already filters by `ActivityType.AUTO`, so this should be safe. But verify the query explicitly excludes SUB_WORKFLOW. The query joins `ActivityTemplate` and filters `activity_type == ActivityType.AUTO`, which naturally excludes SUB_WORKFLOW.
**Warning signs:** Error logs showing "Auto method 'None' not registered" for SUB_WORKFLOW activities.

### Pitfall 5: SQLite Enum Handling in Tests
**What goes wrong:** SQLite does not support native enums. Adding a new enum value works on PostgreSQL but tests use SQLite (in-memory).
**Why it happens:** SQLAlchemy's `Enum` type on SQLite stores values as strings, so the new enum value "just works" without migration. But the migration script's `ALTER TYPE` command will fail on SQLite.
**How to avoid:** Guard the `ALTER TYPE` in the migration with a dialect check: `if op.get_bind().dialect.name != 'sqlite'`.
**Warning signs:** Tests crash on migration step.

### Pitfall 6: Depth Limit Off-By-One
**What goes wrong:** Depth limit check at runtime allows one more level than intended, or blocks one level too early.
**Why it happens:** Confusion about whether depth 0 means "top-level" or "first nesting."
**How to avoid:** Convention: top-level workflows have `nesting_depth=0`. A child of a top-level has `nesting_depth=1`. Depth limit of 5 means max chain is: top -> child(1) -> child(2) -> child(3) -> child(4) -> child(5). Check `current_depth + 1 > MAX_DEPTH` before spawning.
**Warning signs:** Tests with depth=MAX_DEPTH succeed when they should fail, or fail when they should succeed.

## Code Examples

### Alembic Migration for New Enum Value and Columns
```python
"""Phase 18: sub-workflow support.

Revision ID: phase18_001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    # Add SUB_WORKFLOW to ActivityType enum (PostgreSQL only)
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("ALTER TYPE activitytype ADD VALUE IF NOT EXISTS 'sub_workflow'")

    # Add sub-workflow columns to activity_templates
    op.add_column("activity_templates", sa.Column("sub_template_id", sa.Uuid(), nullable=True))
    op.add_column("activity_templates", sa.Column("variable_mapping", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_activity_templates_sub_template_id",
        "activity_templates", "process_templates",
        ["sub_template_id"], ["id"],
    )

    # Add parent linkage columns to workflow_instances
    op.add_column("workflow_instances", sa.Column("parent_workflow_id", sa.Uuid(), nullable=True))
    op.add_column("workflow_instances", sa.Column("parent_activity_instance_id", sa.Uuid(), nullable=True))
    op.add_column("workflow_instances", sa.Column("nesting_depth", sa.Integer(), server_default="0", nullable=False))
    op.create_foreign_key(
        "fk_workflow_instances_parent",
        "workflow_instances", "workflow_instances",
        ["parent_workflow_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_workflow_instances_parent_activity",
        "workflow_instances", "activity_instances",
        ["parent_activity_instance_id"], ["id"],
    )

def downgrade() -> None:
    op.drop_constraint("fk_workflow_instances_parent_activity", "workflow_instances", type_="foreignkey")
    op.drop_constraint("fk_workflow_instances_parent", "workflow_instances", type_="foreignkey")
    op.drop_column("workflow_instances", "nesting_depth")
    op.drop_column("workflow_instances", "parent_activity_instance_id")
    op.drop_column("workflow_instances", "parent_workflow_id")
    op.drop_constraint("fk_activity_templates_sub_template_id", "activity_templates", type_="foreignkey")
    op.drop_column("activity_templates", "variable_mapping")
    op.drop_column("activity_templates", "sub_template_id")
```

### Template Validation Extension
```python
# In validate_template, add after MISSING_METHOD check:

# 9. MISSING_SUB_TEMPLATE: Every SUB_WORKFLOW activity needs sub_template_id
for a in activities:
    if a.activity_type == ActivityType.SUB_WORKFLOW:
        if not a.sub_template_id:
            errors.append({
                "code": "MISSING_SUB_TEMPLATE",
                "message": f"Sub-workflow activity '{a.name}' requires a sub_template_id",
                "entity_type": "activity_template",
                "entity_id": str(a.id),
            })
```

### Frontend SubWorkflowNode Component
```tsx
// SubWorkflowNode.tsx
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { GitBranch } from 'lucide-react';
import type { ActivityNodeData } from '../../types/designer';

type SubWorkflowNodeType = Node<ActivityNodeData, 'subWorkflowNode'>;

export function SubWorkflowNode({ data, selected }: NodeProps<SubWorkflowNodeType>) {
  return (
    <div className={`min-w-[160px] min-h-[64px] ${selected ? 'ring-2 ring-primary ring-offset-2' : ''}`}>
      <div className="bg-purple-500 border-2 border-purple-600 text-white rounded-lg px-4 py-3 border-double border-4">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4" />
          <div className="font-semibold text-sm truncate">{data.name}</div>
        </div>
        <div className="text-xs opacity-70 truncate">
          {data.subTemplateId ? 'Template linked' : 'No template selected'}
        </div>
      </div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Only 4 activity types (start, end, manual, auto) | Adding sub_workflow as 5th type | Phase 18 | Engine dispatch, designer, schemas all need the new type |
| Flat workflow instances | Parent-child hierarchy with nesting_depth | Phase 18 | Enables composed workflows; queries may need to account for hierarchy |
| No workflow.completed consumption | Event handler resumes parent | Phase 18 | First feature to react to workflow completion events |

## Open Questions

1. **Failure propagation semantics**
   - What we know: STATE.md flags this as a product decision: "auto-fail vs allow retry"
   - What's unclear: Should the parent SUB_WORKFLOW activity go to ERROR state when the child fails, or should it allow manual retry?
   - Recommendation: Mark parent activity as ERROR when child fails. The existing retry mechanism (`workflow_mgmt_service` has error recovery patterns) allows an admin to retry. This is the simplest approach and matches the AUTO activity error pattern. Handle `workflow.failed` event in addition to `workflow.completed`.

2. **MAX_DEPTH constant location**
   - What we know: Depth limit must exist (SUBWF-05). Value not specified.
   - What's unclear: Should it be a settings constant or stored per-template?
   - Recommendation: Use a system-wide constant (default 5) in `app/core/config.py` via pydantic-settings. Simple, sufficient for v1.2. Per-template limits are deferred complexity.

3. **Output variable mapping (child back to parent)**
   - What we know: SUBWF-06 (output mapping) is explicitly deferred to Future Requirements.
   - What's unclear: N/A -- it's out of scope.
   - Recommendation: Only implement input mapping (parent to child) per SUBWF-04. Note in code comments that SUBWF-06 will add output mapping later.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | pyproject.toml (pytest section) |
| Quick run command | `python -m pytest tests/test_sub_workflows.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SUBWF-01 | Create SUB_WORKFLOW activity via API with sub_template_id | integration | `python -m pytest tests/test_sub_workflows.py::test_create_sub_workflow_activity -x` | Wave 0 |
| SUBWF-02 | Starting workflow spawns child when reaching SUB_WORKFLOW activity | integration | `python -m pytest tests/test_sub_workflows.py::test_sub_workflow_spawns_child -x` | Wave 0 |
| SUBWF-03 | Parent pauses at SUB_WORKFLOW, resumes when child completes | integration | `python -m pytest tests/test_sub_workflows.py::test_parent_resumes_on_child_complete -x` | Wave 0 |
| SUBWF-04 | Variable mapping from parent to child at spawn time | integration | `python -m pytest tests/test_sub_workflows.py::test_variable_mapping_parent_to_child -x` | Wave 0 |
| SUBWF-05 | Template install rejects circular/deep sub-workflow chains | integration | `python -m pytest tests/test_sub_workflows.py::test_depth_limit_rejected -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_sub_workflows.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_sub_workflows.py` -- covers SUBWF-01 through SUBWF-05
- [ ] Existing `tests/conftest.py` -- may need a `sub_workflow_template` fixture (installed child template)

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `src/app/services/engine_service.py` -- full advancement loop, activity type dispatch pattern
- Codebase analysis: `src/app/services/template_service.py` -- validation and installation logic
- Codebase analysis: `src/app/services/event_bus.py` -- event emission and handler registration pattern
- Codebase analysis: `src/app/services/event_handlers.py` -- existing handler pattern for notifications
- Codebase analysis: `src/app/models/enums.py` -- current ActivityType enum values
- Codebase analysis: `src/app/models/workflow.py` -- WorkflowInstance and ActivityTemplate schema
- Codebase analysis: `src/app/tasks/auto_activity.py` -- Celery poll task that must not pick up SUB_WORKFLOW
- Codebase analysis: `frontend/src/components/nodes/` -- existing node type pattern
- Codebase analysis: `frontend/src/components/designer/NodePalette.tsx` -- palette item pattern
- Codebase analysis: `frontend/src/types/designer.ts` -- ActivityNodeData interface
- Codebase analysis: `alembic/versions/` -- migration naming and pattern conventions

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` -- blocker note on failure propagation semantics
- `.planning/ROADMAP.md` -- Phase 18 dependencies and success criteria
- `.planning/REQUIREMENTS.md` -- SUBWF-01 through SUBWF-05 definitions, deferred SUBWF-06/07/08

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, all existing patterns
- Architecture: HIGH - clear extension points in engine_service dispatch loop, event bus, and designer
- Pitfalls: HIGH - PostgreSQL enum migration is well-documented; failure propagation is flagged as open question

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable domain, all internal code patterns)
