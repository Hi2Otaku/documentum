# Phase 3: Workflow Template Design (API) - Research

**Researched:** 2026-03-30
**Domain:** Workflow template CRUD, validation, versioning (FastAPI + SQLAlchemy async)
**Confidence:** HIGH

## Summary

Phase 3 builds the complete API layer for designing workflow templates -- the blueprint objects that the Process Engine (Phase 4) will instantiate and execute. The existing codebase already has skeleton SQLAlchemy models for ProcessTemplate, ActivityTemplate, FlowTemplate, and ProcessVariable from Phase 1, plus well-established patterns for services, routers, schemas, and audit. This phase needs to flesh out those models (add missing relationships, fix the trigger_type column to use a proper enum, add TriggerType to enums.py), build a full CRUD + validation + installation API, and implement copy-on-write versioning.

The primary complexity is in template validation (graph connectivity analysis, performer assignment checks, reachability) and versioning (immutable snapshots on install). The models, schemas, router, service, and test patterns are all well-established from Phases 1 and 2 -- this phase follows those patterns exactly.

**Primary recommendation:** Build separate CRUD endpoints per sub-entity (process templates, activities, flows, variables) rather than a single nested JSON endpoint. This aligns with the Visual Designer (Phase 8) which will need fine-grained operations. Add a dedicated `/validate` and `/install` endpoint on process templates. Use a simple JSON-based expression format for conditional routing (e.g., `{"field": "amount", "operator": ">", "value": 10000}`) that can be safely evaluated without `eval()`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
All implementation decisions are at Claude's discretion. The following prior decisions from Phase 1 are locked constraints:

- Template + Instance split: separate `process_templates` / `activity_templates` tables from runtime instances (D-01)
- Copy-on-write versioning: installing creates frozen snapshot, edits create new version (D-02)
- Flows as junction table: source_activity_id, target_activity_id, flow_type (normal/reject), condition expression (D-03)
- Process variables: typed columns table with name, type, and separate value columns (D-04)
- PostgreSQL ENUMs for activity types (manual/auto), flow types (normal/reject), trigger types (AND/OR) (D-11)
- All standard patterns: UUID PKs, soft deletes, base model, audit on mutations, envelope responses, /api/v1/ prefix, offset pagination

### Claude's Discretion
- Template API shape: single nested JSON for full template creation vs separate CRUD per sub-entity
- Validation rules: connectivity check, orphan detection, performer assignment validation, cycle detection
- Condition expressions: expression format for routing conditions (simple DSL, Python subset, JSON-based)
- Template state machine: Draft -> Validated -> Installed lifecycle

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TMPL-01 | Create workflow template with name and description | ProcessTemplate CRUD -- model exists, needs router/service/schema |
| TMPL-02 | Add Manual Activities with performer assignment config | ActivityTemplate CRUD with performer_type/performer_id fields |
| TMPL-03 | Add Auto Activities with Python method reference | ActivityTemplate with activity_type=AUTO and method_name field |
| TMPL-04 | Connect activities with Normal/Reject flows | FlowTemplate CRUD with flow_type enum |
| TMPL-05 | Define process variables (string, int, boolean, date) | ProcessVariable CRUD with typed value columns |
| TMPL-06 | Configure AND-join/OR-join triggers on activities | TriggerType enum (missing), update ActivityTemplate.trigger_type |
| TMPL-07 | Conditional routing with expressions based on variables | condition_expression on FlowTemplate + expression format design |
| TMPL-08 | Validate template (connectivity, performers, reachability) | Graph validation service with BFS/DFS analysis |
| TMPL-09 | Install (activate) a validated template | State machine transition + immutable version creation |
| TMPL-10 | Versioning -- editing installed template creates new version | Copy-on-write deep clone of template + activities + flows + variables |
| TMPL-11 | Start Activity and End Activity markers | ActivityType enum already has START/END values |
</phase_requirements>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.x | HTTP API framework | Already in use, native async |
| SQLAlchemy | 2.0.x | Async ORM | Already in use, relationship modeling |
| Pydantic | 2.x | Request/response validation | Already in use, FastAPI integration |
| pytest | 8.x | Test framework | Already in use |
| pytest-asyncio | 0.24.x | Async test support | Already in use |
| httpx | 0.28.x | Test HTTP client | Already in use |

### No Additional Libraries Needed

This phase uses only what is already installed. Template validation (graph traversal) is standard BFS/DFS with no external dependency. Expression parsing uses a safe JSON-based format evaluated with simple Python logic -- no expression parser library needed.

## Architecture Patterns

### File Structure (new files for Phase 3)
```
src/app/
  models/
    enums.py          # ADD: TriggerType enum
    workflow.py        # UPDATE: add TriggerType, method_name, relationships, default_value on ProcessVariable
  schemas/
    template.py        # NEW: all Pydantic schemas for template CRUD
  services/
    template_service.py  # NEW: business logic for CRUD, validation, install, versioning
  routers/
    templates.py       # NEW: API endpoints
tests/
  test_templates.py    # NEW: integration tests
```

### Pattern 1: Separate CRUD Per Sub-Entity
**What:** Individual endpoints for process templates, activities, flows, and variables rather than a single nested JSON create.
**When to use:** When downstream consumers (Visual Designer) need fine-grained control.
**Why:** The Visual Designer (Phase 8) will add/remove individual activities and flows interactively. A nested JSON approach forces the client to send the entire template on every small change. Separate endpoints also simplify error handling and partial updates.

**API structure:**
```
POST   /api/v1/templates                        # Create process template
GET    /api/v1/templates                        # List templates (paginated)
GET    /api/v1/templates/{id}                   # Get template with activities, flows, variables
PUT    /api/v1/templates/{id}                   # Update template metadata
DELETE /api/v1/templates/{id}                   # Soft delete template

POST   /api/v1/templates/{id}/activities        # Add activity
PUT    /api/v1/templates/{id}/activities/{aid}  # Update activity
DELETE /api/v1/templates/{id}/activities/{aid}  # Remove activity

POST   /api/v1/templates/{id}/flows             # Add flow
PUT    /api/v1/templates/{id}/flows/{fid}       # Update flow
DELETE /api/v1/templates/{id}/flows/{fid}       # Remove flow

POST   /api/v1/templates/{id}/variables         # Add variable
PUT    /api/v1/templates/{id}/variables/{vid}   # Update variable
DELETE /api/v1/templates/{id}/variables/{vid}   # Remove variable

POST   /api/v1/templates/{id}/validate          # Validate template
POST   /api/v1/templates/{id}/install           # Install (activate) template
```

### Pattern 2: Template State Machine
**What:** ProcessTemplate transitions through Draft -> Validated -> Installed (Active).
**When to use:** Always -- enforces that templates cannot be instantiated without passing validation.

**State transitions:**
```
Draft ----[validate]--> Validated ----[install]--> Active
  ^                        |
  |                        |
  +------[edit]------------+
```

- **Draft:** Template is being designed. All CRUD operations allowed.
- **Validated:** Template passed structural validation. Can be installed. Any edit reverts to Draft.
- **Active (Installed):** Template is frozen. Can be instantiated. Editing creates a new version in Draft state.
- **Deprecated:** (existing in enum) Old versions after a new version is installed.

**Key rule:** Any modification to a Validated template (add/remove activity, change flow, etc.) automatically resets state to Draft. This prevents installing a template that was modified after validation.

### Pattern 3: Copy-on-Write Versioning
**What:** When an installed template is edited, create a complete deep copy (new ProcessTemplate row + all activities + flows + variables) with version incremented.
**When to use:** When `state == Active` and user attempts any edit.

**Implementation approach:**
```python
async def create_new_version(db: AsyncSession, template_id: UUID, user_id: str) -> ProcessTemplate:
    """Deep clone an installed template for editing."""
    original = await get_template_with_relations(db, template_id)

    # Create new template row
    new_template = ProcessTemplate(
        name=original.name,
        description=original.description,
        version=original.version + 1,
        state=ProcessState.DRAFT,
        is_installed=False,
        created_by=user_id,
    )
    db.add(new_template)
    await db.flush()

    # Map old activity IDs to new ones (needed for flow re-linking)
    activity_id_map = {}
    for activity in original.activity_templates:
        new_activity = ActivityTemplate(
            process_template_id=new_template.id,
            name=activity.name,
            activity_type=activity.activity_type,
            # ... all fields ...
        )
        db.add(new_activity)
        await db.flush()
        activity_id_map[activity.id] = new_activity.id

    # Clone flows with remapped activity IDs
    for flow in original.flow_templates:
        new_flow = FlowTemplate(
            process_template_id=new_template.id,
            source_activity_id=activity_id_map[flow.source_activity_id],
            target_activity_id=activity_id_map[flow.target_activity_id],
            flow_type=flow.flow_type,
            condition_expression=flow.condition_expression,
        )
        db.add(new_flow)

    # Clone variables
    for var in original.process_variables:
        new_var = ProcessVariable(
            process_template_id=new_template.id,
            name=var.name,
            variable_type=var.variable_type,
            string_value=var.string_value,
            # ... all typed value columns ...
        )
        db.add(new_var)

    return new_template
```

### Pattern 4: JSON-Based Condition Expressions
**What:** Routing conditions stored as structured JSON, not free-form strings.
**Why:** Safe evaluation without `eval()`. Easy validation. Serializable. The Visual Designer can render a form for it.

**Format:**
```json
{
  "field": "contract_amount",
  "operator": ">",
  "value": 10000
}
```

**Compound conditions:**
```json
{
  "all": [
    {"field": "contract_amount", "operator": ">", "value": 10000},
    {"field": "department", "operator": "==", "value": "legal"}
  ]
}
```

**Supported operators:** `==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not_in`, `is_null`, `is_not_null`
**Compound:** `all` (AND), `any` (OR)

**Evaluator (for Phase 4, but design the format now):**
```python
def evaluate_condition(expression: dict, variables: dict[str, Any]) -> bool:
    if "all" in expression:
        return all(evaluate_condition(c, variables) for c in expression["all"])
    if "any" in expression:
        return any(evaluate_condition(c, variables) for c in expression["any"])

    field = expression["field"]
    op = expression["operator"]
    value = expression["value"]
    actual = variables.get(field)

    ops = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "in": lambda a, b: a in b,
        "not_in": lambda a, b: a not in b,
        "is_null": lambda a, b: a is None,
        "is_not_null": lambda a, b: a is not None,
    }
    return ops[op](actual, value)
```

### Pattern 5: Graph Validation
**What:** Structural validation of the workflow template before installation.
**Checks to implement:**

1. **Exactly one Start activity** -- template must have exactly one activity with type=START
2. **At least one End activity** -- template must have at least one activity with type=END
3. **Connectivity** -- all activities must be reachable from Start via BFS/DFS
4. **No orphan activities** -- every non-Start activity must have at least one incoming flow; every non-End activity must have at least one outgoing flow
5. **Performer assignment** -- every Manual activity must have performer_type set
6. **Method reference** -- every Auto activity must have a method_name set
7. **Flow endpoint validity** -- all flow source/target IDs must reference activities within this template
8. **No self-loops** -- a flow cannot have source == target
9. **Condition expression validity** -- if a flow has a condition_expression, validate its JSON structure
10. **Variable reference check** -- condition expressions should reference variables that exist on the template

**Return format:** List of validation errors, not just pass/fail. Each error has a code, message, and reference to the offending entity.

```python
@dataclass
class ValidationError:
    code: str           # e.g., "NO_START_ACTIVITY", "ORPHAN_ACTIVITY"
    message: str        # Human-readable description
    entity_type: str    # "activity", "flow", "template"
    entity_id: str | None  # UUID of the offending entity
```

### Anti-Patterns to Avoid
- **In-place template modification after install:** Never UPDATE an installed template's activities/flows. Always create a new version.
- **eval() for condition expressions:** Security vulnerability. Use the structured JSON format above.
- **Single nested JSON create:** While simpler initially, forces full-template round-trips from the Visual Designer. Separate CRUD per sub-entity is better.
- **Validation as a side effect of install:** Validation should be a separate explicit step that returns detailed errors. Install should just check `state == Validated`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID generation | Custom ID schemes | `uuid.uuid4()` via BaseModel | Already standardized in the project |
| Pagination | Custom offset logic | EnvelopeResponse + PaginationMeta pattern | Already established in Phase 1/2 |
| Audit trail | Custom logging | `create_audit_record()` from audit_service | Already established, same transaction pattern |
| Auth dependencies | Custom auth checks | `get_current_user` / `get_current_active_admin` | Already established |
| Soft deletes | Custom deletion logic | `is_deleted` flag on BaseModel | Already standardized |

**Key insight:** Nearly all infrastructure patterns are already established. Phase 3 should focus on domain logic (validation, versioning) and follow existing patterns for everything else.

## Common Pitfalls

### Pitfall 1: Forgetting to Reset State on Edit
**What goes wrong:** User validates a template, then adds an activity, but the template state stays "Validated." User installs the invalid template.
**Why it happens:** CRUD operations on sub-entities (activities, flows) don't check or update the parent template's state.
**How to avoid:** Every mutation on activities, flows, or variables must check if the parent template is in Validated state and reset it to Draft. Implement this as a service-layer helper called after every sub-entity mutation.
**Warning signs:** Templates in Validated state that fail validation when re-checked.

### Pitfall 2: Orphan Detection Misses Disconnected Subgraphs
**What goes wrong:** Validation checks that every activity has incoming/outgoing flows, but misses a cluster of activities that form a disconnected subgraph (connected to each other but not to Start/End).
**Why it happens:** Only checking local connectivity (has incoming flow) instead of global reachability (reachable from Start).
**How to avoid:** Use BFS from Start activity. Any activity not visited is unreachable. This catches both isolated nodes AND disconnected subgraphs.
**Warning signs:** Workflow instances that complete without executing all expected activities.

### Pitfall 3: Flow Remapping During Version Clone
**What goes wrong:** When cloning a template for a new version, flows reference old activity IDs instead of the cloned activity IDs. The new version's flows point to activities in the old version.
**Why it happens:** Copying flow rows without remapping source_activity_id and target_activity_id to the new activity UUIDs.
**How to avoid:** Build an `old_id -> new_id` mapping during activity cloning, then use it when cloning flows. This is shown in the Pattern 3 code example above.
**Warning signs:** Foreign key violations or flows that appear to connect to activities in a different template version.

### Pitfall 4: Missing selectinload for Async Relationships
**What goes wrong:** Accessing `template.activity_templates` raises `MissingGreenlet` error because SQLAlchemy async does not support lazy loading.
**Why it happens:** Default relationship loading is "lazy" which requires synchronous DB access.
**How to avoid:** Always use `selectinload()` (or `joinedload()`) when querying templates that need their relationships. This was already solved in Phase 1 for user groups/roles.
**Warning signs:** `MissingGreenlet` or `greenlet_spawn has not been called` errors.

### Pitfall 5: TriggerType Still a String Column
**What goes wrong:** ActivityTemplate.trigger_type is currently `String(20)` with a default of "or_join". Decision D-11 requires PostgreSQL ENUMs for trigger types.
**Why it happens:** Phase 1 created skeleton models without the TriggerType enum.
**How to avoid:** Add `TriggerType` enum to `enums.py` and update `ActivityTemplate.trigger_type` to use `Enum(TriggerType)`. Note: SQLite (used in tests) does not enforce CHECK constraints from SA enums, so validation must also happen at the Pydantic schema level.
**Warning signs:** Invalid trigger_type values accepted without error.

## Code Examples

### Schema Pattern (following established project style)
```python
# src/app/schemas/template.py
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActivityType, FlowType, ProcessState, TriggerType


class ProcessTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProcessTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None


class ProcessTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    version: int
    state: ProcessState
    is_installed: bool
    installed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


class ActivityTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    activity_type: ActivityType
    description: str | None = None
    performer_type: str | None = None  # Required for MANUAL
    performer_id: str | None = None
    trigger_type: TriggerType = TriggerType.OR_JOIN
    method_name: str | None = None  # Required for AUTO
    position_x: float | None = None
    position_y: float | None = None


class FlowTemplateCreate(BaseModel):
    source_activity_id: uuid.UUID
    target_activity_id: uuid.UUID
    flow_type: FlowType = FlowType.NORMAL
    condition_expression: dict[str, Any] | None = None


class ProcessVariableCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    variable_type: str = Field(pattern=r"^(string|int|boolean|date)$")
    default_string_value: str | None = None
    default_int_value: int | None = None
    default_bool_value: bool | None = None
    default_date_value: datetime | None = None


class ValidationErrorResponse(BaseModel):
    code: str
    message: str
    entity_type: str
    entity_id: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationErrorResponse] = []
```

### Service Pattern (following established project style)
```python
# src/app/services/template_service.py
async def create_template(
    db: AsyncSession, data: ProcessTemplateCreate, user_id: str
) -> ProcessTemplate:
    template = ProcessTemplate(
        name=data.name,
        description=data.description,
        created_by=user_id,
    )
    db.add(template)
    await db.flush()

    await create_audit_record(
        db,
        entity_type="process_template",
        entity_id=str(template.id),
        action="create",
        user_id=user_id,
        after_state={"name": data.name, "description": data.description},
    )
    return template
```

### Router Pattern (following established project style)
```python
# src/app/routers/templates.py
router = APIRouter(prefix="/templates", tags=["templates"])

@router.post(
    "/",
    response_model=EnvelopeResponse[ProcessTemplateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: ProcessTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = await template_service.create_template(
        db, data, str(current_user.id)
    )
    return EnvelopeResponse(data=ProcessTemplateResponse.model_validate(template))
```

### Validation Service (graph analysis)
```python
async def validate_template(db: AsyncSession, template_id: UUID) -> ValidationResult:
    template = await get_template_with_relations(db, template_id)
    errors = []

    activities = [a for a in template.activity_templates if not a.is_deleted]
    flows = [f for f in template.flow_templates if not f.is_deleted]

    # Check exactly one start
    starts = [a for a in activities if a.activity_type == ActivityType.START]
    if len(starts) != 1:
        errors.append(ValidationError(
            code="INVALID_START_COUNT",
            message=f"Expected exactly 1 start activity, found {len(starts)}",
            entity_type="template",
            entity_id=str(template_id),
        ))

    # Check at least one end
    ends = [a for a in activities if a.activity_type == ActivityType.END]
    if len(ends) < 1:
        errors.append(ValidationError(
            code="NO_END_ACTIVITY",
            message="Template must have at least one end activity",
            entity_type="template",
            entity_id=str(template_id),
        ))

    # BFS reachability from start
    if starts:
        reachable = set()
        adjacency = {}
        for flow in flows:
            adjacency.setdefault(flow.source_activity_id, []).append(flow.target_activity_id)

        queue = [starts[0].id]
        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            for neighbor in adjacency.get(current, []):
                if neighbor not in reachable:
                    queue.append(neighbor)

        for activity in activities:
            if activity.id not in reachable:
                errors.append(ValidationError(
                    code="UNREACHABLE_ACTIVITY",
                    message=f"Activity '{activity.name}' is not reachable from start",
                    entity_type="activity",
                    entity_id=str(activity.id),
                ))

    # Performer assignment check for manual activities
    for activity in activities:
        if activity.activity_type == ActivityType.MANUAL and not activity.performer_type:
            errors.append(ValidationError(
                code="MISSING_PERFORMER",
                message=f"Manual activity '{activity.name}' has no performer assigned",
                entity_type="activity",
                entity_id=str(activity.id),
            ))

    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

## Model Updates Required

### Existing Model Gaps

The Phase 1 skeleton models need these updates:

1. **Add TriggerType enum** to `enums.py`:
```python
class TriggerType(str, enum.Enum):
    AND_JOIN = "and_join"
    OR_JOIN = "or_join"
```

2. **Update ActivityTemplate.trigger_type** from `String(20)` to `Enum(TriggerType)`:
```python
trigger_type: Mapped[TriggerType] = mapped_column(
    Enum(TriggerType, name="triggertype"),
    default=TriggerType.OR_JOIN,
    nullable=False,
)
```

3. **Add method_name to ActivityTemplate** for auto activities:
```python
method_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

4. **Add relationships to ProcessTemplate** for flows and variables:
```python
flow_templates: Mapped[list["FlowTemplate"]] = relationship(back_populates="process_template")
process_variables: Mapped[list["ProcessVariable"]] = relationship(back_populates="process_template")
```

5. **Add back_populates to FlowTemplate and ProcessVariable**:
```python
# FlowTemplate
process_template: Mapped["ProcessTemplate"] = relationship(back_populates="flow_templates")

# ProcessVariable
process_template: Mapped["ProcessTemplate"] = relationship(back_populates="process_variables")
```

6. **Add default_value columns to ProcessVariable** (or reuse existing value columns as defaults at the template level).

7. **Update models/__init__.py** to export TriggerType.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| eval() for expressions | Structured JSON conditions | Always was bad practice | Security: no arbitrary code execution |
| Single nested template JSON | Separate CRUD per sub-entity | Common in modern BPM APIs | Better for interactive designers |
| In-place template updates | Copy-on-write versioning | D-02 locked decision | Running instances never disrupted |

## Open Questions

1. **Should the `install` endpoint also validate, or require prior validation?**
   - What we know: The state machine has a Validated step between Draft and Active.
   - What's unclear: Whether install should implicitly run validation or strictly require `state == Validated`.
   - Recommendation: Install should verify `state == Validated` and reject otherwise. This makes the two-step flow explicit and avoids hiding validation results.

2. **Should auto-activity method_name be validated against a registry?**
   - What we know: Auto activities reference Python methods (dm_method equivalent). Phase 9 implements the actual execution.
   - What's unclear: Whether Phase 3 should validate method names exist.
   - Recommendation: Store method_name as a string. Do NOT validate against a registry in Phase 3 -- the registry does not exist yet. Phase 9 will handle method resolution. Template validation should only check that method_name is non-empty for AUTO activities.

3. **Should condition_expression be stored as JSON or Text?**
   - What we know: The existing FlowTemplate.condition_expression is `Text`. We want structured JSON.
   - Recommendation: Keep the column as `Text` in the database (SQLite test compatibility), but serialize/deserialize JSON in the service layer. Pydantic schemas accept `dict` and the service converts to/from JSON string for storage.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `tests/conftest.py` (existing) |
| Quick run command | `python -m pytest tests/test_templates.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TMPL-01 | Create template with name/description | integration | `pytest tests/test_templates.py::test_create_template -x` | Wave 0 |
| TMPL-02 | Add manual activity with performer config | integration | `pytest tests/test_templates.py::test_add_manual_activity -x` | Wave 0 |
| TMPL-03 | Add auto activity with method reference | integration | `pytest tests/test_templates.py::test_add_auto_activity -x` | Wave 0 |
| TMPL-04 | Connect activities with normal/reject flows | integration | `pytest tests/test_templates.py::test_add_flows -x` | Wave 0 |
| TMPL-05 | Define process variables (4 types) | integration | `pytest tests/test_templates.py::test_add_variables -x` | Wave 0 |
| TMPL-06 | Configure AND/OR join triggers | integration | `pytest tests/test_templates.py::test_trigger_types -x` | Wave 0 |
| TMPL-07 | Conditional routing expressions | integration | `pytest tests/test_templates.py::test_condition_expressions -x` | Wave 0 |
| TMPL-08 | Validate template (structural checks) | integration | `pytest tests/test_templates.py::test_validate_template -x` | Wave 0 |
| TMPL-09 | Install validated template | integration | `pytest tests/test_templates.py::test_install_template -x` | Wave 0 |
| TMPL-10 | Versioning: edit creates new version | integration | `pytest tests/test_templates.py::test_versioning -x` | Wave 0 |
| TMPL-11 | Start/End activity markers | integration | `pytest tests/test_templates.py::test_start_end_activities -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_templates.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] `tests/test_templates.py` -- covers TMPL-01 through TMPL-11
- [ ] Test helper: function to create a complete valid template (start + activities + flows + end) for reuse across tests

## Sources

### Primary (HIGH confidence)
- Existing codebase (`src/app/`) -- all patterns derived from Phase 1/2 implementation
- `.planning/phases/01-foundation-user-management/01-CONTEXT.md` -- locked data model decisions D-01 through D-20
- `.planning/research/PITFALLS.md` -- Pitfall 3 (template versioning) directly applies
- `.planning/research/ARCHITECTURE.md` -- Process Definition Service component

### Secondary (MEDIUM confidence)
- Documentum dm_process/dm_activity conceptual model (training data knowledge, consistent with project requirements)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in the project, no new dependencies
- Architecture: HIGH -- patterns well-established in Phases 1/2, decisions locked in CONTEXT.md
- Pitfalls: HIGH -- versioning pitfall from PITFALLS.md, graph validation is well-understood domain
- Validation logic: HIGH -- BFS/DFS connectivity checks are standard graph algorithms

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable domain, no moving parts)
