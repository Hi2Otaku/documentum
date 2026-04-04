# Phase 10: Delegation, Work Queues & Workflow Management - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can delegate tasks when unavailable, shared work queues allow any qualified user to claim tasks, and admins can halt, resume, abort, and restart workflow instances. Plus admin can view all running workflows and query the audit trail.

</domain>

<decisions>
## Implementation Decisions

### Delegation Model
- **D-01:** Toggle + single delegate — User sets `is_available=false` and designates one delegate user via `PUT /api/v1/users/me/availability`. New work items auto-route to the delegate. Existing items stay with the original user. Toggle back when available.
- **D-02:** Add `is_available` (boolean, default true) and `delegate_id` (nullable FK to users) fields on the User model.
- **D-03:** Engine's performer resolution checks availability before assigning work items. If user is unavailable and has a delegate, the work item goes to the delegate instead. Audit trail logs "delegated from X to Y".

### Work Queue Design
- **D-04:** New `WorkQueue` model with id, name, description, created_at. Many-to-many `WorkQueueMember` join table (queue_id, user_id) for qualified members.
- **D-05:** New `PerformerType.QUEUE` enum value. When an activity's performer_type is QUEUE, performer_id references the queue. Engine creates ONE shared work item visible to all queue members.
- **D-06:** Claim via existing `POST /inbox/{id}/acquire` — locks item to claiming user. Release via `POST /inbox/{id}/release`. Prevents double-work.
- **D-07:** Queue CRUD endpoints: `POST/GET/PUT/DELETE /api/v1/queues/`, with member management (`POST/DELETE /api/v1/queues/{id}/members`). Admin-only.

### Admin Workflow Control
- **D-08:** Action endpoints on workflow resource:
  - `POST /api/v1/workflows/{id}/halt` — RUNNING → HALTED, active work items become SUSPENDED
  - `POST /api/v1/workflows/{id}/resume` — HALTED → RUNNING, suspended items become AVAILABLE
  - `POST /api/v1/workflows/{id}/abort` — RUNNING|HALTED → FAILED, all items cancelled
  - `POST /api/v1/workflows/{id}/restart` — FAILED → DORMANT, clears state for re-start
- **D-09:** Each operation validates current state, transitions atomically, and logs to audit trail. Admin-only (superuser check).
- **D-10:** Filtered workflow list: `GET /api/v1/workflows/` with query params: state, template_id, created_by, date range. Returns paginated list with current state, active activities, started_at/started_by. Admin-only.

### Audit Trail Query Interface
- **D-11:** `GET /api/v1/audit/` with query params: user_id, workflow_id, document_id, action_type, date_from, date_to. Paginated. Returns audit records with full details (action, entity_type, entity_id, user, details JSON, timestamp). Admin-only.

### Claude's Discretion
- WorkQueue model details (additional fields if needed)
- SUSPENDED work item state implementation (new enum value vs reuse existing)
- Restart behavior details (what gets cleared, whether to preserve variables)
- Inbox query modifications for queue-based items (how queue members see shared items)
- Alembic migration strategy for new models/fields

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — USER-05, INBOX-08, QUEUE-01 through QUEUE-04, MGMT-01 through MGMT-05, AUDIT-05

### Existing Code (must read before implementing)
- `src/app/models/user.py` — User model (add is_available, delegate_id fields)
- `src/app/models/enums.py` — PerformerType (add QUEUE), WorkflowState (HALTED exists), WorkItemState
- `src/app/services/engine_service.py` — Performer resolution, state machine transitions (RUNNING↔HALTED already defined)
- `src/app/services/inbox_service.py` — Acquire/release work items (reuse for queue claim)
- `src/app/services/audit_service.py` — Audit trail recording
- `src/app/models/audit.py` — AuditLog model
- `src/app/routers/workflows.py` — Existing workflow endpoints (add halt/resume/abort/restart/list)
- `src/app/routers/inbox.py` — Existing inbox endpoints
- `src/app/schemas/common.py` — EnvelopeResponse, PaginationMeta patterns

### Prior Phase Context
- `.planning/phases/05-work-items-inbox/05-CONTEXT.md` — Work item lifecycle, acquire/release pattern (D-08, D-09)
- `.planning/phases/04-process-engine-core/04-CONTEXT.md` — State machine, engine advancement

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `inbox_service.py` acquire/release pattern — direct reuse for queue claim/release
- `audit_service.py` — already records all mutations, reuse for delegation/queue/admin actions
- State machine in `engine_service.py` — RUNNING↔HALTED transitions already defined

### Established Patterns
- Service layer pattern for all business logic
- EnvelopeResponse wrapping with PaginationMeta
- Admin-only via `is_superuser` check on current_user dependency
- Alembic migrations for schema changes

### Integration Points
- Engine performer resolution must be updated for QUEUE type and delegation
- Inbox queries must include queue-based items (items where performer is a queue the user belongs to)
- Workflow router gets 4 new action endpoints + list enhancement

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-delegation-work-queues-workflow-management*
*Context gathered: 2026-04-04*
