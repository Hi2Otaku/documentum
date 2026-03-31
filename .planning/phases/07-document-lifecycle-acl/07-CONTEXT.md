# Phase 7: Document Lifecycle & ACL - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds document lifecycle state management (Draft/Review/Approved/Archived) with enforced transitions, workflow-triggered lifecycle actions, object-level ACL permissions that change automatically with lifecycle state, and permission checks on all document API operations. After this phase, documents have a complete state machine integrated with the workflow engine.

</domain>

<decisions>
## Implementation Decisions

### Lifecycle State Machine
- **D-01:** Fixed enum for lifecycle states: DRAFT, REVIEW, APPROVED, ARCHIVED. Not configurable per document type — matches Documentum spec directly.
- **D-02:** Valid transitions enforced via a transition map set (same pattern as WORKFLOW_TRANSITIONS and ACTIVITY_TRANSITIONS in engine_service.py). Set of (from_state, to_state) tuples.
- **D-03:** Transitions can be triggered both manually (dedicated API endpoint) and automatically (workflow activity completion). Both paths go through the same service function.
- **D-04:** Invalid transition attempts raise ValueError, log an audit record, and do not halt the workflow. Document stays in current state.

### ACL Permission Model
- **D-05:** ACL stored in a dedicated table: `document_acl` with columns (id, document_id, principal_id, principal_type [user/group], permission_level). Queryable and indexable.
- **D-06:** Four permission levels as enum: READ, WRITE, DELETE, ADMIN. ADMIN implies all others.
- **D-07:** Lifecycle-ACL rule table maps lifecycle state transitions to ACL changes. E.g., transition to APPROVED removes WRITE for non-admin users. Rules evaluated automatically on every lifecycle transition.
- **D-08:** Permission checks enforced via FastAPI dependency injection on all document routes. A `require_permission(document_id, level)` dependency that raises 403 on insufficient access.

### Workflow-Triggered Transitions
- **D-09:** New field on ActivityTemplate: `lifecycle_action` (nullable string). Format: "transition_to:{state}" (e.g., "transition_to:approved"). When activity completes, engine checks this field and triggers the transition if present.
- **D-10:** Lifecycle action affects ALL documents in the workflow package — consistent with Documentum's model where the entire package moves through states together.
- **D-11:** Lifecycle transition fires on activity completion, after work item is completed but before advancing to the next activity. This ensures the document state is correct before downstream activities see it.

### Claude's Discretion
- Default ACL rules for each lifecycle state (what permissions are set on document creation, what changes per transition)
- Whether to add a `lifecycle_state` field directly on Document model or in a separate LifecycleState table
- Migration strategy for existing documents (default to DRAFT state)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code
- `src/app/services/engine_service.py` — WORKFLOW_TRANSITIONS pattern to replicate for lifecycle, activity completion hook point for lifecycle_action
- `src/app/models/workflow.py` — ActivityTemplate model where lifecycle_action field will be added
- `src/app/models/document.py` — Document model to extend with lifecycle_state
- `src/app/services/document_service.py` — Document CRUD to add permission checks
- `src/app/routers/documents.py` — Routes to protect with ACL dependency
- `src/app/services/audit_service.py` — Audit trail integration for lifecycle and ACL changes

### Spec Reference
- `documentum-workflow-management.docx` — Lifecycle management and ACL patterns from Documentum spec

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- WORKFLOW_TRANSITIONS / ACTIVITY_TRANSITIONS pattern — exact same set-of-tuples approach for lifecycle transitions
- `create_audit_record` function — reuse for lifecycle and ACL audit logging
- FastAPI dependency injection pattern from auth (get_current_user) — extend for permission checks

### Established Patterns
- Service layer pattern: routers -> services -> models with audit
- Enum-based state tracking (WorkflowState, ActivityState, WorkItemState)
- Transition enforcement via set lookup

### Integration Points
- `engine_service._advance_from_activity()` — hook point for lifecycle_action trigger
- Document routes — add permission dependency
- WorkflowPackage — link between workflows and documents for bulk lifecycle operations

</code_context>

<specifics>
## Specific Ideas

- Lifecycle-ACL rules should be seed data, not hardcoded — makes it possible to adjust rules without code changes
- Permission check should be a reusable dependency, not per-route logic

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-document-lifecycle-acl*
*Context gathered: 2026-03-31*
