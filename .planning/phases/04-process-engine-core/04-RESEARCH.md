# Phase 4: Process Engine Core - Research

**Researched:** 2026-03-30
**Domain:** Workflow execution engine (Petri-net style token-based state machine)
**Confidence:** HIGH

## Summary

Phase 4 builds the core process engine that starts workflow instances from installed templates and advances them through sequential and parallel paths. The engine operates synchronously within HTTP request scope (no Celery in this phase), using a Petri-net token model to track parallel execution. The main work is: (1) an Alembic migration to add ActivityState enum and an execution_tokens table, (2) an engine service that instantiates workflows from templates and advances them through flows, (3) a condition expression evaluator using Python's ast module with a whitelist sandbox, (4) Pydantic schemas and a router for workflow lifecycle endpoints, and (5) comprehensive tests for sequential and parallel routing.

The existing codebase provides solid foundations: WorkflowInstance, ActivityInstance, WorkItem, ProcessVariable, and WorkflowPackage models are already defined as skeletons. The engine service needs to flesh out relationships on these models (they currently lack back-references), add the token tracking table, and implement the advancement loop. All patterns (service layer, audit integration, async SQLAlchemy with selectinload, EnvelopeResponse wrapping) are well-established from Phases 1-3.

**Primary recommendation:** Build engine_service.py as a single module with clear internal sections (instantiation, advancement, token management, expression evaluation). Split into separate modules only if it exceeds ~600 lines.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Synchronous advancement -- when a user completes a work item, the same API request evaluates flows and activates next activities. No Celery involvement in Phase 4.
- **D-02:** Token-based parallel tracking (Petri-net style) -- each flow carries a token, AND-join fires when all incoming tokens arrive. Requires a flow_tokens/execution_tokens table.
- **D-03:** Iterative loop for chaining -- after completing an activity, engine loops (evaluate next -> if start/end activity, execute immediately -> repeat) until hitting a manual activity or dead end. No recursion.
- **D-04:** Document attachment is optional at startup -- packages can be attached later.
- **D-05:** Alias resolution deferred to Phase 6 -- Phase 4 uses basic performer_id from template. Start API accepts optional performer overrides as a simple map.
- **D-06:** Immediate start -- POST /workflows creates instance, sets Running, activates start activity, and advances to first real activity, all in one request.
- **D-07:** Full ActivityState enum with enforced transitions -- add ActivityState enum (Dormant, Active, Paused, Complete, Error) with valid transition enforcement. Alembic migration to convert existing string column.
- **D-08:** Auto-finish -- engine detects End activity completion, marks workflow as Finished, records completed_at automatically.
- **D-09:** Model + basic enforcement for halt/resume -- state transitions enforced (can't complete work item on halted workflow), but admin halt/resume endpoints are Phase 10 (MGMT-01/02).
- **D-10:** Simple Python subset for routing conditions -- expressions like `amount > 10000 and department == 'legal'`. Parsed with Python's ast module.
- **D-11:** AST whitelist sandbox -- parse with ast.parse(), walk tree, allow only: comparisons, boolean ops, arithmetic, string literals, variable names. Reject function calls, attribute access, imports.

### Claude's Discretion
- Engine service structure (single engine_service.py vs split into engine + evaluator)
- Token table schema design
- Workflow start endpoint shape and validation
- How process variables are copied from template to instance at startup
- Test strategy and fixture design

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXEC-01 | User can start a workflow instance from an installed template | Engine service instantiation + POST /workflows endpoint |
| EXEC-02 | User attaches documents to the workflow package at startup | WorkflowPackage creation during startup (optional per D-04) |
| EXEC-03 | User assigns performers for aliases at startup | Performer override map in start request (basic, alias resolution deferred to Phase 6 per D-05) |
| EXEC-04 | Workflow instance transitions through states: Dormant -> Running -> Halted -> Failed -> Finished | WorkflowState enum already exists; add transition enforcement in engine service |
| EXEC-05 | Process Engine automatically advances workflow by evaluating flows and activating next activities | Core advancement loop (iterative per D-03) with token evaluation |
| EXEC-06 | Sequential routing: activities execute one after another | Single outgoing flow -> activate target; iterative chaining handles start/end auto-advance |
| EXEC-07 | Parallel routing: AND-split activates multiple simultaneously, AND-join waits for all | Token table tracks flow completion; AND-join checks all incoming tokens before firing |
| EXEC-12 | OR-join trigger: activity starts when any one incoming flow completes | OR-join fires on first token arrival (simpler than AND-join) |
| EXEC-13 | Process variables can be read and written by activities during execution | Variable copy from template at startup; read/write API during work item completion |
| EXEC-14 | Process variables can be used in routing condition expressions | AST-based expression evaluator resolves variable names from instance variables |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.1 | HTTP API framework | Already in use; native async |
| SQLAlchemy | 2.0.48 | ORM | Already in use; async engine with selectinload |
| Pydantic | 2.12.5 | Request/response schemas | Already in use; FastAPI native |
| Alembic | 1.18.x | Database migrations | Already in use; needed for ActivityState enum migration |
| pytest | 8.x | Test framework | Already in use with asyncio_mode="auto" |
| httpx | 0.28.x | Async test client | Already in use for integration tests |
| aiosqlite | latest | SQLite async driver for tests | Already in use; in-memory test DB |

### No New Dependencies
Phase 4 requires zero new packages. The expression evaluator uses Python's stdlib `ast` module. Token tracking uses a new SQLAlchemy model. All infrastructure is already in place.

## Architecture Patterns

### Recommended Project Structure
```
src/app/
  models/
    enums.py           # ADD: ActivityState enum
    workflow.py         # MODIFY: add relationships, ExecutionToken model
  schemas/
    workflow.py         # NEW: WorkflowInstance/WorkItem/Variable request/response schemas
  services/
    engine_service.py   # NEW: core engine (instantiation, advancement, tokens, expressions)
  routers/
    workflows.py        # NEW: workflow lifecycle endpoints
```

### Pattern 1: Engine Advancement Loop (Iterative, per D-03)
**What:** After any activity completion, the engine enters a loop that evaluates outgoing flows, activates target activities, and auto-completes Start/End activities, repeating until only manual activities remain pending.
**When to use:** Every time an activity is completed (including at workflow start).
**Example:**
```python
async def _advance_from_activity(
    db: AsyncSession,
    workflow: WorkflowInstance,
    completed_activity: ActivityInstance,
    user_id: str,
) -> None:
    """Iterative advancement loop. No recursion."""
    queue: list[ActivityInstance] = [completed_activity]

    while queue:
        current = queue.pop(0)
        # 1. Find outgoing NORMAL flows from current activity's template
        outgoing_flows = _get_outgoing_flows(current.activity_template_id, flow_templates)

        for flow in outgoing_flows:
            # 2. Place token on flow
            await _place_token(db, workflow.id, flow, current)

            # 3. Check if target activity should fire
            target = activity_map[flow.target_activity_id]
            if await _should_activate(db, workflow.id, target):
                await _activate_activity(db, workflow, target, user_id)

                # 4. If start/end/auto-complete type, complete immediately and re-queue
                if target.activity_template.activity_type in (ActivityType.START, ActivityType.END):
                    await _complete_activity(db, target)
                    queue.append(target)
```

### Pattern 2: Token-Based Parallel Join (Petri-net, per D-02)
**What:** Each flow traversal deposits a token. AND-join activities check that all incoming flows have tokens before activating. OR-join activities activate on the first token.
**When to use:** Determining whether a target activity should fire.
**Example:**
```python
async def _should_activate(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    target_activity: ActivityInstance,
) -> bool:
    """Check if target activity's trigger condition is met."""
    template = target_activity.activity_template
    incoming_flow_ids = [f.id for f in flow_templates if f.target_activity_id == template.id]

    # Count tokens that arrived for this activity in this workflow
    token_count = await _count_tokens(db, workflow_id, incoming_flow_ids)

    if template.trigger_type == TriggerType.AND_JOIN:
        return token_count >= len(incoming_flow_ids)  # All must arrive
    else:  # OR_JOIN
        return token_count >= 1  # Any one is enough
```

### Pattern 3: AST Whitelist Expression Evaluator (per D-10, D-11)
**What:** Parse condition expressions using ast.parse(), validate the AST tree contains only allowed node types, then evaluate safely.
**When to use:** Evaluating routing condition expressions on flows.
**Example:**
```python
import ast

ALLOWED_NODES = {
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.Not,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    ast.UnaryOp, ast.USub, ast.UAdd,
    ast.Constant, ast.Name, ast.Load,
}

def validate_expression(expr: str) -> None:
    """Raise ValueError if expression uses disallowed constructs."""
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            raise ValueError(f"Disallowed expression node: {type(node).__name__}")

def evaluate_expression(expr: str, variables: dict) -> bool:
    """Evaluate a validated expression against process variables."""
    validate_expression(expr)
    # compile and eval with restricted globals
    code = compile(ast.parse(expr, mode="eval"), "<expr>", "eval")
    return bool(eval(code, {"__builtins__": {}}, variables))
```

### Pattern 4: Workflow Instantiation from Template
**What:** Deep-copy template structure into instance records, maintaining ID mappings.
**When to use:** POST /workflows (start workflow).
**Example:**
```python
async def start_workflow(
    db: AsyncSession,
    template_id: uuid.UUID,
    user_id: str,
    document_ids: list[uuid.UUID] | None = None,
    performer_overrides: dict[str, str] | None = None,
) -> WorkflowInstance:
    # 1. Load installed template with all relations
    template = await _get_installed_template(db, template_id)

    # 2. Create WorkflowInstance
    instance = WorkflowInstance(
        process_template_id=template.id,
        state=WorkflowState.RUNNING,
        started_at=datetime.now(timezone.utc),
        supervisor_id=uuid.UUID(user_id),
        created_by=user_id,
    )
    db.add(instance)
    await db.flush()  # get instance.id

    # 3. Create ActivityInstances (template_id -> instance_id mapping)
    activity_map: dict[uuid.UUID, ActivityInstance] = {}
    for at in template.activity_templates:
        ai = ActivityInstance(
            workflow_instance_id=instance.id,
            activity_template_id=at.id,
            state=ActivityState.DORMANT,
        )
        db.add(ai)
        activity_map[at.id] = ai
    await db.flush()

    # 4. Copy process variables from template defaults
    for pv in template.process_variables:
        instance_var = ProcessVariable(
            workflow_instance_id=instance.id,
            name=pv.name,
            variable_type=pv.variable_type,
            string_value=pv.string_value,
            int_value=pv.int_value,
            bool_value=pv.bool_value,
            date_value=pv.date_value,
        )
        db.add(instance_var)

    # 5. Create workflow packages for attached documents
    if document_ids:
        for doc_id in document_ids:
            pkg = WorkflowPackage(
                workflow_instance_id=instance.id,
                document_id=doc_id,
            )
            db.add(pkg)

    # 6. Find start activity, activate it, and advance
    start_activity = _find_start_activity(activity_map, template.activity_templates)
    await _activate_and_advance(db, instance, start_activity, user_id, template)

    # 7. Audit
    await create_audit_record(db, entity_type="workflow_instance", ...)

    return instance
```

### Anti-Patterns to Avoid
- **Recursive advancement:** D-03 explicitly forbids recursion. Use iterative loop with a queue.
- **Celery/background tasks:** D-01 says synchronous advancement in Phase 4. No task queue.
- **eval() without AST validation:** Never pass user expressions directly to eval(). Always validate the AST first.
- **Loading template per activity:** Load the full template with all relations once at the start of each engine operation. Do not query per-activity.
- **Forgetting to flush before using IDs:** After creating WorkflowInstance or ActivityInstance, call `await db.flush()` to populate the UUID before referencing it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Expression parsing | Custom tokenizer/parser | Python `ast.parse()` + whitelist | ast module handles all Python expression syntax correctly; building a parser is error-prone |
| UUID generation | Sequential IDs | SQLAlchemy `Uuid()` with `default=uuid.uuid4` | Already established in BaseModel; consistent with all existing tables |
| State machine transitions | Ad-hoc if/else chains | Transition map dict `{(from_state, to_state): True}` | Explicit, testable, documents all valid transitions in one place |
| Audit trail | Manual log calls | `create_audit_record()` from audit_service | Already established pattern; same-transaction atomicity |

**Key insight:** The token model for parallel tracking is the only genuinely new data structure. Everything else builds on existing patterns.

## Common Pitfalls

### Pitfall 1: AND-Join Double-Firing
**What goes wrong:** If two parallel branches complete near-simultaneously in separate requests, the AND-join activity gets activated twice.
**Why it happens:** Race condition where both requests see "I'm the last token" before either commits.
**How to avoid:** Use `SELECT ... FOR UPDATE` on the token rows when checking join conditions, or leverage PostgreSQL's serializable isolation. For SQLite tests, this is less of a concern since tests are single-threaded. In production (PostgreSQL), the synchronous-in-request model (D-01) means only one request at a time modifies a given workflow, but add a `SELECT FOR UPDATE` on the workflow instance row as a defensive lock.
**Warning signs:** Duplicate work items for the same activity, or activity advancing past end twice.

### Pitfall 2: Orphaned Tokens After Workflow Completion
**What goes wrong:** Tokens remain in the execution_tokens table after a workflow finishes, causing stale data buildup.
**Why it happens:** End activity completion marks workflow as Finished but doesn't clean up tokens.
**How to avoid:** When auto-finishing a workflow (D-08), delete all tokens for that workflow instance. This is both a correctness and hygiene concern.

### Pitfall 3: ActivityInstance.state Column Migration
**What goes wrong:** The existing `state` column on `activity_instances` is `String(50)` with default `"dormant"`. Migrating to an Enum column in PostgreSQL requires careful Alembic work; SQLite does not support ALTER COLUMN.
**Why it happens:** Phase 1 created the column as a string, and D-07 requires a proper enum.
**How to avoid:** For PostgreSQL, create the enum type first, then ALTER COLUMN with USING clause. For SQLite tests, the models define the column type and `create_all` handles it. Write the Alembic migration targeting PostgreSQL (production) and ensure SQLite tests work with the model definition directly (since tests use `create_all`).

### Pitfall 4: Template Relationship Loading
**What goes wrong:** Accessing `activity_template.activity_type` on an ActivityInstance fails with `MissingGreenlet` error.
**Why it happens:** SQLAlchemy async requires explicit eager loading. ActivityInstance references activity_template_id but there is no relationship defined on ActivityInstance to load the template.
**How to avoid:** Add `activity_template` relationship to ActivityInstance model. Use `selectinload(ActivityInstance.activity_template)` when querying. The existing template_service.py pattern shows how.

### Pitfall 5: Condition Expression Variable Resolution
**What goes wrong:** Expression evaluation fails because variable names in expressions don't match process variable names, or type coercion is wrong.
**Why it happens:** ProcessVariable stores typed values in separate columns (string_value, int_value, etc.). The evaluator needs to extract the correct typed value based on variable_type.
**How to avoid:** Build a `dict[str, Any]` from process variables, resolving each to its typed value. Include type coercion in the variable resolution step, not the expression evaluator.

### Pitfall 6: Missing Relationships on Instance Models
**What goes wrong:** WorkflowInstance has no relationships to ActivityInstance, WorkItem, ProcessVariable, or WorkflowPackage. Queries require separate lookups.
**Why it happens:** Phase 1 created skeleton models without back-references on instance tables.
**How to avoid:** Add relationships in the model update migration task:
- WorkflowInstance -> activity_instances, work_items, process_variables, workflow_packages
- ActivityInstance -> work_items, activity_template, workflow_instance

## Code Examples

### ActivityState Enum (new in enums.py)
```python
class ActivityState(str, enum.Enum):
    DORMANT = "dormant"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETE = "complete"
    ERROR = "error"
```

### State Transition Map
```python
# Valid workflow state transitions
WORKFLOW_TRANSITIONS: set[tuple[WorkflowState, WorkflowState]] = {
    (WorkflowState.DORMANT, WorkflowState.RUNNING),
    (WorkflowState.RUNNING, WorkflowState.HALTED),
    (WorkflowState.RUNNING, WorkflowState.FAILED),
    (WorkflowState.RUNNING, WorkflowState.FINISHED),
    (WorkflowState.HALTED, WorkflowState.RUNNING),  # resume (Phase 10)
    (WorkflowState.FAILED, WorkflowState.DORMANT),   # restart (Phase 10)
}

ACTIVITY_TRANSITIONS: set[tuple[ActivityState, ActivityState]] = {
    (ActivityState.DORMANT, ActivityState.ACTIVE),
    (ActivityState.ACTIVE, ActivityState.COMPLETE),
    (ActivityState.ACTIVE, ActivityState.PAUSED),
    (ActivityState.ACTIVE, ActivityState.ERROR),
    (ActivityState.PAUSED, ActivityState.ACTIVE),
    (ActivityState.ERROR, ActivityState.ACTIVE),     # retry
}

def enforce_transition(
    current: WorkflowState | ActivityState,
    target: WorkflowState | ActivityState,
    valid_transitions: set,
) -> None:
    if (current, target) not in valid_transitions:
        raise ValueError(f"Invalid state transition: {current.value} -> {target.value}")
```

### ExecutionToken Model
```python
class ExecutionToken(BaseModel):
    __tablename__ = "execution_tokens"

    workflow_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("workflow_instances.id"), nullable=False, index=True
    )
    flow_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("flow_templates.id"), nullable=False
    )
    source_activity_instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("activity_instances.id"), nullable=False
    )
    target_activity_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("activity_templates.id"), nullable=False
    )
    is_consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

### Process Variable Value Resolution
```python
def resolve_variable_value(pv: ProcessVariable) -> Any:
    """Extract the typed value from a ProcessVariable."""
    match pv.variable_type:
        case "string":
            return pv.string_value
        case "int":
            return pv.int_value
        case "boolean":
            return pv.bool_value
        case "date":
            return pv.date_value
        case _:
            return pv.string_value

def build_variable_context(variables: list[ProcessVariable]) -> dict[str, Any]:
    """Build evaluation context from instance process variables."""
    return {pv.name: resolve_variable_value(pv) for pv in variables}
```

### Workflow Start Endpoint Shape
```python
class WorkflowStartRequest(BaseModel):
    template_id: uuid.UUID
    document_ids: list[uuid.UUID] = []  # optional per D-04
    performer_overrides: dict[str, str] = {}  # activity_template_id -> user_id
    initial_variables: dict[str, Any] = {}  # override template defaults

class WorkflowInstanceResponse(BaseModel):
    id: uuid.UUID
    process_template_id: uuid.UUID
    state: WorkflowState
    started_at: datetime | None
    completed_at: datetime | None
    supervisor_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

### Complete Work Item Endpoint Shape
```python
class CompleteWorkItemRequest(BaseModel):
    output_variables: dict[str, Any] = {}  # variables to update

# POST /api/v1/workflows/{workflow_id}/work-items/{work_item_id}/complete
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-jose for JWT | PyJWT | Phase 1 decision | Already using PyJWT |
| passlib for password hashing | pwdlib | Phase 1 decision | Already using pwdlib |
| String columns for enums | Proper SQLAlchemy Enum | Phase 3+ pattern | ActivityState enum needs migration |

**Already current:** All libraries are at latest versions (verified: SQLAlchemy 2.0.48, FastAPI 0.135.1, Pydantic 2.12.5).

## Open Questions

1. **Concurrent workflow modification**
   - What we know: D-01 says synchronous advancement. Single request handles completion.
   - What's unclear: If two users complete parallel activities in the same workflow at the exact same time, do we need row-level locking on the workflow instance?
   - Recommendation: Add `SELECT FOR UPDATE` on workflow_instance row when advancing. For SQLite tests, this is a no-op. Document as a production concern.

2. **Token cleanup timing**
   - What we know: Tokens track flow traversal for AND/OR joins.
   - What's unclear: Should consumed tokens be deleted immediately or marked as consumed and cleaned up later?
   - Recommendation: Mark as consumed (is_consumed=True) rather than delete. This preserves execution history for debugging. Clean up on workflow finish.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `python -m pytest tests/test_workflows.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEC-01 | Start workflow from installed template | integration | `python -m pytest tests/test_workflows.py::test_start_workflow -x` | Wave 0 |
| EXEC-02 | Attach documents at startup | integration | `python -m pytest tests/test_workflows.py::test_start_workflow_with_documents -x` | Wave 0 |
| EXEC-03 | Assign performer overrides at startup | integration | `python -m pytest tests/test_workflows.py::test_start_workflow_performer_overrides -x` | Wave 0 |
| EXEC-04 | Workflow state transitions | integration | `python -m pytest tests/test_workflows.py::test_workflow_state_transitions -x` | Wave 0 |
| EXEC-05 | Engine auto-advances through flows | integration | `python -m pytest tests/test_workflows.py::test_engine_auto_advance -x` | Wave 0 |
| EXEC-06 | Sequential routing A->B->C | integration | `python -m pytest tests/test_workflows.py::test_sequential_routing -x` | Wave 0 |
| EXEC-07 | Parallel routing AND-split/AND-join | integration | `python -m pytest tests/test_workflows.py::test_parallel_routing_and_join -x` | Wave 0 |
| EXEC-12 | OR-join fires on first incoming | integration | `python -m pytest tests/test_workflows.py::test_or_join_routing -x` | Wave 0 |
| EXEC-13 | Process variables read/write | integration | `python -m pytest tests/test_workflows.py::test_process_variables_rw -x` | Wave 0 |
| EXEC-14 | Variables in routing conditions | integration | `python -m pytest tests/test_workflows.py::test_condition_expression_routing -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_workflows.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_workflows.py` -- all EXEC-XX integration tests
- [ ] `tests/test_expression_evaluator.py` -- unit tests for AST sandbox (edge cases: injection attempts, type coercion, invalid syntax)
- [ ] Extend `conftest.py` -- `installed_template` fixture (creates template + validates + installs via API), `parallel_template` fixture (AND-split/join graph)

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis: `src/app/models/workflow.py`, `src/app/models/enums.py`, `src/app/services/template_service.py`, `src/app/services/audit_service.py`
- Python ast module documentation (stdlib, stable API)
- SQLAlchemy 2.0.48 async patterns (verified installed version)
- FastAPI 0.135.1 (verified installed version)
- Pydantic 2.12.5 (verified installed version)

### Secondary (MEDIUM confidence)
- Petri-net token semantics for workflow engines (well-established computer science; Documentum uses this model internally)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all versions verified against installed packages
- Architecture: HIGH -- patterns derived from existing codebase (template_service.py, conftest.py) and locked decisions from CONTEXT.md
- Pitfalls: HIGH -- identified from direct code inspection (missing relationships, String column migration, async loading requirements)
- Expression evaluator: HIGH -- verified ast.parse works with target expressions via live Python test

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable domain, no moving targets)
