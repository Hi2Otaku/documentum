# Phase 7: Document Lifecycle & ACL - Research

**Researched:** 2026-03-31
**Domain:** Document state machine, access control lists, workflow-lifecycle integration
**Confidence:** HIGH

## Summary

Phase 7 adds two tightly coupled subsystems: (1) a document lifecycle state machine with enforced transitions (DRAFT -> REVIEW -> APPROVED -> ARCHIVED), and (2) an object-level ACL system that automatically adjusts permissions when lifecycle state changes. Both integrate into the existing workflow engine so that activity completion can trigger lifecycle transitions on all documents in a workflow package.

The codebase already has well-established patterns for everything this phase needs. The transition set pattern (WORKFLOW_TRANSITIONS, ACTIVITY_TRANSITIONS) maps directly to lifecycle transitions. The existing `create_audit_record` function handles audit logging. FastAPI dependency injection (get_current_user, get_current_active_admin) provides the template for a `require_permission` dependency. The only genuinely new concepts are the `document_acl` table, the `lifecycle_acl_rule` seed data table, and the lifecycle_action field on ActivityTemplate.

**Primary recommendation:** Follow existing patterns exactly. Lifecycle transitions use the same set-of-tuples enforcement as workflow/activity transitions. ACL is a new table + service + dependency. The engine hook goes in `_advance_from_activity` immediately after marking the activity COMPLETE and before processing outgoing flows.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Fixed enum for lifecycle states: DRAFT, REVIEW, APPROVED, ARCHIVED. Not configurable per document type.
- **D-02:** Valid transitions enforced via a transition map set (same pattern as WORKFLOW_TRANSITIONS and ACTIVITY_TRANSITIONS). Set of (from_state, to_state) tuples.
- **D-03:** Transitions can be triggered both manually (dedicated API endpoint) and automatically (workflow activity completion). Both paths go through the same service function.
- **D-04:** Invalid transition attempts raise ValueError, log an audit record, and do not halt the workflow. Document stays in current state.
- **D-05:** ACL stored in a dedicated table: `document_acl` with columns (id, document_id, principal_id, principal_type [user/group], permission_level). Queryable and indexable.
- **D-06:** Four permission levels as enum: READ, WRITE, DELETE, ADMIN. ADMIN implies all others.
- **D-07:** Lifecycle-ACL rule table maps lifecycle state transitions to ACL changes. Rules evaluated automatically on every lifecycle transition.
- **D-08:** Permission checks enforced via FastAPI dependency injection on all document routes. A `require_permission(document_id, level)` dependency that raises 403 on insufficient access.
- **D-09:** New field on ActivityTemplate: `lifecycle_action` (nullable string). Format: "transition_to:{state}". When activity completes, engine checks this field and triggers the transition if present.
- **D-10:** Lifecycle action affects ALL documents in the workflow package.
- **D-11:** Lifecycle transition fires on activity completion, after work item is completed but before advancing to the next activity.

### Claude's Discretion
- Default ACL rules for each lifecycle state (what permissions are set on document creation, what changes per transition)
- Whether to add `lifecycle_state` field directly on Document model or in a separate LifecycleState table
- Migration strategy for existing documents (default to DRAFT state)

### Deferred Ideas (OUT OF SCOPE)
None.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIFE-01 | Documents transition through defined states: Draft -> Review -> Approved -> Archived | LifecycleState enum + LIFECYCLE_TRANSITIONS set on Document model; transition_lifecycle_state service function |
| LIFE-02 | Lifecycle transitions can be triggered automatically by workflow activity completion | lifecycle_action field on ActivityTemplate; engine hook in _advance_from_activity after COMPLETE before flows |
| LIFE-03 | Lifecycle state changes are recorded in the audit trail | create_audit_record with entity_type="document", action="lifecycle_transition" |
| LIFE-04 | ACL permissions automatically change when lifecycle state changes | lifecycle_acl_rule table evaluated in transition_lifecycle_state; apply_lifecycle_acl_rules helper |
| ACL-01 | Objects have Access Control Lists defining who can read/write/delete | document_acl table with principal_id, principal_type, permission_level columns |
| ACL-02 | Workflow activities can automatically modify document ACLs | Achieved via LIFE-04 -- lifecycle transition triggers ACL rule application |
| ACL-03 | ACL changes are recorded in the audit trail | create_audit_record with entity_type="document_acl", action="acl_modified" |
| ACL-04 | Permission checks are enforced on all API operations | require_permission FastAPI dependency injected on all document routes |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech stack:** FastAPI + SQLAlchemy 2.0 async + PostgreSQL (SQLite for tests) + Pydantic v2
- **Service layer pattern:** Routers delegate to service functions; services handle business logic and audit
- **Enum-based state tracking:** Use Python str enums, lowercase values, registered with SQLAlchemy Enum
- **Transition enforcement:** Set-of-tuples pattern (e.g., WORKFLOW_TRANSITIONS)
- **Models dialect-agnostic:** sqlalchemy.Uuid not postgresql.UUID, JSON not JSONB (SQLite test compat)
- **Audit:** create_audit_record in same transaction via flush
- **Phase 06 convention:** All new model fields nullable with defaults for backward compatibility
- **Service raises ValueError:** Router maps to HTTP 400/403/404

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.x | HTTP framework | Already in use; dependency injection for permission checks |
| SQLAlchemy | 2.0.x | ORM | Async models, relationships, existing pattern |
| Pydantic | 2.12.x | Validation | Schemas for lifecycle/ACL request/response |
| Alembic | 1.18.x | Migrations | New tables require migration script |

### No Additional Libraries Needed
This phase requires zero new dependencies. Everything is achievable with existing stack:
- Lifecycle state machine: Python enum + set of tuples (same pattern as engine_service.py)
- ACL table: Standard SQLAlchemy model
- Permission dependency: FastAPI Depends() -- same pattern as get_current_user
- Audit: Existing create_audit_record function

## Architecture Patterns

### Recommended Project Structure (new files only)
```
src/app/
  models/
    document.py          # MODIFY: add lifecycle_state field
    workflow.py          # MODIFY: add lifecycle_action to ActivityTemplate
    enums.py             # MODIFY: add LifecycleState, PermissionLevel enums
    acl.py               # NEW: DocumentACL and LifecycleACLRule models
  schemas/
    document.py          # MODIFY: add lifecycle_state to responses
    acl.py               # NEW: ACL request/response schemas
    lifecycle.py         # NEW: lifecycle transition schemas
  services/
    lifecycle_service.py # NEW: transition_lifecycle_state, apply_lifecycle_acl_rules
    acl_service.py       # NEW: CRUD for ACL entries, check_permission
    engine_service.py    # MODIFY: hook lifecycle_action in advancement
  routers/
    documents.py         # MODIFY: add permission dependency, lifecycle endpoint
    lifecycle.py         # NEW: manual lifecycle transition endpoint
  core/
    dependencies.py      # MODIFY: add require_permission dependency
```

### Pattern 1: Lifecycle State Machine (mirrors engine_service.py exactly)
**What:** Enum-based states with transition enforcement via set lookup
**When to use:** Document lifecycle transitions
**Example:**
```python
# In enums.py
class LifecycleState(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"

# In lifecycle_service.py
LIFECYCLE_TRANSITIONS: set[tuple[LifecycleState, LifecycleState]] = {
    (LifecycleState.DRAFT, LifecycleState.REVIEW),
    (LifecycleState.REVIEW, LifecycleState.APPROVED),
    (LifecycleState.REVIEW, LifecycleState.DRAFT),      # Reject back to draft
    (LifecycleState.APPROVED, LifecycleState.ARCHIVED),
}
```

### Pattern 2: Permission Dependency (mirrors get_current_user pattern)
**What:** FastAPI dependency that checks ACL before route executes
**When to use:** Every document route
**Example:**
```python
# In core/dependencies.py
def require_permission(level: PermissionLevel):
    async def checker(
        document_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        has_access = await acl_service.check_permission(
            db, document_id, current_user.id, level
        )
        if not has_access:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return checker

# Usage in router
@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    user: User = Depends(require_permission(PermissionLevel.READ)),
    db: AsyncSession = Depends(get_db),
):
    ...
```

### Pattern 3: Workflow-Triggered Lifecycle (engine hook)
**What:** After activity completion, before advancing, check lifecycle_action field
**When to use:** In _advance_from_activity or complete_work_item
**Hook point:** In complete_work_item, after step 6 (sequential/runtime checks) and before step 7 (_advance_from_activity call), OR at the start of _advance_from_activity after marking COMPLETE.
**Example:**
```python
# In engine_service.py, inside _advance_from_activity, after marking completed_activity COMPLETE:
activity_template = activity_template_map.get(completed_activity.activity_template_id)
if activity_template and activity_template.lifecycle_action:
    from app.services import lifecycle_service
    await lifecycle_service.execute_lifecycle_action(
        db, workflow, activity_template.lifecycle_action, user_id
    )
```

### Pattern 4: Lifecycle-ACL Rule Application
**What:** When lifecycle state changes, look up rules and apply ACL modifications
**When to use:** Inside transition_lifecycle_state, after state change
**Example:**
```python
# lifecycle_acl_rule table rows (seed data):
# (from_state=REVIEW, to_state=APPROVED, action="remove", permission_level=WRITE, principal_type="non_admin")
# (from_state=APPROVED, to_state=ARCHIVED, action="remove", permission_level=DELETE, principal_type="all")

async def apply_lifecycle_acl_rules(
    db: AsyncSession, document_id: uuid.UUID, 
    from_state: LifecycleState, to_state: LifecycleState, user_id: str
):
    rules = await get_rules_for_transition(db, from_state, to_state)
    for rule in rules:
        if rule.action == "remove":
            await remove_permission(db, document_id, rule.permission_level, rule.principal_filter)
        elif rule.action == "add":
            await add_permission(db, document_id, rule.principal_id, rule.permission_level)
        # Audit each ACL change
        await create_audit_record(db, entity_type="document_acl", ...)
```

### Claude's Discretion Recommendations

**1. lifecycle_state on Document model directly (not separate table):**
- Add `lifecycle_state` as a nullable column on the existing Document model with default `LifecycleState.DRAFT`
- Rationale: Simpler queries, no join needed, consistent with how workflow state is stored directly on WorkflowInstance
- One column vs. a whole table + relationship for what is fundamentally a single enum field

**2. Default ACL rules (seed data):**

| Transition | Action | Permission | Principal Filter | Rationale |
|------------|--------|------------|------------------|-----------|
| (any) -> DRAFT | add | WRITE | document creator | Creator gets full write access |
| DRAFT -> REVIEW | add | READ | all users | Reviewers need to read |
| REVIEW -> APPROVED | remove | WRITE | non-admin | Approved docs are read-only |
| APPROVED -> ARCHIVED | remove | DELETE | all | Archived docs cannot be deleted |

These rules should be stored in a `lifecycle_acl_rules` table and loaded as seed data in the migration or via a startup function. Not hardcoded in Python.

**3. Migration strategy for existing documents:**
- Add `lifecycle_state` column as nullable with server_default='draft'
- Alembic migration sets all existing documents to DRAFT
- No ACL entries created for existing documents (they operate without ACL until explicitly managed)
- This is the safest approach -- existing documents continue to work, ACL enforcement on document routes should fall back to "allow if no ACL entries exist" (or "allow for document creator")

### Anti-Patterns to Avoid
- **Hardcoding ACL rules in Python:** Store in database table, not if/else chains. Rules should be data, not code.
- **Checking permissions inside service layer:** Permission check belongs in the FastAPI dependency layer (separation of concerns). Services assume the caller is authorized.
- **Separate lifecycle_state table:** Overengineered for a single enum field. Just add a column to Document.
- **Blocking workflow on lifecycle failure:** Per D-04, lifecycle errors are logged but do not halt the workflow. Use try/except in the engine hook.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| State machine validation | Custom FSM library | Set-of-tuples pattern | Already proven in engine_service.py; 5 lines of code |
| Permission hierarchy (ADMIN implies all) | Nested if/else permission checks | Integer comparison or set containment | PermissionLevel.ADMIN.value >= requested.value |
| ACL caching | In-memory ACL cache | Direct DB query per request | Premature optimization; SQLite/PG query is fast enough |

## Common Pitfalls

### Pitfall 1: Permission Check Bypass on Upload
**What goes wrong:** New document uploads don't have ACL entries yet, so the permission check dependency blocks the upload.
**Why it happens:** The document doesn't exist before the upload, so there's no ACL to check.
**How to avoid:** Upload endpoint does NOT use require_permission -- any authenticated user can upload. ACL entries are created in the upload service function (document creator gets ADMIN).
**Warning signs:** 403 errors on document upload.

### Pitfall 2: Lifecycle Action Halting Workflow
**What goes wrong:** A lifecycle transition error (e.g., document already in target state) raises an exception that propagates up and prevents workflow advancement.
**Why it happens:** Missing try/except around the lifecycle hook in the engine.
**How to avoid:** Per D-04, wrap lifecycle_action execution in try/except. Log the error and audit it, but continue advancement.
**Warning signs:** Workflows stuck at activities with lifecycle_action configured.

### Pitfall 3: ACL Check on Bulk Package Operations
**What goes wrong:** When lifecycle_action affects all documents in a package (D-10), checking permissions for each document individually causes N+1 queries.
**Why it happens:** Naive loop over workflow_packages.
**How to avoid:** Load all document IDs from workflow_packages in one query, then apply lifecycle transition in a batch. The engine is acting as the system (not a user), so ACL checks are bypassed for engine-triggered transitions.
**Warning signs:** Slow workflow advancement when packages have many documents.

### Pitfall 4: Circular Import with Engine Service
**What goes wrong:** lifecycle_service imports engine models, engine_service imports lifecycle_service -- circular import.
**Why it happens:** Engine needs lifecycle, lifecycle needs engine models.
**How to avoid:** Use lazy import (same pattern as Phase 5's resolve_performers): `from app.services import lifecycle_service` inside the function body, not at module top.
**Warning signs:** ImportError at startup.

### Pitfall 5: SQLite Enum Compatibility
**What goes wrong:** New LifecycleState and PermissionLevel enums fail in SQLite test environment.
**Why it happens:** SQLAlchemy Enum types need careful naming.
**How to avoid:** Follow existing convention: `Enum(LifecycleState, name="lifecyclestate")` with lowercase name. Same pattern as workflowstate, activitystate, etc.
**Warning signs:** Test failures with "enum not found" type errors.

### Pitfall 6: Document Creator Loses Access After Lifecycle Change
**What goes wrong:** ACL rules remove WRITE from "non-admin" principals, accidentally including the document creator.
**Why it happens:** Rule matching is too broad.
**How to avoid:** Document creator should always get ADMIN permission level (which is never removed by lifecycle rules). Only WRITE/READ/DELETE are subject to rule-based removal.
**Warning signs:** Document creators unable to view their own documents after approval.

## Code Examples

### New Enums (enums.py additions)
```python
class LifecycleState(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"

class PermissionLevel(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
```

### DocumentACL Model (acl.py)
```python
class DocumentACL(BaseModel):
    __tablename__ = "document_acl"
    __table_args__ = (
        UniqueConstraint("document_id", "principal_id", "principal_type", name="uq_document_acl_principal"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False, index=True
    )
    principal_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "group"
    permission_level: Mapped[PermissionLevel] = mapped_column(
        Enum(PermissionLevel, name="permissionlevel"), nullable=False
    )
```

### LifecycleACLRule Model (acl.py)
```python
class LifecycleACLRule(BaseModel):
    __tablename__ = "lifecycle_acl_rules"

    from_state: Mapped[LifecycleState] = mapped_column(
        Enum(LifecycleState, name="lifecyclestate"), nullable=False
    )
    to_state: Mapped[LifecycleState] = mapped_column(
        Enum(LifecycleState, name="lifecyclestate"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # "add" or "remove"
    permission_level: Mapped[PermissionLevel] = mapped_column(
        Enum(PermissionLevel, name="permissionlevel"), nullable=False
    )
    principal_filter: Mapped[str] = mapped_column(
        String(50), nullable=False  # "creator", "non_admin", "all"
    )
```

### Document Model Extension
```python
# Add to Document class in document.py:
lifecycle_state: Mapped[str | None] = mapped_column(
    Enum(LifecycleState, name="lifecyclestate"), 
    default=LifecycleState.DRAFT, 
    nullable=True  # Nullable for backward compatibility
)
```

### Permission Hierarchy Check
```python
PERMISSION_HIERARCHY = {
    PermissionLevel.READ: 1,
    PermissionLevel.WRITE: 2,
    PermissionLevel.DELETE: 3,
    PermissionLevel.ADMIN: 4,
}

def has_sufficient_permission(granted: PermissionLevel, required: PermissionLevel) -> bool:
    """ADMIN implies all; DELETE implies WRITE implies READ."""
    return PERMISSION_HIERARCHY[granted] >= PERMISSION_HIERARCHY[required]
```

### Engine Hook for Lifecycle Action
```python
# In engine_service.py, _advance_from_activity, after marking completed_activity COMPLETE:
current_at = activity_template_map.get(completed_activity.activity_template_id)
if current_at and getattr(current_at, 'lifecycle_action', None):
    try:
        from app.services import lifecycle_service
        await lifecycle_service.execute_lifecycle_action(
            db, workflow, current_at.lifecycle_action, user_id
        )
    except Exception:
        logger.warning(
            "Lifecycle action failed for activity %s, continuing advancement",
            completed_activity.id,
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded permission checks in each route | Dependency injection (require_permission) | Standard FastAPI pattern | Centralized, consistent enforcement |
| PostgreSQL RLS (row-level security) | Application-level ACL table | N/A | SQLite test compatibility requirement makes RLS impossible |
| Separate state machine library (transitions, python-statemachine) | Set-of-tuples in-code | Project convention from Phase 4 | Zero dependencies, proven pattern |

**Note on PostgreSQL RLS:** The CLAUDE.md specifies dialect-agnostic models (SQLite for tests). PostgreSQL RLS would be ideal for ACL enforcement but is incompatible with the SQLite test strategy. Application-level ACL checks are the correct approach for this project.

## Open Questions

1. **ACL for workflows (not just documents)**
   - What we know: ACL-01 says "Objects (documents, workflows) have ACLs"
   - What's unclear: Should workflow ACL be built in this phase or deferred?
   - Recommendation: Focus on documents only in this phase. Workflow ACL is not required by any LIFE-xx or ACL-xx requirement except the generic ACL-01. If needed, it can be added in Phase 10 (Workflow Management).

2. **ACL fallback when no entries exist**
   - What we know: Existing documents have no ACL entries. New permission checks could block all access.
   - What's unclear: Should "no ACL entries" mean "full access" or "creator only"?
   - Recommendation: "No ACL entries" = full access for any authenticated user (backward compatible). Once the first ACL entry is created for a document, enforcement begins. Document upload always creates an ADMIN ACL entry for the creator.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | pyproject.toml (or pytest.ini if present) |
| Quick run command | `python -m pytest tests/test_lifecycle.py tests/test_acl.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIFE-01 | Document transitions through DRAFT/REVIEW/APPROVED/ARCHIVED with enforcement | unit + integration | `python -m pytest tests/test_lifecycle.py::test_valid_transitions -x` | Wave 0 |
| LIFE-02 | Activity completion auto-triggers lifecycle transition via lifecycle_action | integration | `python -m pytest tests/test_lifecycle.py::test_workflow_triggered_transition -x` | Wave 0 |
| LIFE-03 | Lifecycle changes create audit records | integration | `python -m pytest tests/test_lifecycle.py::test_lifecycle_audit_trail -x` | Wave 0 |
| LIFE-04 | ACL permissions change automatically on lifecycle transition | integration | `python -m pytest tests/test_lifecycle.py::test_lifecycle_acl_rules_applied -x` | Wave 0 |
| ACL-01 | Documents have ACLs defining read/write/delete access | unit + integration | `python -m pytest tests/test_acl.py::test_acl_crud -x` | Wave 0 |
| ACL-02 | Workflow activities modify document ACLs via lifecycle | integration | `python -m pytest tests/test_acl.py::test_workflow_acl_modification -x` | Wave 0 |
| ACL-03 | ACL changes recorded in audit trail | integration | `python -m pytest tests/test_acl.py::test_acl_audit_trail -x` | Wave 0 |
| ACL-04 | Permission checks enforced on all document API operations | integration | `python -m pytest tests/test_acl.py::test_permission_enforcement -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_lifecycle.py tests/test_acl.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_lifecycle.py` -- covers LIFE-01 through LIFE-04
- [ ] `tests/test_acl.py` -- covers ACL-01 through ACL-04

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/app/services/engine_service.py` -- transition set pattern, advancement loop, hook points
- Existing codebase: `src/app/models/workflow.py` -- ActivityTemplate model, WorkflowPackage relationship
- Existing codebase: `src/app/models/document.py` -- Document model to extend
- Existing codebase: `src/app/core/dependencies.py` -- FastAPI dependency injection pattern
- Existing codebase: `src/app/services/audit_service.py` -- Audit record creation pattern
- Existing codebase: `src/app/models/enums.py` -- Enum naming convention (lowercase)
- CONTEXT.md decisions D-01 through D-11 -- locked implementation decisions

### Secondary (MEDIUM confidence)
- FastAPI dependency injection docs -- parameterized dependencies pattern (require_permission factory)
- SQLAlchemy enum handling -- reuse existing Enum() with name= parameter pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, uses existing project patterns exclusively
- Architecture: HIGH -- every pattern maps to an existing codebase equivalent (transitions, dependencies, audit)
- Pitfalls: HIGH -- based on direct code analysis of hook points, import patterns, and test infrastructure

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable -- no external dependencies to change)
