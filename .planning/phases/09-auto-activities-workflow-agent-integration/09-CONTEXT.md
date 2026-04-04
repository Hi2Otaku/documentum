# Phase 9: Auto Activities, Workflow Agent & Integration - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Automated activities execute server-side Python methods without human intervention, a Celery-based Workflow Agent continuously polls for and executes queued auto activities, and external systems can interact with workflows via REST API. This phase makes the engine capable of fully automated workflow steps.

</domain>

<decisions>
## Implementation Decisions

### Auto Activity Method Registry
- **D-01:** Decorator-based registry — methods decorated with `@auto_method('method_name')` are auto-discovered at startup. Method name stored in activity template's `method_name` field maps to the registered function.
- **D-02:** `ActivityContext` object passed to each method providing access to: process variables (read/write), attached documents, workflow instance, current activity, database session. Methods are async.
- **D-03:** Four built-in auto methods ship with v1:
  - `send_email` — Send notification email to a user/group (SMTP or log in dev mode)
  - `change_lifecycle_state` — Transition attached document lifecycle (e.g., Draft → Approved)
  - `modify_acl` — Add/remove ACL entries on attached documents
  - `call_external_api` — HTTP POST to external URL (reads URL from process variable, sends workflow context, stores response in process variable)

### Workflow Agent Execution Model
- **D-04:** Celery beat periodic task polling every 10 seconds. Scans for activity instances in RUNNING state with type=AUTO, dispatches each as an individual Celery task. Scales via worker count.
- **D-05:** Configurable timeout per method, default 60 seconds. Max 3 retries with exponential backoff (10s, 30s, 90s). After max retries, mark activity as FAILED and log error. Workflow halts at the failed activity.
- **D-06:** Create `celery_app` module (referenced in Docker Compose but not yet implemented). Configure Celery with Redis broker (already in Docker Compose).

### Admin Failure Management
- **D-07:** API endpoints only (no UI in this phase):
  - `POST /api/v1/workflows/{id}/activities/{id}/retry` — re-queues failed activity, resets retry count
  - `POST /api/v1/workflows/{id}/activities/{id}/skip` — marks activity COMPLETED, advances workflow, logs skip in audit trail
- **D-08:** Error details (exception message, traceback, attempt count, timestamps) stored in activity instance or a new execution log table. Visible via audit trail queries.

### External API Integration Scope
- **D-09:** INTG-02 and INTG-03 are already implemented — existing endpoints for starting workflows (`POST /api/v1/workflows/`) and completing/rejecting work items (`POST /inbox/{id}/complete`, `POST /inbox/{id}/reject`). No new REST endpoints needed.
- **D-10:** INTG-01 covered by the `call_external_api` built-in auto method. Reads target URL and payload template from process variables, sends HTTP POST with workflow context, stores response.
- **D-11:** No new authentication mechanism (API keys, etc.) — external systems use the existing JWT auth. Dedicated integration auth deferred to future phases.

### Claude's Discretion
- Celery task configuration details (queues, prefetch, acks_late)
- ActivityContext implementation details
- Email configuration approach (SMTP settings, dev mode logging)
- Execution log table schema vs storing in existing audit trail
- Auto method module organization (single file vs directory)
- How to prevent duplicate execution (idempotency/locking on poll)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — AUTO-01 through AUTO-05, INTG-01 through INTG-03

### Existing Code (must read before implementing)
- `src/app/models/enums.py` — ActivityType.AUTO enum already defined
- `src/app/models/workflow.py` — ActivityTemplate.method_name field, ActivityInstance model
- `src/app/services/engine_service.py` — Engine advancement logic, auto-completes start/end but skips AUTO activities (line ~444, ~508)
- `src/app/services/lifecycle_service.py` — Lifecycle transitions (reusable for change_lifecycle_state method)
- `src/app/services/acl_service.py` — ACL management (reusable for modify_acl method)
- `src/app/routers/workflows.py` — Existing start_workflow, complete_work_item endpoints
- `src/app/routers/inbox.py` — Existing complete/reject endpoints
- `docker-compose.yml` — Celery worker/beat services already defined (lines 70-91), reference `app.celery_app`

### Prior Phase Context
- `.planning/phases/04-process-engine-core/04-CONTEXT.md` — Engine decisions (synchronous advancement, token-based parallel, state machines)
- `.planning/phases/07-document-lifecycle-acl/07-CONTEXT.md` — Lifecycle and ACL integration patterns

### Tech Stack
- `CLAUDE.md` — Celery 5.6.x, Redis 7.x, redis-py 5.x

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lifecycle_service.py` — Direct reuse for `change_lifecycle_state` auto method
- `acl_service.py` — Direct reuse for `modify_acl` auto method
- `audit_service.py` — Audit logging for all auto activity executions
- `engine_service.py` — `complete_work_item` and `advance_workflow` for post-execution advancement

### Established Patterns
- Service layer pattern: all business logic in `src/app/services/`, routers are thin
- Async SQLAlchemy sessions via `get_db` dependency
- EnvelopeResponse wrapping on all API responses
- Audit trail on all mutations

### Integration Points
- Engine must be updated to detect AUTO activities and queue them instead of skipping
- Celery app module needs to be created at `src/app/celery_app.py` (Docker Compose already references it)
- Auto methods need database session access (Celery tasks run outside FastAPI request context)
- Redis already running in Docker Compose as Celery broker

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

*Phase: 09-auto-activities-workflow-agent-integration*
*Context gathered: 2026-04-04*
