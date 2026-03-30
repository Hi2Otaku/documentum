# Phase 1: Foundation & User Management - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Docker Compose stack (FastAPI, PostgreSQL, Redis, MinIO, Celery workers), database schema for Documentum's 5 core object types (Process, Activity, Flow, Package, WorkItem), user/group/role management with authentication, and cross-cutting audit trail baked in from day one.

</domain>

<decisions>
## Implementation Decisions

### Data Model Strategy
- **D-01:** Template + Instance split — separate tables for design-time (process_templates, activity_templates) and runtime (workflow_instances, activity_instances, work_items). Mirrors Documentum's dm_process vs dm_workflow.
- **D-02:** Copy-on-write template versioning — installing creates a frozen snapshot row. Edits create a new row with incremented version. Running instances reference the snapshot they started with.
- **D-03:** Flows stored as a junction table — a 'flows' table with source_activity_id, target_activity_id, flow_type (normal/reject), and condition expression. Standard relational approach.
- **D-04:** Process variables use typed columns table — a 'process_variables' table with name, type, and separate value columns (string_value, int_value, bool_value, date_value). Type-safe queries.
- **D-05:** Workflow packages as many-to-many junction — a 'workflow_packages' junction table linking workflow instances to documents, with package_name and activity-level tracking.
- **D-06:** Soft deletes everywhere — is_deleted flag on all tables. Preserves audit trail integrity and enables recovery.
- **D-07:** UUID primary keys on all tables.
- **D-08:** UTC timestamps everywhere — frontend converts to local time for display.
- **D-09:** Alembic for database migrations.
- **D-10:** Common base model — all SQLAlchemy models inherit from a base with id (UUID), created_at, updated_at, created_by, is_deleted.
- **D-11:** PostgreSQL native ENUMs for workflow states, activity types, flow types.

### Auth & Sessions
- **D-12:** JWT stateless authentication — no server-side session storage. Token contains user info.
- **D-13:** bcrypt for password hashing.
- **D-14:** Admin user seeded on first startup from environment variables.

### Audit Trail Design
- **D-15:** Audit records created via middleware/decorator — automatic capture on all API endpoints, including background tasks.
- **D-16:** Full before/after state — store complete object state (as JSON) before and after each change. Enables diff views.
- **D-17:** Single audit_log table — entity_type, entity_id, action, user_id, timestamp, before_state (JSONB), after_state (JSONB). Simpler cross-entity queries.

### API Conventions
- **D-18:** Versioned URL prefix — /api/v1/workflows, /api/v1/documents, /api/v1/users.
- **D-19:** Envelope response format — all responses wrapped: {"data": {...}, "meta": {...}, "errors": [...]}.
- **D-20:** Offset-based pagination — ?page=2&page_size=20.

### Claude's Discretion
- JWT expiry duration and refresh strategy
- Exact Docker Compose service configuration and networking
- FastAPI project structure (routers, services, models organization)
- Redis usage pattern (caching, Celery broker, or both)
- Exact base model implementation details

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above and in:
- `.planning/PROJECT.md` — Project vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` — FOUND-01..03, USER-01..04, AUDIT-01..04
- `.planning/research/STACK.md` — Technology stack with versions and rationale
- `.planning/research/ARCHITECTURE.md` — Component boundaries and data flow
- `.planning/research/PITFALLS.md` — Critical pitfalls for schema design and audit trail

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None — patterns will be established in this phase

### Integration Points
- Docker Compose will be the entry point for all services
- FastAPI app will be the API gateway
- PostgreSQL will be the single source of truth
- Redis will serve as Celery broker
- MinIO will serve as document storage (Phase 2 will connect)

</code_context>

<specifics>
## Specific Ideas

- Documentum's 5 core object types (dm_process, dm_activity, flow links, dmi_package, dmi_workitem) should be recognizable in the schema — use naming that maps back to the spec
- The audit trail is a compliance feature — it must be append-only and capture every mutation from the start

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-user-management*
*Context gathered: 2026-03-30*
