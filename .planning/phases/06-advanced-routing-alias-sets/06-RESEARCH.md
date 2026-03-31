# Phase 6: Advanced Routing & Alias Sets - Research

**Researched:** 2026-03-31
**Domain:** Workflow engine routing patterns, performer resolution, alias management
**Confidence:** HIGH

## Summary

Phase 6 extends the existing token-based Petri-net workflow engine with four major capabilities: conditional routing (performer-chosen, expression-based, broadcast), reject flow traversal, alias set management with snapshot-at-start semantics, and sequential/runtime performer assignment modes. The existing codebase provides strong foundations -- `FlowType.REJECT` and `PerformerType.ALIAS` enums already exist, the expression evaluator is production-ready, and the iterative advancement loop in `_advance_from_activity` is well-structured for extension.

The primary technical challenge is modifying `_advance_from_activity` to support three distinct routing modes (conditional, performer-chosen, broadcast) controlled by a new `routing_type` field on ActivityTemplate, plus adding a parallel reject-flow traversal path. The secondary challenge is the alias set data model and its snapshot semantics at workflow start. Sequential performer tracking requires careful state management on ActivityInstance or WorkItem to know which performer in the ordered list is "current."

**Primary recommendation:** Extend the engine incrementally -- first add the `routing_type` field and modify `_advance_from_activity` flow filtering, then add reject flow traversal as a separate engine function, then build alias sets as standalone CRUD + resolve-at-start, and finally add sequential/runtime performer modes to `resolve_performers()`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Performer-chosen routing uses named path selection. Each outgoing flow has a `display_label` field. When completing a work item at a performer-chosen activity, the user selects from these labels. The engine fires only the selected flow.
- **D-02:** An activity-level `routing_type` field controls routing behavior: `conditional` (evaluate expressions), `performer_chosen` (user picks path), or `broadcast` (all outgoing flows fire unconditionally). Default is `conditional` for backward compatibility.
- **D-03:** Rejection follows explicit reject flow edges (`FlowType.REJECT`). The engine traverses reject flows the same way it traverses normal flows, but triggered by rejection instead of completion. If no reject flow exists from the current activity, rejection is denied (error).
- **D-04:** When a reject flow activates a previous activity, that activity resets from COMPLETE to ACTIVE with new work items created for its original performers. Old work items remain in history. Process variables are preserved so the re-performer sees updated context.
- **D-05:** Alias sets are shared, standalone entities (own DB table: `AliasSet` + `AliasMapping`). Templates reference an alias set by FK. Multiple templates can share the same alias set. Updating the set affects future workflow starts only.
- **D-06:** Alias-to-user mappings are resolved (snapshotted) at workflow start time. The resolved mappings are stored on the workflow instance so mid-workflow alias changes don't affect running instances.
- **D-07:** Sequential performers use a `performer_list` JSON field on ActivityTemplate -- an ordered array of user/group IDs. Task goes to performer[0] first, then performer[1] on completion, etc. On rejection within the sequence, it goes back to the previous performer in the list. All must complete for the activity to be COMPLETE.
- **D-08:** Runtime selection: activity has a candidate group (via `performer_id` pointing to a group). When completing, the current performer selects the next performer from that group's members (pass `next_performer_id` in completion request). Engine rejects completion if no selection provided.
- **D-09:** New `PerformerType` enum values needed: `SEQUENTIAL` and `RUNTIME_SELECTION` added alongside existing USER, GROUP, SUPERVISOR, ALIAS.

### Claude's Discretion
- Expression evaluator extensions (if needed for new condition patterns)
- Internal state tracking for sequential performer position (e.g., a `current_performer_index` field on ActivityInstance or WorkItem)
- Whether broadcast routing needs special token/join handling or just fires all flows

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXEC-08 | Conditional routing (performer-chosen): performer selects which path to take | D-01/D-02: `routing_type` field + `display_label` on flows + `selected_path` param on completion |
| EXEC-09 | Conditional routing (condition-based): system evaluates expressions to determine next activity | Already partially working via `condition_expression` on flows; D-02 `routing_type=conditional` makes this the default path |
| EXEC-10 | Conditional routing (broadcast): all connected activities activated simultaneously | D-02 `routing_type=broadcast` fires all outgoing flows unconditionally, ignoring condition expressions |
| EXEC-11 | Reject flow: performer rejects task, document returns to previous activity | D-03/D-04: reject flow traversal + activity reset + new work items for original performers |
| PERF-04 | Sequential performers (ordered list, can reject back) | D-07/D-09: `performer_list` JSON field + `current_performer_index` tracking + sequential rejection |
| PERF-05 | Runtime selection (previous performer chooses next) | D-08/D-09: `next_performer_id` param on completion + group membership validation |
| ALIAS-01 | Create alias set mapping logical roles to actual users/groups | D-05: `AliasSet` + `AliasMapping` tables + CRUD endpoints |
| ALIAS-02 | Alias sets assigned to workflow templates | D-05: FK from ProcessTemplate to AliasSet + template schema updates |
| ALIAS-03 | Updating alias mapping does not require editing workflow template | D-05: Shared standalone entities; template references by FK, not by copy |
</phase_requirements>

## Standard Stack

No new external dependencies required. This phase extends existing models, services, and APIs using the established stack (FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic).

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.x | ORM -- new tables (AliasSet, AliasMapping), model field additions | Already in use |
| Alembic | 1.18.x | Database migrations for schema changes | Already in use |
| FastAPI | 0.135.x | New CRUD endpoints for alias sets, modified completion endpoints | Already in use |
| Pydantic | 2.12.x | Request/response schemas for alias sets, extended completion schemas | Already in use |

### Supporting
No additional libraries needed. The expression evaluator, audit service, and all infrastructure are in place.

## Architecture Patterns

### Modified Files Map

```
src/app/
  models/
    enums.py              # Add PerformerType.SEQUENTIAL, PerformerType.RUNTIME_SELECTION, RoutingType enum
    workflow.py            # Add fields to ActivityTemplate, FlowTemplate; new AliasSet, AliasMapping models
  schemas/
    template.py           # Add routing_type, performer_list, display_label to activity/flow schemas
    inbox.py              # Add selected_path, next_performer_id to completion request
    workflow.py            # Add selected_path, next_performer_id to workflow completion request
    alias.py              # NEW: Pydantic schemas for alias CRUD
  routers/
    aliases.py            # NEW: CRUD endpoints for alias sets
    inbox.py              # Modify complete/reject to pass new params
    workflows.py          # Modify complete to pass new params; add alias_set_id to start
  services/
    engine_service.py     # Major changes: routing_type dispatch, reject flow traversal, sequential/runtime performers
    inbox_service.py      # Pass through selected_path, next_performer_id to engine
    alias_service.py      # NEW: Alias set CRUD + resolve-at-start logic
alembic/versions/
    xxx_phase6_routing.py # Migration: new columns + new tables
tests/
    test_routing.py       # NEW: conditional, broadcast, performer-chosen routing tests
    test_reject_flows.py  # NEW: reject flow traversal tests
    test_aliases.py       # NEW: alias set CRUD + snapshot-at-start tests
    test_sequential.py    # NEW: sequential and runtime performer tests
```

### Pattern 1: Routing Type Dispatch in Advancement Loop

**What:** The `_advance_from_activity` function currently iterates all outgoing NORMAL flows and evaluates condition expressions. With the new `routing_type` field, the flow-filtering logic needs to branch based on routing type.

**When to use:** Every time the engine advances from a completed activity.

**Example:**
```python
# In _advance_from_activity, after getting outgoing_flows:
routing_type = activity_template_map.get(current.activity_template_id).routing_type or "conditional"

match routing_type:
    case "broadcast":
        # Fire ALL outgoing normal flows, ignore condition_expression
        flows_to_fire = outgoing_flows
    case "performer_chosen":
        # Fire only the flow matching selected_path label
        if not selected_path:
            raise ValueError("Performer-chosen activity requires selected_path")
        flows_to_fire = [f for f in outgoing_flows if f.display_label == selected_path]
        if not flows_to_fire:
            raise ValueError(f"No flow with label '{selected_path}'")
    case "conditional" | _:
        # Existing behavior: evaluate condition_expression on each flow
        flows_to_fire = []
        for flow in outgoing_flows:
            if flow.condition_expression:
                if evaluate_expression(flow.condition_expression, var_context):
                    flows_to_fire.append(flow)
            else:
                flows_to_fire.append(flow)  # No condition = always fire
```

### Pattern 2: Reject Flow Traversal

**What:** A new `reject_work_item` function in engine_service that finds REJECT flows from the current activity and traverses them, resetting target activities.

**When to use:** When a user rejects a work item and the engine needs to route backward.

**Example:**
```python
async def reject_work_item(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    work_item_id: uuid.UUID,
    user_id: str,
    reason: str | None = None,
) -> WorkItem:
    # 1. Load and validate work item (same as complete_work_item)
    # 2. Mark work item as REJECTED
    # 3. Find REJECT flows from current activity template
    reject_flows = [
        f for f in template.flow_templates
        if not f.is_deleted
        and f.source_activity_id == activity_instance.activity_template_id
        and f.flow_type == FlowType.REJECT
    ]
    if not reject_flows:
        raise ValueError("No reject flow defined for this activity")
    # 4. For each reject flow target:
    #    - Reset target ActivityInstance: COMPLETE -> ACTIVE (need new transition)
    #    - Create new work items for original performers
    #    - Process variables preserved (already on workflow instance)
```

### Pattern 3: Activity Reset for Reject (D-04)

**What:** When a reject flow activates a previously-completed activity, that activity resets to ACTIVE and gets fresh work items. This requires a new state transition COMPLETE -> ACTIVE in `ACTIVITY_TRANSITIONS`.

**When to use:** Reject flow landing on a previously completed activity.

**Key detail:** Add `(ActivityState.COMPLETE, ActivityState.ACTIVE)` to `ACTIVITY_TRANSITIONS` set. Old work items stay in history (no deletion). New work items created for the activity's configured performers.

### Pattern 4: Alias Snapshot at Start

**What:** When `start_workflow` is called, if the template has an alias set, resolve all alias mappings to concrete user IDs and store them as a JSON blob on the WorkflowInstance (new `alias_snapshot` column). During performer resolution, ALIAS type reads from this snapshot, not from the live AliasSet.

**When to use:** Workflow instantiation.

**Example:**
```python
# In start_workflow, after creating WorkflowInstance:
if template.alias_set_id:
    alias_set = await alias_service.get_alias_set_with_mappings(db, template.alias_set_id)
    snapshot = {}
    for mapping in alias_set.mappings:
        snapshot[mapping.alias_name] = str(mapping.target_id)
    # Apply performer_overrides if provided
    if performer_overrides:
        for alias_name, override_id in performer_overrides.items():
            if alias_name in snapshot:
                snapshot[alias_name] = override_id
    instance.alias_snapshot = snapshot
```

### Pattern 5: Sequential Performer Tracking

**What:** For `PerformerType.SEQUENTIAL`, use a `current_performer_index` field on ActivityInstance to track position in the ordered performer list. Each completion advances the index; rejection decrements it.

**Recommended:** Store `current_performer_index` on ActivityInstance (Integer, nullable, default 0). This is cleaner than storing it on WorkItem because the sequence belongs to the activity, not individual work items.

**When activity completes a sequential step:**
1. Increment `current_performer_index`
2. If index < len(performer_list): create new work item for performer_list[index], activity stays ACTIVE
3. If index >= len(performer_list): all performers done, activity becomes COMPLETE, advance workflow

**When sequential step is rejected:**
1. Decrement `current_performer_index` (min 0)
2. Create new work item for performer_list[decremented_index]

### Anti-Patterns to Avoid

- **Modifying old work items during reject:** D-04 explicitly says old work items remain in history. Create NEW work items for the reset activity.
- **Reading live alias mappings mid-workflow:** D-06 requires snapshot semantics. Always read from `alias_snapshot` on the workflow instance.
- **Recursive reject flow traversal:** Reject flows should be single-hop (source -> target). Do not chain reject flows or auto-complete after rejection.
- **Broadcasting through conditions:** When `routing_type=broadcast`, explicitly skip condition evaluation. Do not evaluate and then fire all anyway.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Expression evaluation | Custom parser | Existing `expression_evaluator.py` | Already sandboxed, tested, production-ready |
| State machine enforcement | Ad-hoc if/else checks | Existing `ACTIVITY_TRANSITIONS` / `_enforce_activity_transition()` | Add new transition to the set, don't bypass the guard |
| Audit trail | Manual logging | Existing `create_audit_record()` | Consistent format, append-only |
| Performer resolution | Inline logic | Extend existing `resolve_performers()` match/case | Single entry point for all performer types |

## Common Pitfalls

### Pitfall 1: Double Advancement on Broadcast
**What goes wrong:** Broadcast fires all outgoing flows. If two flows target the same AND-join activity, and both tokens arrive immediately, the activity fires twice.
**Why it happens:** The existing OR-join guard checks `state != DORMANT` to prevent double activation. But if both tokens arrive in the same queue iteration before the target is activated, the guard might not catch it.
**How to avoid:** The existing `_should_activate` function with AND-join token counting handles this correctly -- it only activates when ALL incoming tokens are present. For OR-join targets of broadcast, the existing `state != DORMANT` guard prevents double activation. Verify with tests that cover broadcast -> OR-join and broadcast -> AND-join scenarios.
**Warning signs:** Duplicate work items for the same activity instance.

### Pitfall 2: Activity Reset State Transition
**What goes wrong:** `ACTIVITY_TRANSITIONS` does not currently include `(COMPLETE, ACTIVE)`. Reject flow traversal will fail with a ValueError.
**Why it happens:** The transition set was designed for forward-only flow.
**How to avoid:** Add `(ActivityState.COMPLETE, ActivityState.ACTIVE)` to `ACTIVITY_TRANSITIONS` at the start of implementation.
**Warning signs:** "Invalid state transition: complete -> active" error during reject flow tests.

### Pitfall 3: Sequential Performer Completion Logic
**What goes wrong:** Engine calls `_advance_from_activity` after each work item completion. For sequential performers, the activity should NOT advance to the next activity until ALL sequential performers have completed.
**Why it happens:** The current `complete_work_item` always calls `_advance_from_activity` after marking the work item complete.
**How to avoid:** Add a check in `complete_work_item`: if the activity uses sequential performers and `current_performer_index < len(performer_list) - 1`, create next work item and return WITHOUT calling `_advance_from_activity`. Only advance when the last performer completes.
**Warning signs:** Workflow advances to next activity after first sequential performer completes.

### Pitfall 4: Alias Resolution in resolve_performers
**What goes wrong:** `resolve_performers()` currently returns `[]` for ALIAS type. If alias resolution is not connected to the workflow's `alias_snapshot`, alias-type activities get no performers.
**Why it happens:** The alias snapshot lives on the WorkflowInstance, but `resolve_performers` needs access to it.
**How to avoid:** Pass `alias_snapshot` (or the full workflow instance) to `resolve_performers`. The function already receives the workflow object -- add alias snapshot reading to the ALIAS match case.
**Warning signs:** Activities with alias performers get unassigned work items (performer_id=None).

### Pitfall 5: SQLite JSON Column in Tests
**What goes wrong:** Tests use SQLite (not PostgreSQL). New JSON columns (`performer_list`, `alias_snapshot`) need to work with SQLite's JSON support.
**Why it happens:** The project uses `sqlalchemy.JSON` (not `postgresql.JSONB`) per Phase 1 decision for dialect-agnostic models. But test assertions on JSON content may behave differently.
**How to avoid:** Use `sqlalchemy.JSON` (already the convention). Test with explicit Python dict comparisons, not SQL JSON operators.
**Warning signs:** Tests pass locally but fail with JSON serialization errors.

### Pitfall 6: Performer-Chosen Missing Flow Label
**What goes wrong:** User completes a performer-chosen activity but the `selected_path` label doesn't match any flow's `display_label`.
**Why it happens:** Label mismatch between what the UI presents and what flows have stored.
**How to avoid:** When activating a performer-chosen activity, include available path labels in the work item response (or inbox detail) so the UI knows valid options. Validate `selected_path` against actual flow labels before attempting advancement.
**Warning signs:** 400 error "No flow with label X" on completion.

## Code Examples

### New Enum: RoutingType
```python
# In src/app/models/enums.py
class RoutingType(str, enum.Enum):
    CONDITIONAL = "conditional"
    PERFORMER_CHOSEN = "performer_chosen"
    BROADCAST = "broadcast"
```

### New Model Fields on ActivityTemplate
```python
# In src/app/models/workflow.py, ActivityTemplate class
routing_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default="conditional")
performer_list: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # For SEQUENTIAL: ordered list of user IDs
```

### New Field on FlowTemplate
```python
# In src/app/models/workflow.py, FlowTemplate class
display_label: Mapped[str | None] = mapped_column(String(255), nullable=True)  # For performer-chosen paths
```

### New Fields on ActivityInstance
```python
# In src/app/models/workflow.py, ActivityInstance class
current_performer_index: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
```

### New Field on WorkflowInstance
```python
# In src/app/models/workflow.py, WorkflowInstance class
alias_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Resolved alias mappings
```

### New Field on ProcessTemplate
```python
# In src/app/models/workflow.py, ProcessTemplate class
alias_set_id: Mapped[uuid.UUID | None] = mapped_column(
    Uuid(), ForeignKey("alias_sets.id"), nullable=True
)
```

### AliasSet and AliasMapping Models
```python
# In src/app/models/workflow.py (or new alias.py)
class AliasSet(BaseModel):
    __tablename__ = "alias_sets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    mappings: Mapped[list["AliasMapping"]] = relationship(back_populates="alias_set")


class AliasMapping(BaseModel):
    __tablename__ = "alias_mappings"

    alias_set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("alias_sets.id"), nullable=False
    )
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., "reviewer", "approver"
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "user" or "group"
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)  # user or group UUID

    alias_set: Mapped["AliasSet"] = relationship(back_populates="mappings")
```

### Extended resolve_performers for ALIAS and SEQUENTIAL
```python
# In engine_service.py resolve_performers():
case "alias":
    if not performer_id:
        return []
    # performer_id is the alias_name, look up in workflow's alias_snapshot
    snapshot = workflow.alias_snapshot or {}
    target_id = snapshot.get(performer_id)
    if target_id:
        return [uuid.UUID(target_id)]
    return []
case "sequential":
    # Return the current performer based on index
    # performer_list is on the activity template, index is on activity instance
    # Caller must pass activity_template and activity_instance
    return []  # Handled specially in advancement loop
case "runtime_selection":
    # Handled during completion -- next_performer_id passed explicitly
    return []  # Placeholder; actual performer comes from completion request
```

### Modified Complete Inbox Request Schema
```python
# In src/app/schemas/inbox.py
class CompleteFromInboxRequest(BaseModel):
    output_variables: dict[str, Any] = {}
    selected_path: str | None = None       # For performer-chosen routing
    next_performer_id: str | None = None   # For runtime selection
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Only NORMAL flow traversal | NORMAL + REJECT flow traversal | Phase 6 | Reject flows now functional |
| Single routing mode (conditional) | Three routing modes (conditional, performer_chosen, broadcast) | Phase 6 | Activity-level routing control |
| Four performer types (USER, GROUP, SUPERVISOR, ALIAS) | Six performer types (+SEQUENTIAL, RUNTIME_SELECTION) | Phase 6 | Richer assignment models |
| Alias returns empty | Alias resolved from snapshot | Phase 6 | Alias-based assignment works |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v --tb=short` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEC-08 | Performer-chosen: user selects path, only selected flow fires | integration | `python -m pytest tests/test_routing.py::test_performer_chosen_routing -x` | Wave 0 |
| EXEC-09 | Condition-based: expression evaluation selects flow | integration | `python -m pytest tests/test_routing.py::test_conditional_routing -x` | Wave 0 |
| EXEC-10 | Broadcast: all outgoing flows fire | integration | `python -m pytest tests/test_routing.py::test_broadcast_routing -x` | Wave 0 |
| EXEC-11 | Reject flow traversal resets previous activity | integration | `python -m pytest tests/test_reject_flows.py::test_reject_traverses_reject_flow -x` | Wave 0 |
| PERF-04 | Sequential performers: ordered completion, reject back | integration | `python -m pytest tests/test_sequential.py::test_sequential_performers -x` | Wave 0 |
| PERF-05 | Runtime selection: next performer chosen at completion | integration | `python -m pytest tests/test_sequential.py::test_runtime_selection -x` | Wave 0 |
| ALIAS-01 | Alias set CRUD | integration | `python -m pytest tests/test_aliases.py::test_create_alias_set -x` | Wave 0 |
| ALIAS-02 | Alias set assigned to template | integration | `python -m pytest tests/test_aliases.py::test_template_alias_set -x` | Wave 0 |
| ALIAS-03 | Alias update without template edit | integration | `python -m pytest tests/test_aliases.py::test_alias_update_independent -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_routing.py` -- covers EXEC-08, EXEC-09, EXEC-10
- [ ] `tests/test_reject_flows.py` -- covers EXEC-11
- [ ] `tests/test_sequential.py` -- covers PERF-04, PERF-05
- [ ] `tests/test_aliases.py` -- covers ALIAS-01, ALIAS-02, ALIAS-03
- [ ] Fixtures for performer-chosen template, reject flow template, sequential performer template, alias set template in relevant test files (inline, per Phase 5 convention)

## Open Questions

1. **Broadcast + AND-join interaction**
   - What we know: Broadcast fires all outgoing flows. If two broadcast outputs converge on an AND-join, both tokens will be placed before the join evaluates.
   - What's unclear: Does the existing `_should_activate` AND-join logic handle this correctly when tokens are placed in the same queue iteration?
   - Recommendation: The existing logic should work because tokens are placed and then `_should_activate` counts them. Test explicitly with a broadcast -> AND-join fixture.

2. **Sequential performer rejection at index 0**
   - What we know: D-07 says rejection goes to previous performer. At index 0, there is no previous.
   - What's unclear: Should rejection at index 0 fail (error) or follow reject flows (if any)?
   - Recommendation: At index 0, sequential rejection should raise ValueError("Cannot reject: already at first performer"). If the activity has reject flows, those are a separate mechanism (activity-level reject, not sequential-level).

3. **display_label uniqueness**
   - What we know: D-01 says performer selects from display labels of outgoing flows.
   - What's unclear: Must labels be unique per activity? What if two flows have the same label?
   - Recommendation: Enforce uniqueness per source activity during template validation. If duplicate labels exist, validation fails with a descriptive error.

## Sources

### Primary (HIGH confidence)
- `src/app/services/engine_service.py` -- Current advancement loop, token model, performer resolution (read directly)
- `src/app/models/enums.py` -- Existing FlowType.REJECT, PerformerType.ALIAS already defined (read directly)
- `src/app/models/workflow.py` -- Current model structure, BaseModel pattern (read directly)
- `src/app/services/inbox_service.py` -- Current complete/reject delegation pattern (read directly)
- `src/app/services/expression_evaluator.py` -- Sandboxed AST evaluator (read directly)
- `src/app/schemas/template.py` -- Current schema patterns (read directly)
- `.planning/phases/06-advanced-routing-alias-sets/06-CONTEXT.md` -- All decisions D-01 through D-09 (read directly)

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` -- Project decisions and conventions from Phases 1-5 (read directly)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, extending existing proven codebase
- Architecture: HIGH -- patterns directly derived from reading current engine code and CONTEXT.md decisions
- Pitfalls: HIGH -- identified from code analysis of actual edge cases in the advancement loop
- Alias model: HIGH -- straightforward CRUD + FK pattern consistent with existing models

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable -- internal project, no external dependency changes)
