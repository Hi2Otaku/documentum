# Phase 3: Workflow Template Design (API) - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can create complete workflow templates through the API — activities (manual/auto), flows (normal/reject), process variables, trigger conditions (AND/OR joins), conditional routing expressions, validation, installation, and versioning. Templates are the canonical schema consumed by both the Process Engine (Phase 4) and Visual Designer (Phase 8).

Requirements: TMPL-01 through TMPL-11.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

All implementation decisions are at Claude's discretion. User deferred all gray areas. Use established patterns from Phase 1/2 and these locked prior decisions as constraints:

**Locked from Phase 1:**
- Template + Instance split: separate `process_templates` / `activity_templates` tables from runtime instances (D-01)
- Copy-on-write versioning: installing creates frozen snapshot, edits create new version (D-02)
- Flows as junction table: source_activity_id, target_activity_id, flow_type (normal/reject), condition expression (D-03)
- Process variables: typed columns table with name, type, and separate value columns (D-04)
- PostgreSQL ENUMs for activity types (manual/auto), flow types (normal/reject), trigger types (AND/OR) (D-11)
- All standard patterns: UUID PKs, soft deletes, base model, audit on mutations, envelope responses, /api/v1/ prefix, offset pagination

**Recommended approaches (Claude to decide specifics):**
- Template API shape: single nested JSON for full template creation vs separate CRUD per sub-entity
- Validation rules: connectivity check, orphan detection, performer assignment validation, cycle detection
- Condition expressions: expression format for routing conditions (simple DSL, Python subset, JSON-based)
- Template state machine: Draft → Validated → Installed lifecycle

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above and in:
- `.planning/PROJECT.md` — Project vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` — TMPL-01 through TMPL-11
- `.planning/research/ARCHITECTURE.md` — Component boundaries and data flow
- `.planning/research/PITFALLS.md` — Template versioning pitfalls (critical)
- `.planning/phases/01-foundation-user-management/01-CONTEXT.md` — Data model decisions (D-01 through D-11)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/app/models/workflow.py` — Skeleton workflow models from Phase 1 (ProcessTemplate, ActivityTemplate, FlowTemplate, etc.)
- `src/app/models/base.py` — BaseModel with UUID, timestamps, soft delete
- `src/app/models/enums.py` — Existing enum definitions
- `src/app/services/audit_service.py` — create_audit_record for template mutations
- `src/app/schemas/common.py` — EnvelopeResponse, PaginatedResponse patterns
- `src/app/core/dependencies.py` — Auth dependencies (get_current_user, get_current_active_admin)

### Established Patterns
- Service layer: services handle business logic, routers handle HTTP
- Router registration in main.py
- Pydantic schemas for request/response validation
- Audit trail on every mutation
- Offset pagination with EnvelopeResponse wrapping

### Integration Points
- Template routers register at /api/v1/templates (or /api/v1/processes)
- Models extend existing workflow.py or create new template-specific files
- Process Engine (Phase 4) will consume installed templates
- Visual Designer (Phase 8) will CRUD templates through these endpoints

</code_context>

<specifics>
## Specific Ideas

- Templates should feel like Documentum's dm_process — a blueprint that can be instantiated multiple times
- The 5 Documentum object types (Process, Activity, Flow, Package, WorkItem) should be recognizable in the API

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-workflow-template-design-api*
*Context gathered: 2026-03-30*
