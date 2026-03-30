# Phase 4: Process Engine Core - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

The process engine can start workflow instances from installed templates and automatically advance them through sequential and parallel paths, creating work items for manual activities. Covers EXEC-01 through EXEC-07, EXEC-12, EXEC-13, EXEC-14.

NOT in scope: conditional routing (performer-chosen, condition-based, broadcast), reject flows, alias sets, auto activity execution, admin workflow management, delegation. Those are Phases 5, 6, 9, 10.

</domain>

<decisions>
## Implementation Decisions

### Execution Model
- **D-01:** Synchronous advancement — when a user completes a work item, the same API request evaluates flows and activates next activities. No Celery involvement in Phase 4.
- **D-02:** Token-based parallel tracking (Petri-net style) — each flow carries a token, AND-join fires when all incoming tokens arrive. Requires a flow_tokens/execution_tokens table.
- **D-03:** Iterative loop for chaining — after completing an activity, engine loops (evaluate next → if start/end activity, execute immediately → repeat) until hitting a manual activity or dead end. No recursion.

### Instance Startup
- **D-04:** Document attachment is optional at startup — packages can be attached later.
- **D-05:** Alias resolution deferred to Phase 6 — Phase 4 uses basic performer_id from template. Start API accepts optional performer overrides as a simple map.
- **D-06:** Immediate start — POST /workflows creates instance, sets Running, activates start activity, and advances to first real activity, all in one request.

### State Machine Rules
- **D-07:** Full ActivityState enum with enforced transitions — add ActivityState enum (Dormant, Active, Paused, Complete, Error) with valid transition enforcement. Alembic migration to convert existing string column.
- **D-08:** Auto-finish — engine detects End activity completion, marks workflow as Finished, records completed_at automatically.
- **D-09:** Model + basic enforcement for halt/resume — state transitions enforced (can't complete work item on halted workflow), but admin halt/resume endpoints are Phase 10 (MGMT-01/02).

### Condition Expressions
- **D-10:** Simple Python subset for routing conditions — expressions like `amount > 10000 and department == 'legal'`. Parsed with Python's ast module.
- **D-11:** AST whitelist sandbox — parse with ast.parse(), walk tree, allow only: comparisons, boolean ops, arithmetic, string literals, variable names. Reject function calls, attribute access, imports.

### Claude's Discretion
- Engine service structure (single engine_service.py vs split into engine + evaluator)
- Token table schema design
- Workflow start endpoint shape and validation
- How process variables are copied from template to instance at startup
- Test strategy and fixture design

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Project vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` — EXEC-01 through EXEC-14 (Phase 4 covers EXEC-01 to EXEC-07, EXEC-12 to EXEC-14)
- `.planning/ROADMAP.md` — Phase 4 goal and success criteria

### Architecture & Prior Decisions
- `.planning/research/ARCHITECTURE.md` — Component boundaries and data flow
- `.planning/research/PITFALLS.md` — Template versioning pitfalls
- `.planning/phases/01-foundation-user-management/01-CONTEXT.md` — Foundation data model decisions (D-01 through D-11)
- `.planning/phases/03-workflow-template-design-api/03-CONTEXT.md` — Template design decisions

### Existing Code (must read before implementing)
- `src/app/models/workflow.py` — All workflow models (templates + instances + work items)
- `src/app/models/enums.py` — WorkflowState, ActivityType, FlowType, TriggerType, WorkItemState, PerformerType
- `src/app/services/template_service.py` — Template CRUD patterns to follow
- `src/app/services/audit_service.py` — Audit trail integration pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/app/models/workflow.py` — WorkflowInstance, ActivityInstance, WorkItem, WorkflowPackage, ProcessVariable already defined as skeleton models
- `src/app/models/enums.py` — WorkflowState (Dormant/Running/Halted/Failed/Finished), WorkItemState, ActivityType already defined
- `src/app/models/base.py` — BaseModel with UUID, timestamps, soft delete
- `src/app/services/audit_service.py` — create_audit_record for workflow mutations
- `src/app/services/template_service.py` — Pattern for service layer (960 lines, 17 functions)
- `src/app/schemas/common.py` — EnvelopeResponse, PaginatedResponse
- `src/app/core/dependencies.py` — Auth dependencies

### Established Patterns
- Service layer: routers delegate to service functions, services handle business logic and audit
- Async SQLAlchemy with selectinload for relationship loading
- UUID PKs, soft deletes, audit on every mutation
- Pydantic schemas for all request/response validation
- EnvelopeResponse wrapping on all endpoints

### Integration Points
- Engine router registers at `/api/v1/workflows` in main.py
- Engine service reads installed ProcessTemplate + related ActivityTemplate/FlowTemplate
- Creates WorkflowInstance, ActivityInstance, WorkItem, WorkflowPackage records
- ProcessVariable copied from template defaults to instance scope
- WorkItem creation will be consumed by Phase 5 (inbox)

### Key Model Notes
- ActivityInstance.state is currently `String(50)` — needs migration to proper enum (D-07)
- ProcessVariable has dual FK (process_template_id OR workflow_instance_id) — template values serve as defaults, instance values are runtime
- WorkflowPackage.document_id references documents from Phase 2
- WorkItem.performer_id references users from Phase 1

</code_context>

<specifics>
## Specific Ideas

- Token-based execution gives Documentum-grade formal semantics — this is the right choice for an enterprise workflow engine clone
- The engine should feel like Documentum's Process Engine: a background runtime that advances workflows deterministically
- Start activity and End activity are special — they execute instantly (no work items), just advance the flow

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-process-engine-core*
*Context gathered: 2026-03-30*
