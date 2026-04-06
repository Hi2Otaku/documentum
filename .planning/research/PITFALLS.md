# Pitfalls Research

**Domain:** Adding timer activities, sub-workflows, event-driven activities, notifications, document renditions, virtual documents, retention policies, and digital signatures to an existing Documentum Workflow Clone (v1.2)
**Researched:** 2026-04-06
**Confidence:** HIGH (based on existing codebase analysis + verified patterns from production workflow engines)

**Context:** The existing system already has a working token-based Petri-net execution engine (`engine_service.py` with `WORKFLOW_TRANSITIONS`, `ACTIVITY_TRANSITIONS`, `WORK_ITEM_TRANSITIONS`), Celery with Redis broker (`celery_app.py` with `task_acks_late=True`), PostgreSQL with SQLAlchemy async, MinIO for document storage, and a full React/TypeScript frontend with React Flow workflow designer. These pitfalls are specific to ADDING v1.2 features to this existing foundation.

---

## Critical Pitfalls

### Pitfall 1: Individual Delayed Celery Tasks for Timers Silently Vanish on Restart

**What goes wrong:**
Using `task.apply_async(eta=deadline)` to schedule one Celery task per work item deadline. When the Celery worker restarts (deploy, crash, OOM, scaling), all pending ETA tasks are lost silently. No deadlines fire. No one notices until users complain about missing escalations days later.

**Why it happens:**
It feels natural -- "this work item is due in 48 hours, schedule a task for 48 hours from now." This is simpler than building a polling system. But Celery ETA tasks are stored in the broker (Redis), and depending on Redis persistence settings and worker visibility timeout configuration, they can be lost on restart. Even when they survive, they cannot be queried ("what deadlines are pending?"), cannot be easily cancelled, and cannot be modified.

**How to avoid:**
- Use the Celery Beat polling pattern already established by `poll_auto_activities` in `celery_app.py`. A periodic task (every 30s) queries the database: `WHERE state = 'active' AND timer_deadline < NOW() AND timer_fired = False`. This is idempotent, survives restarts, and is queryable.
- Alternatively, use RedBeat (Redis-backed dynamic scheduler) for per-activity-instance timer schedules. RedBeat stores schedules in Redis sorted sets with persistence and supports runtime CRUD. Since Redis is already the Celery broker, no new infrastructure is needed. Configure: `celery_app.conf.beat_scheduler = 'redbeat.RedBeatScheduler'`.
- Store timer metadata on the database model (new columns on `ActivityInstance` or a new `ActivityTimer` table): `timer_deadline`, `timer_type` (escalation, auto-complete, reminder), `timer_fired` boolean. The database is the source of truth; Redis/Beat is the scheduling mechanism.
- Every timer task must include a guard clause: verify `ActivityInstance.state == ACTIVE` and `WorkflowInstance.state == RUNNING` before acting. This makes stale timers harmless no-ops.
- Implement `cancel_timer(activity_instance_id)` and call it from EVERY code path that ends an activity: completion in `advance_workflow`, rejection handling, workflow halt, workflow failure, and AND-join token consumption that deactivates losing parallel branches.

**Warning signs:**
- Calling `.apply_async(eta=...)` for deadline/escalation logic anywhere in the codebase
- Escalation actions not firing after worker restarts
- No database table or column tracking pending timer state

**Phase to address:**
Timer Activities -- timer persistence design must be the first decision, before any escalation logic.

---

### Pitfall 2: Sub-Workflow Recursion Creating Infinite Workflow Cascades

**What goes wrong:**
A process template includes a SUB_WORKFLOW activity referencing another template, which itself contains a SUB_WORKFLOW activity pointing back to the first template (or to itself). Starting the workflow creates an infinite cascade of child workflows until database connections, memory, and the Celery task queue are exhausted.

**Why it happens:**
Template designers do not realize they created a cycle. The system has no guard at design time or runtime. With the current `ProcessTemplate` -> `ActivityTemplate` structure, there is no column linking an activity to a child template, so this relationship is invisible to validation logic.

**How to avoid:**
- At template validation/installation time: build a directed graph of template-to-template references via SUB_WORKFLOW activities. Detect cycles using DFS. Reject installation if a cycle exists.
- At runtime: track spawn depth. Add a `depth` field to `WorkflowInstance` (or pass it via process variables). Before spawning a child, check `depth < MAX_DEPTH` (5 is reasonable). Reject with an error if exceeded.
- Add `parent_workflow_id` (nullable FK to `workflow_instances.id`) and `spawning_activity_instance_id` (nullable FK to `activity_instances.id`) to `WorkflowInstance` via Alembic migration.
- Monitor: alert if any single root workflow has more than 20 descendant sub-workflows.

**Warning signs:**
- Database connection pool exhaustion shortly after starting a specific workflow template
- Rapid growth of rows in `workflow_instances` table
- Celery task queue depth spiking after a single workflow start

**Phase to address:**
Sub-Workflows -- depth tracking and cycle detection must be part of the initial schema migration.

---

### Pitfall 3: Sub-Workflow Lifecycle Coupling Creates Orphaned or Zombie Workflows

**What goes wrong:**
A parent workflow spawns a child and waits. If the parent is halted by a supervisor, the child keeps running and generating work items. Or the child fails, but the parent activity never gets notified and hangs in `ACTIVE` state forever. Completing a child might try to advance a parent that was already halted, causing an `Invalid state transition` error from `_enforce_activity_transition`.

**Why it happens:**
The current `WorkflowInstance` model has no parent-child relationship. The `WORKFLOW_TRANSITIONS` set in `engine_service.py` only governs individual workflow state machines with no cascade semantics. The `advance_workflow` function has no concept of "this workflow has a parent that needs to be notified."

**How to avoid:**
- Define explicit cascading rules in `engine_service.py`:
  - Halting a parent MUST recursively halt all children via their `parent_workflow_id` chain.
  - Failing a parent MUST fail all running children.
  - Completing a child should advance the parent's spawning activity (load via `spawning_activity_instance_id`, call `complete_activity`). But first check the parent workflow's state -- if it is `HALTED` or `FAILED`, the child completion is a graceful no-op.
  - Child failure should transition the parent's spawning activity to `ERROR` (this transition exists in `ACTIVITY_TRANSITIONS`).
- Use a callback pattern, not polling: when `advance_workflow` finishes a `WorkflowInstance` that has `parent_workflow_id`, it loads the parent activity and calls the advancement logic. This avoids periodic polling overhead.
- Test the full matrix: parent halt while child running, child fail while parent waiting, child complete while parent halted, nested sub-workflows (grandchild cascading).

**Warning signs:**
- `WorkflowInstance` records stuck in `RUNNING` with all `ActivityInstance` records `COMPLETE` (parent waiting for a dead child)
- Work items appearing in inboxes for workflows whose parent was halted
- `ActivityInstance` records in `ACTIVE` state with no `WorkItem` records and no running child workflow

**Phase to address:**
Sub-Workflows -- requires engine_service changes as part of the core sub-workflow implementation.

---

### Pitfall 4: Event-Driven Activities Racing on Concurrent Event Delivery

**What goes wrong:**
Two events arrive simultaneously that both match the same EVENT activity subscription. Both Celery workers try to complete the activity and advance the workflow. This causes either duplicate advancement (two downstream activities created) or integrity errors from attempting invalid state transitions.

**Why it happens:**
Without row-level locking, concurrent event handlers both read the activity as `ACTIVE`, both call `complete_activity`, and both succeed before either commits. The token-based engine creates duplicate `ExecutionToken` entries, causing duplicate downstream activations.

**How to avoid:**
- Use `SELECT ... FOR UPDATE SKIP LOCKED` when checking if an EVENT activity is still `ACTIVE` before completing it. This pattern is already used in `poll_auto_activities` for auto activities -- apply the same pattern to event-driven activities.
- Make all activity completion handlers idempotent: if the activity is already `COMPLETE`, return early without error.
- Process events through a single Celery queue with concurrency=1 per workflow instance (using task routing by workflow_instance_id). This serializes event processing per instance while allowing parallelism across instances.

**Warning signs:**
- Duplicate work items for the same activity in the same workflow
- Activity `COMPLETE` transition appearing twice in audit log
- More `ExecutionToken` entries than expected for a given workflow instance

**Phase to address:**
Event-Driven Activities -- locking strategy must be part of the event handler implementation.

---

### Pitfall 5: Digital Signature Linked to Document Instead of DocumentVersion

**What goes wrong:**
A digital signature is created by hashing the document content, but the signature record references `Document.id` (mutable -- always points to latest version) instead of `DocumentVersion.id` (immutable snapshot). When a new version is uploaded, the hash no longer matches. Verification fails on a legitimately signed document.

**Why it happens:**
The `Document` model is the primary entity in the API (`/documents/{id}`). Developers naturally link the signature to it. But `Document.current_major_version` and `current_minor_version` change with every check-in, so the document-level reference is unstable.

**How to avoid:**
- Signatures MUST be linked to `DocumentVersion.id`, not `Document.id`. The `DocumentVersion.minio_object_key` is immutable once created (contains a UUID path segment). The `content_hash` on `DocumentVersion` already captures the exact content hash.
- Create a `DocumentSignature` model: `version_id` (FK to `document_versions.id`), `signer_id` (FK to `users.id`), `signature_data` (binary/base64), `algorithm` (e.g., "RSA-SHA256"), `certificate_fingerprint`, `signed_at`.
- Once signed, the `DocumentVersion` must be immutable. Add `is_signed` boolean to `DocumentVersion`. Check-in and metadata update endpoints must reject modifications to signed versions (409 Conflict).
- For PDF documents, use PAdES format via the `endesive` library. For non-PDF files, use PKCS#7/CMS detached signatures via the `cryptography` library. The signing service must dispatch based on `content_type`.
- Hash computation must stream from MinIO in chunks (`hashlib.update()` with 64KB chunks), never loading the entire file into memory.

**Warning signs:**
- Signature verification failures on documents that have not been re-signed
- `DocumentSignature` table having a `document_id` column instead of `version_id`
- Users able to modify documents after signing without the system detecting it

**Phase to address:**
Digital Signatures -- model design and immutability constraint must precede any signing logic.

---

### Pitfall 6: Event-Driven Activities Causing Infinite Loops via Circular Event Chains

**What goes wrong:**
An event-driven activity triggers on "document lifecycle state changed." The activity performs a lifecycle transition (using the existing `lifecycle_action` field on `ActivityTemplate`). This emits another "lifecycle state changed" event, re-triggering the activity. Even indirect chains (event A triggers activity that emits event B that triggers another activity that emits event A) can create storms that exhaust Celery workers.

**Why it happens:**
The current system has no event bus -- `create_audit_record` logs events but does not emit them for subscription. Adding event emission to existing mutation points means every lifecycle transition, document upload, and workflow state change becomes an event source. Without re-entrancy guards, handlers recursively trigger themselves.

**How to avoid:**
- Implement a correlation ID system: each event carries a `correlation_id` and a `chain_depth` counter. When an event handler emits a new event as a result of processing, it increments `chain_depth`. If `chain_depth > 5`, the event is logged but not processed.
- Add a `source_event_id` field to all emitted events. Event handlers check: "Was this event caused by my own execution?" If yes, skip.
- Persist all events to an `events` table BEFORE processing. Use the table as the source of truth. Structure: `id`, `event_type`, `payload` (JSONB), `emitted_at`, `processed_at` (nullable), `correlation_id`, `chain_depth`, `source_activity_instance_id`.
- Rate-limit event processing per workflow instance via Redis counter with TTL: max 10 events per minute per instance.
- ALL event processing must go through Celery, never synchronously in the FastAPI request path.

**Warning signs:**
- CPU spikes and Celery queue depth explosion after certain document operations
- The `events` table growing rapidly with similar event types within seconds
- Duplicate work items appearing for the same activity instance

**Phase to address:**
Event-Driven Activities -- circuit breakers must be part of the event bus design from day one. Do NOT build event emission first and add protections later.

---

## Moderate Pitfalls

### Pitfall 7: Notification Storm on Bulk Operations

**What goes wrong:**
Starting a workflow that fans out to 50 parallel activities, each creating work items. The notification service sends 50 emails synchronously, slowing the `start_workflow` call to 30+ seconds. Or a supervisor reassigns 50 tasks and generates 50 individual notifications.

**How to avoid:**
- ALL notification sending must go through Celery tasks, never inline in service functions.
- Implement a `notifications` table that buffers notification records. A periodic Celery Beat task (every 30-60s) processes the buffer and sends batched digests.
- Add deduplication: if the same user gets 5+ "task assigned" events within 60 seconds, consolidate into one message.
- Rate-limit per user: max 5 emails per minute, aggregate the rest into a digest.

**Phase to address:**
Notifications -- notification infrastructure (queue table, batching, preferences) must be built before any other phase starts sending notifications.

---

### Pitfall 8: Virtual Document Circular References Crash Rendering

**What goes wrong:**
Document A contains Document B, which contains Document A. The `resolve_tree()` function enters infinite recursion. API returns 500 or times out. Even without exact cycles, deep nesting (20+ levels) causes performance degradation.

**How to avoid:**
- Cycle detection at add-component time using PostgreSQL recursive CTE: `WITH RECURSIVE ancestors AS (SELECT parent_id FROM virtual_document_components WHERE child_id = :new_parent UNION ALL ...)`. Reject with 400 if adding the child would create a cycle.
- Set maximum nesting depth (10 levels). Reject deeper hierarchies.
- Track visited document IDs during tree resolution as a runtime safety net.
- Support two binding modes per component: "fixed version" (bind to specific `DocumentVersion.id`) and "floating latest" (resolve to latest at render time).

**Phase to address:**
Virtual Documents -- cycle detection is a schema-level constraint, not a UI concern.

---

### Pitfall 9: Retention Policy Deleting Documents Referenced by Active Workflows

**What goes wrong:**
A retention policy triggers disposition on a document in `lifecycle_state = ARCHIVED`. The document is also attached to a running workflow via `WorkflowPackage`. The retention job deletes it from MinIO. The next workflow activity fails with a 404 when loading the document package.

**How to avoid:**
- Implement a "legal hold" mechanism: documents referenced by `WorkflowPackage` where the `WorkflowInstance.state IN ('running', 'halted')` automatically have disposition blocked.
- Two-phase disposition: first mark (`disposition_status = PENDING`, `disposition_scheduled_at`), then hard delete after a 30-day grace period.
- Audit records must retain document metadata (title, version, content_hash) even after disposition. Never cascade-delete audit records.

**Phase to address:**
Retention Policies -- legal hold integration with `WorkflowPackage` must be designed before any disposition logic.

---

### Pitfall 10: Rendition Processing in API Worker Crashes the Server

**What goes wrong:**
Running LibreOffice headless conversion in the FastAPI process (synchronously or via `asyncio.to_thread`). LibreOffice uses 500MB+ RAM per conversion, blocks the event loop, and can segfault on malformed documents, crashing the entire API server.

**How to avoid:**
- ALWAYS dispatch rendition work to Celery via a dedicated queue (`-Q renditions`).
- Set `worker_max_tasks_per_child=20` on rendition workers to force process recycling (LibreOffice has known memory leaks).
- Set `worker_max_memory_per_child=512000` (512MB) as a safety net.
- Use subprocess isolation: `subprocess.run(["soffice", "--headless", "--convert-to", "pdf", ...], timeout=60)`. Kill on timeout.
- Set Celery concurrency to 1 for rendition workers (or use unique `--user-installation` paths) to avoid LibreOffice lock file conflicts when multiple instances share a profile directory.

**Warning signs:**
- `subprocess.run(["soffice", ...])` appearing in a router or service file (not a task)
- Worker processes growing to 1GB+ memory over time
- Docker containers being OOM-killed

**Phase to address:**
Renditions -- queue separation and worker limits must be configured before any conversion logic.

---

### Pitfall 11: Timer Configuration Lost on Template Versioning

**What goes wrong:**
A process template is versioned (new version created via the existing versioning system). Timer configurations on activities (deadline durations, escalation rules) are not copied to the new version because they live in new columns/tables that the versioning logic does not know about. New workflow instances start without timers.

**How to avoid:**
- The template versioning/deep-copy logic must be updated to include ALL new v1.2 fields: timer configs, event subscriptions, sub-workflow references, signature requirements, notification settings.
- Write a test that creates a template with all v1.2 features configured, versions it, and verifies the new version has identical configuration.

**Phase to address:**
Each v1.2 phase that adds template-level configuration -- but especially Timer Activities and Sub-Workflows. The versioning test should be written in the first phase and extended in each subsequent phase.

---

### Pitfall 12: Sub-Workflow Variable Mapping Type Mismatch

**What goes wrong:**
Parent workflow has an `int` process variable mapped to a child workflow's `string` variable. The value is passed without type conversion via `_set_variable_value`, causing silent data corruption or crashes in the child's expression evaluator (e.g., `"5000" > 1000` evaluates as string comparison).

**How to avoid:**
- Validate variable type compatibility at template design time (when configuring the SUB_WORKFLOW activity's variable mappings).
- At runtime, use `_set_variable_value` with explicit type coercion and raise an error if coercion fails.
- Include variable type information in the mapping: `{parent_var: "amount", child_var: "total", parent_type: "int", child_type: "int"}`.

**Phase to address:**
Sub-Workflows -- variable mapping validation must be part of template validation.

---

### Pitfall 13: Event Bus Message Loss During Worker Downtime

**What goes wrong:**
Redis pub/sub is fire-and-forget. If no subscriber is listening when an event is published, the event is permanently lost. Similarly, PostgreSQL LISTEN/NOTIFY drops notifications when no listener is connected. Event-driven activities miss their triggers.

**How to avoid:**
- Persist events to an `events` table BEFORE emitting via pub/sub. The table is the reliable delivery mechanism.
- Workers query `events WHERE processed_at IS NULL` on startup to catch missed events.
- Pub/sub serves as a "check the table now" signal, not as the payload delivery.
- If higher durability is needed later, migrate from pub/sub to Redis Streams (which support consumer groups and acknowledgment).

**Phase to address:**
Event-Driven Activities -- event persistence must be part of the event bus architecture.

---

### Pitfall 14: Retention Policy Bypassed by Soft Delete

**What goes wrong:**
The `is_deleted` soft delete pattern (if present on `Document`) makes a document invisible in the UI but does not trigger retention disposition. Or conversely, retention only guards against hard deletes, so soft-deleting a document under retention hold succeeds.

**How to avoid:**
- Retention checks must run on BOTH soft delete and hard delete operations.
- A document under legal hold cannot be soft-deleted or hard-deleted. Period.
- Soft-deleted documents that reach their retention eligibility date should still go through proper disposition (two-phase: mark, then purge).

**Phase to address:**
Retention Policies -- must integrate with the existing delete operations.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Individual `apply_async(eta=...)` for each timer | No new infrastructure needed | Silent timer loss on restart; unqueryable pending timers | Never -- use database-backed polling or RedBeat |
| Inline notification calls in service functions | Quick to implement | Scattered logic, no batching, API response time regression | Never -- always use notification queue |
| Same Celery worker pool for renditions and workflow tasks | Simpler Docker Compose (fewer services) | LibreOffice memory leaks crash workflow workers | Development only; split queues for staging/production |
| Polling for sub-workflow completion | Simpler than callback wiring | Wastes CPU; adds latency up to poll interval; poor scaling | Acceptable for MVP if poll interval 30s+ with plan to add callbacks |
| Signing document record instead of raw file content | Simpler -- just hash the DB row | Any metadata change invalidates signature | Never -- always sign MinIO content bytes |
| Skipping cycle detection on virtual doc assembly | Faster add-component API | Circular references crash rendering; hard to fix retroactively | Never |
| Events via pub/sub only (no persistence table) | Simpler architecture | Lost events during downtime; untraceable event history | Never -- always persist to table first |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| RedBeat + existing `celery_app.py` | Running both RedBeat scheduler and default Beat simultaneously, causing duplicate execution of `poll-auto-activities` and `aggregate-dashboard-metrics` | Replace scheduler entirely: `celery_app.conf.beat_scheduler = 'redbeat.RedBeatScheduler'`. Static schedules from `beat_schedule` dict are still honored by RedBeat. |
| LibreOffice headless + Docker Compose | Installing LibreOffice in the main API container, bloating it from ~200MB to 1.2GB+ | Create a separate `rendition-worker` service in `docker-compose.yml` with LibreOffice. Only rendition Celery workers run there. Main API container stays lean. |
| SMTP email + async FastAPI | Using synchronous `smtplib` in async handlers, blocking the uvicorn event loop | Never send email from the API process. Dispatch a Celery task. The Celery worker (sync) can safely use `smtplib`. |
| Digital signatures + MinIO object keys | Signing based on MinIO versionId which changes on bucket versioning operations | Pin signatures to `DocumentVersion.minio_object_key` (contains UUID, immutable by construction) and `DocumentVersion.content_hash`. Do not depend on MinIO's internal versioning. |
| PostgreSQL LISTEN/NOTIFY for events | Using it as sole event transport; events lost when no listener connected | Use as real-time "check now" signal only. Persist events to `events` table. Workers catch up from table on reconnect. |
| `endesive` library for PDF signing | Assuming it handles all document types | `endesive` is PDF-specific (PAdES). Non-PDF files need PKCS#7/CMS via `cryptography` library. Route based on `DocumentVersion.content_type`. |
| Retention + audit trail | Cascade-deleting audit records when document is disposed | Audit records must NEVER be deleted by retention. Store document metadata snapshot in `after_state` JSON. The audit record survives the document. |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Recursive CTE for virtual document tree on every view | Document detail API > 500ms for deep hierarchies | Materialize resolved tree as JSONB on parent Document row; invalidate on component change; cache in Redis with 5min TTL | 50+ components, 5+ nesting levels |
| Full table scan for retention-eligible documents | Retention task takes minutes, locks rows | Add indexed `retention_eligible_at` column, set on lifecycle transition. Query only eligible rows. | 10K+ documents |
| Loading full file into memory for signature hashing | Memory spikes to 500MB+ for large files | Stream from MinIO with chunked reads; `hashlib.update()` in 64KB chunks | Documents > 50MB |
| Individual Celery task per notification | Queue depth spikes to hundreds on bulk ops | Buffer in database table; process in batches of 50-100 per task | Any parallel split with 10+ branches |
| Timer poll scanning all active workflows | Database load grows linearly with active workflow count | Use RedBeat sorted-set (fires at exact due time) or add index on `(state, timer_deadline)` for efficient poll queries | 500+ active workflows with timers |
| Event handlers querying full context on each event | Connection pool exhaustion under event storms | Include essential context in event payload JSONB; only query DB when needed | 100+ events/minute |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing private signing keys in database or plaintext env vars | Key compromise = forged signatures on any document | Store keys encrypted at rest. For internal use, generate a project CA with `cryptography` library; encrypt CA key with passphrase from env var. Never commit keys to git. |
| Retention policy CRUD without elevated authorization | Unauthorized users could disable retention or accelerate disposal | Require `PermissionLevel.ADMIN` for all retention management. Audit-log every retention action. |
| Notification emails containing sensitive workflow data | Email is not encrypted in transit; decisions and document titles visible to email infrastructure | Notifications contain minimal info ("You have a new task") with a link. Sensitive details visible only after login. |
| Event-driven activities executing with system permissions | Privilege escalation: low-privilege user action triggers high-privilege workflow activity | Event payloads must capture triggering user ID. Activities execute with configured performer's permissions, not event emitter's. |
| Signature verification skipping certificate chain validation | Accepting self-signed or expired certificates as valid | Validate full certificate chain. For internal CA, maintain a CRL. Handle cert-expired-after-signing gracefully (signature valid if cert was valid at signing time). |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| "Signature valid" without context | Users trust checkmark on v1.0 without knowing v2.0 exists unsigned | Show: "Signed by [user] on [date] for version [X.Y]. Current version: [A.B]." Yellow warning if versions differ. |
| Virtual document flat list | Users cannot understand nesting or binding modes | Tree view (expandable/collapsible) with binding mode labels (Fixed v1.2 / Floating latest) on each node |
| Silent timer escalation | User completes task 1 minute after escalation; sees priority changed without explanation | Show escalation history: "Escalated at [time] -- SLA deadline exceeded. Priority 5 -> 1." |
| No notification preferences | New users flooded or get nothing | Sensible defaults: in-app for all, email only for task_assigned and task_overdue. Preferences accessible from inbox page. |
| Invisible retention countdown | User archives document without realizing it starts a deletion countdown | Show on document detail: "Retention: [policy name]. Eligible for disposition on [date]." |
| Silent rendition failure | User expects PDF preview, sees blank space | Show status: "Generating PDF..." spinner. On failure: "PDF generation failed. [Retry]" button. |

## "Looks Done But Isn't" Checklist

- [ ] **Timer Activities:** Timer cancellation exists for ALL terminal paths -- verify timers cleaned up on completion, rejection, halt, failure, AND parallel branch cancellation
- [ ] **Timer Activities:** All timer deadlines use `datetime.now(timezone.utc)` -- verify no naive `datetime.now()` calls in timer logic
- [ ] **Timer Activities:** Timer tasks have guard clauses -- verify they check `ActivityInstance.state == ACTIVE` before acting
- [ ] **Sub-Workflows:** Cascade halt/fail implemented -- verify halting a parent halts all children; child failure notifies parent
- [ ] **Sub-Workflows:** "Parent already halted" guard -- verify child completion is a no-op when parent is in terminal state
- [ ] **Sub-Workflows:** Variable type validation -- verify mapping between parent and child variables checks type compatibility
- [ ] **Sub-Workflows:** Recursion depth limit -- verify max depth is enforced at both template validation and runtime
- [ ] **Event-Driven Activities:** Events persisted to table -- verify events survive worker downtime and are caught up on restart
- [ ] **Event-Driven Activities:** Re-entrancy guards -- verify circular event chains are detected and broken at configured depth
- [ ] **Event-Driven Activities:** Row-level locking -- verify `FOR UPDATE SKIP LOCKED` used when completing event-driven activities
- [ ] **Notifications:** Batching for bulk operations -- verify parallel split with 20 branches sends 1 digest, not 20 emails
- [ ] **Notifications:** Unsubscribe works per-type -- verify users can disable specific notification types independently
- [ ] **Renditions:** Separate Celery queue -- verify rendition tasks run on dedicated queue, not default queue with workflow tasks
- [ ] **Renditions:** Worker memory limits -- verify `max_tasks_per_child` and `max_memory_per_child` configured for rendition workers
- [ ] **Renditions:** Failure visible in UI -- verify failed renditions show error state and retry button
- [ ] **Renditions:** Orphan cleanup -- verify deleting a `DocumentVersion` also deletes its renditions from MinIO
- [ ] **Virtual Documents:** Cycle detection at add time -- verify A->B->C->A rejected with 400 error at assembly time
- [ ] **Virtual Documents:** Permission propagation -- verify viewing a virtual document checks READ on ALL child components
- [ ] **Retention:** Legal hold for active workflows -- verify documents attached to RUNNING workflows cannot be disposed
- [ ] **Retention:** Audit trail preserved -- verify document disposition does not cascade-delete audit records
- [ ] **Retention:** Two-phase disposition -- verify soft-delete + grace period before permanent deletion
- [ ] **Digital Signatures:** Linked to DocumentVersion, not Document -- verify `DocumentSignature.version_id` FK exists
- [ ] **Digital Signatures:** Post-signing immutability -- verify signed version rejects check-in and metadata updates (409 Conflict)
- [ ] **Digital Signatures:** Content-only signing -- verify hash computed over MinIO file bytes via streaming, not over DB record
- [ ] **Template Versioning:** All v1.2 configs deep-copied -- verify template version includes timer configs, event subscriptions, sub-workflow refs, signature requirements

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Stale timer schedules firing | LOW | Query for timer entries (RedBeat or DB) where linked `ActivityInstance.state != 'active'`. Delete orphaned entries. Add guard clauses to prevent recurrence. |
| Zombie sub-workflows | MEDIUM | Query `WorkflowInstance WHERE parent_workflow_id IN (SELECT id FROM workflow_instances WHERE state IN ('finished','failed'))`. Halt zombies with audit trail entry. Add cascade logic. |
| Event storm (cascading loops) | HIGH | Kill Celery workers to stop processing. Purge event queue. Identify circular chain from `events` table (rapid same-type events with linked correlation_id). Add circuit breaker. Manually revert affected workflow instances using audit trail. |
| Notification flood | LOW | No data loss or corruption. Apologize. Add batching/deduplication. |
| Rendition worker OOM crash | LOW | Restart workers with `--max-tasks-per-child=20`. Reset `DocumentRendition` records stuck in PROCESSING to PENDING for re-queue. Originals safe in MinIO. |
| Invalid signatures from post-signing modification | HIGH | Identify affected: `DocumentSignature` joined to `DocumentVersion` where current `content_hash` differs from hash stored at signing. Re-sign with immutability controls. If legally binding, requires formal re-execution of signing workflow step. |
| Retention disposed documents still needed | CRITICAL | Restore from MinIO version history (if bucket versioning enabled) or from backup. If no backup, data is permanently lost. This is why two-phase disposition is mandatory. |
| Virtual document circular reference | MEDIUM | Query `virtual_document_components` for cycles via recursive CTE. Delete cycle-creating rows. Add cycle detection constraint. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Timer persistence (#1) | Timer Activities | Integration test: start workflow with timer, restart Celery workers, verify timer still fires on schedule |
| Sub-workflow recursion (#2) | Sub-Workflows | Integration test: create mutually-referencing templates, attempt installation -- verify rejected. Runtime test: verify depth limit stops spawning. |
| Sub-workflow lifecycle (#3) | Sub-Workflows | Integration test: halt parent with running child -- verify child halted. Fail child -- verify parent activity ERROR. Complete child after parent halted -- verify graceful no-op. |
| Event race conditions (#4) | Event-Driven Activities | Integration test: emit same event twice concurrently for same activity -- verify only one completion via FOR UPDATE SKIP LOCKED |
| Signature version binding (#5) | Digital Signatures | Integration test: sign version, upload new version, verify signature still validates against original version, not latest |
| Event infinite loops (#6) | Event-Driven Activities | Integration test: activity emits event that re-triggers itself -- verify circuit breaker stops at max chain depth |
| Notification flooding (#7) | Notifications | Load test: parallel split with 20 branches -- verify 1 batched notification, not 20 individual |
| Virtual doc cycles (#8) | Virtual Documents | Unit test: A->B->C->A assembly -- verify 400 error with "circular reference detected" |
| Retention vs. workflows (#9) | Retention Policies | Integration test: attach doc to running workflow, run disposition -- verify doc preserved with hold |
| Rendition in API (#10) | Renditions | Code review: verify no `subprocess.run(["soffice"...])` in router/service files. Only in Celery tasks. |
| Template versioning gap (#11) | First v1.2 phase (Timer Activities) | Test: create template with timer config, version it, verify new version has same timer config |
| Variable type mismatch (#12) | Sub-Workflows | Test: map int variable to string variable, attempt start -- verify type validation error or explicit coercion |
| Event message loss (#13) | Event-Driven Activities | Integration test: emit events while worker is stopped, start worker, verify all events processed from catch-up query |
| Retention bypass (#14) | Retention Policies | Test: attempt soft-delete on document under retention hold -- verify rejection |

## Sources

- Codebase analysis: `engine_service.py` state transition maps, `advance_workflow`, `_apply_delegation` -- HIGH confidence
- Codebase analysis: `celery_app.py` configuration (`task_acks_late`, `beat_schedule`) -- HIGH confidence
- Codebase analysis: `workflow.py` models (`ExecutionToken`, `WorkflowInstance`, `ActivityInstance`) -- HIGH confidence
- Codebase analysis: `document.py` models (`Document`, `DocumentVersion`, `content_hash`) -- HIGH confidence
- [Celery 5.6 Periodic Tasks Documentation](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html) -- HIGH confidence
- [Celery Workers Guide - Memory Management](https://docs.celeryq.dev/en/latest/userguide/workers.html) -- HIGH confidence
- [Celery Memory Leak Issue #4843](https://github.com/celery/celery/issues/4843) -- HIGH confidence
- [Celery Optimizing Guide](https://docs.celeryq.dev/en/stable/userguide/optimizing.html) -- HIGH confidence
- [RedBeat: Redis-backed Beat Scheduler](https://github.com/sibson/redbeat) -- HIGH confidence
- [Dynamic Task Scheduling in Celery Beat - Issue #3493](https://github.com/celery/celery/issues/3493) -- HIGH confidence
- [Celery Task Resilience: Advanced Strategies](https://blog.gitguardian.com/celery-tasks-retries-errors/) -- MEDIUM confidence
- [Temporal: Workflow Engine Design Principles](https://temporal.io/blog/workflow-engine-principles) -- HIGH confidence
- [Camunda Workflow Patterns](https://docs.camunda.io/docs/components/concepts/workflow-patterns/) -- HIGH confidence
- [Dapr Workflow Patterns](https://docs.dapr.io/developing-applications/building-blocks/workflow/workflow-patterns/) -- HIGH confidence
- [Orkes Conductor: Sub Workflow Reference](https://orkes.io/content/reference-docs/operators/sub-workflow) -- HIGH confidence
- [Event Sourcing Pattern - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing) -- HIGH confidence
- [Event Sourcing Pitfalls](https://sylhare.github.io/2022/07/22/Event-sourcing-pitfalls.html) -- MEDIUM confidence
- [Documentum Virtual Documents - ArgonDigital](https://argondigital.com/blog/ecm/virtual-documents/) -- MEDIUM confidence
- [endesive: Python Digital Signing Library (PyPI)](https://pypi.org/project/endesive/) -- HIGH confidence
- [LibreOffice Headless Memory Leak Investigation](https://ask.libreoffice.org/t/investigating-memory-leak-in-libreoffice-headless-conversion/111359) -- MEDIUM confidence
- [Document Retention Policy Best Practices](https://documentmanagementsoftware.com/document-retention-policy-best-practices/) -- MEDIUM confidence
- [Python Celery Kubernetes and Memory](https://dev.to/redhap/python-celery-kubernetes-and-memory-2old) -- MEDIUM confidence

---
*Pitfalls research for: Documentum Workflow Clone v1.2 -- Advanced Engine & Document Platform*
*Researched: 2026-04-06*
