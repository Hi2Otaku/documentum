# Architecture Patterns

**Domain:** v1.2 Feature Integration -- Timer Activities, Sub-Workflows, Events, Notifications, Renditions, Virtual Documents, Retention, Digital Signatures
**Researched:** 2026-04-06

## Current Architecture Snapshot

The existing system follows a clean layered architecture:

```
React SPA (Vite + React 19)
    |
FastAPI (ASGI, async)
    |-- Routers (auth, users, documents, templates, workflows, inbox, dashboard, query, ...)
    |-- Services (engine_service, document_service, lifecycle_service, acl_service, ...)
    |-- Models (workflow.py, document.py, user.py, acl.py, audit.py)
    |
    +-- PostgreSQL 16 (asyncpg) -- primary data store
    +-- MinIO -- document file storage (single "documents" bucket)
    +-- Redis 7 -- Celery broker + cache
    +-- Celery Worker -- auto activity execution (polls every 10s)
    +-- Celery Beat -- periodic scheduling (auto-activity poll + metrics aggregation)
```

**Key Engine Pattern:** Token-based Petri-net execution in `engine_service.py` (~1100 lines). Activities are START/END/MANUAL/AUTO. The `_advance_from_activity` loop uses breadth-first iterative token placement with AND-join/OR-join semantics. Celery workers poll for ACTIVE AUTO activities and execute registered auto methods from the `auto_methods` registry.

**Key Engine Extension Points:**
- `_advance_from_activity` has a `match` on `ActivityType` (START/END, AUTO, MANUAL) -- new types slot in here
- `auto_methods/__init__.py` provides a `@auto_method("name")` decorator registry -- new methods register the same way
- `celery_app.py` beat_schedule dict -- new periodic tasks add entries here
- `BaseModel` provides soft delete (`is_deleted`), timestamps, `created_by` on all models

## New Features and Their Integration Points

### 1. Timer Activities and Escalation

**What it needs:** Activities that fire based on time (delays, deadlines, SLA triggers) rather than user action or auto-method completion.

**Integration approach:** Extend the existing Celery Beat + task system. Do NOT add a new activity type -- instead, add timer configuration to `ActivityTemplate` that applies to MANUAL activities (deadline/escalation) and can create pure delay nodes (AUTO activity with timer).

**New components:**
- `src/app/models/timer.py` -- `TimerConfig` model (one-to-many from ActivityTemplate)
  - Fields: `activity_template_id` (FK), `timer_type` (delay/deadline/recurring), `duration_seconds`, `deadline_expression` (evaluable against process variables), `escalation_action` (reassign/notify/auto_complete/bump_priority), `escalation_target` (user ID or variable name)
- `src/app/tasks/timer_tasks.py` -- Celery tasks for timer evaluation
  - `check_timer_deadlines` -- Beat task (runs every 30s), queries for ACTIVE activities with timer configs past deadline
  - `execute_timer_escalation` -- Handles the escalation action
- `src/app/services/timer_service.py` -- Timer scheduling and management logic

**Modifications to existing:**
- `ActivityTemplate` model: add `timer_config` JSON column (lightweight option) or FK relationship to `TimerConfig`
- `engine_service._advance_from_activity`: when activating a MANUAL activity with timer config, set `WorkItem.due_date` from the timer config; for delay-type timers on AUTO activities, set a `timer_fires_at` timestamp
- `WorkItem`: `due_date` column already exists -- use it for SLA tracking
- `celery_app.py`: add `check-timer-deadlines` to beat schedule (every 30s)
- `ActivityTemplate`: `expected_duration_hours` already exists -- use as default SLA when no explicit timer config

**Data flow:**
```
Activity activated with timer_config
  -> WorkItem.due_date set from duration/deadline
  -> Celery Beat polls check_timer_deadlines every 30s
  -> Past-due items trigger execute_timer_escalation
  -> Escalation: reassign / notify / bump priority / auto-complete
```

### 2. Sub-Workflows

**What it needs:** A workflow activity that spawns a child workflow, optionally waits for completion, then continues the parent.

**Integration approach:** Add `ActivityType.SUB_WORKFLOW` enum value. The engine handles it by spawning a child workflow and leaving the parent activity ACTIVE until the child finishes.

**New components:**
- `src/app/models/sub_workflow.py` -- `SubWorkflowLink` model
  - Fields: `parent_workflow_id` (FK), `parent_activity_instance_id` (FK), `child_workflow_id` (FK), `variable_mapping_in` (JSON: parent->child), `variable_mapping_out` (JSON: child->parent), `state` (active/completed/failed), `max_depth` (enforced limit)
- `src/app/tasks/sub_workflow_tasks.py` -- Celery task to monitor child completion
  - `poll_sub_workflows` -- Beat task (every 10s), checks if child workflows are FINISHED/FAILED
  - On child FINISHED: copy output variables back to parent, advance parent
  - On child FAILED: mark parent activity as ERROR

**Modifications to existing:**
- `enums.py`: add `ActivityType.SUB_WORKFLOW = "sub_workflow"`
- `ActivityTemplate`: add `sub_process_template_id` (FK to ProcessTemplate) and `variable_mapping` (JSON)
- `engine_service._advance_from_activity`: new case in the activity type match:
  ```python
  case ActivityType.SUB_WORKFLOW:
      # Spawn child workflow, create SubWorkflowLink, leave ACTIVE
  ```
- `engine_service.start_workflow`: accept optional `parent_link_id` for traceability
- `celery_app.py`: add `poll-sub-workflows` to beat schedule

**Data flow:**
```
Parent reaches SUB_WORKFLOW activity
  -> engine calls start_workflow() for child template
  -> SubWorkflowLink created (parent_ai <-> child_wf)
  -> Parent activity stays ACTIVE
  -> Celery Beat polls child state every 10s
  -> Child FINISHED -> copy output vars -> advance parent
```

### 3. Event-Driven Activities

**What it needs:** Activities that wait for a specific event (document uploaded, lifecycle changed, external webhook) rather than user/auto completion.

**Integration approach:** Add `ActivityType.EVENT` and build a lightweight event bus on Redis pub/sub. Events emitted by existing services; event activities subscribe and complete when matched.

**New components:**
- `src/app/services/event_bus.py` -- Event dispatcher
  - `emit_event(event_type: str, payload: dict)` -- publishes to Redis channel
  - Standard event types: `document.uploaded`, `document.checked_in`, `lifecycle.changed`, `workflow.completed`, `external.webhook`
- `src/app/models/event.py`
  - `EventSubscription` model: `activity_template_id` (FK), `event_type`, `filter_expression` (optional condition on payload)
  - `EventLog` model: `event_type`, `payload` (JSON), `timestamp`, `matched_subscription_id`
- `src/app/tasks/event_tasks.py` -- Background event processor
  - Listens to Redis pub/sub, matches against active EVENT activity subscriptions
  - On match: completes the activity instance, advances workflow
- `src/app/routers/events.py` -- Webhook endpoint for external events

**Modifications to existing:**
- `enums.py`: add `ActivityType.EVENT = "event"`
- `ActivityTemplate`: add `event_type` (string) and `event_filter` (JSON)
- `engine_service._advance_from_activity`: for EVENT type, leave ACTIVE (event listener completes)
- `document_service.py`: add `emit_event("document.uploaded", ...)` after upload
- `lifecycle_service.py`: add `emit_event("lifecycle.changed", ...)` after transitions

**Data flow:**
```
EVENT activity activated -> stays ACTIVE, subscription registered in DB
  -> document_service uploads file -> event_bus.emit("document.uploaded", {...})
  -> event_tasks listener matches subscription -> completes activity -> advances workflow
```

### 4. Notifications Framework

**What it needs:** Email and in-app notifications triggered by workflow events (task assignment, delegation, approaching deadlines, workflow completions).

**Integration approach:** Cross-cutting service that hooks into existing operations. The existing `send_email` auto method handles SMTP -- extract and generalize the email logic.

**New components:**
- `src/app/models/notification.py`
  - `Notification` model: `user_id` (FK), `type` (enum: task_assigned, deadline_approaching, workflow_completed, escalation, delegation), `title`, `body`, `is_read`, `link_url`, `metadata` (JSON)
  - `NotificationPreference` model: `user_id`, `notification_type`, `channel` (email/in_app), `enabled`
- `src/app/services/notification_service.py`
  - `notify(user_ids, notification_type, context)` -- creates in-app records + queues email
  - Jinja2 templates for email body rendering
- `src/app/tasks/notification_tasks.py` -- Celery task for async email sending
- `src/app/routers/notifications.py` -- REST endpoints (list, mark-read, preferences, count-unread)
- Frontend: notification bell in AppShell header, notification dropdown/panel

**Modifications to existing:**
- `engine_service._advance_from_activity`: call `notify()` when creating work items
- `engine_service.complete_work_item`: notify on workflow completion (when FINISHED)
- `timer_tasks.py`: notify on deadline approaching/breached
- `config.py`: SMTP settings already present -- sufficient
- `auto_methods/builtin.py`: `send_email` can optionally delegate to notification_service

### 5. Document Renditions and Transformations

**What it needs:** Auto-generate PDF or thumbnail renditions of uploaded documents. Store alongside originals in MinIO.

**Integration approach:** Celery worker tasks triggered on document upload/check-in. Separate MinIO bucket for renditions.

**New components:**
- `src/app/models/rendition.py` -- `DocumentRendition` model
  - Fields: `document_version_id` (FK), `rendition_type` (pdf/thumbnail/preview), `content_type`, `minio_object_key`, `status` (pending/processing/completed/failed), `file_size`, `error_message`
- `src/app/services/rendition_service.py`
  - `request_rendition(document_version_id, rendition_type)` -- creates record + dispatches Celery task
  - `get_rendition(document_version_id, rendition_type)` -- returns rendition data or presigned URL
- `src/app/tasks/rendition_tasks.py` -- Celery tasks for conversion
  - `generate_pdf_rendition` -- LibreOffice headless for Office docs, passthrough for PDFs
  - `generate_thumbnail` -- Pillow for images, pdf2image for PDFs (first page)
- `src/app/routers/renditions.py` -- REST endpoints (list, download, request)

**Modifications to existing:**
- `document_service.py`: after upload/check-in, dispatch rendition tasks automatically
- `minio_client.py`: add `RENDITIONS_BUCKET = "renditions"` and ensure-bucket
- `docker-compose.yml`: Celery worker image needs LibreOffice headless (or add dedicated rendition worker)
- `Dockerfile`: install `libreoffice-headless`, `python3-pil`, `poppler-utils`

### 6. Virtual/Compound Documents

**What it needs:** Parent-child document assemblies where a container document references others in order.

**Integration approach:** Metadata-layer feature -- actual files stay in MinIO unchanged. New model for document tree relationships.

**New components:**
- `src/app/models/virtual_document.py`
  - `VirtualDocumentNode` model: `parent_document_id` (FK to Document), `child_document_id` (FK), `child_version_id` (FK, nullable for late-bound), `sort_order`, `binding_type` (early/late)
- `src/app/services/virtual_document_service.py`
  - `add_child()`, `remove_child()`, `reorder_children()`
  - `resolve_tree(document_id)` -- recursively resolves with cycle detection and depth limit
  - `assemble_pdf(document_id)` -- merges children into single PDF via rendition pipeline
- `src/app/routers/virtual_documents.py` -- REST endpoints

**Modifications to existing:**
- `Document` model: add `is_virtual` boolean flag
- No changes needed to `WorkflowPackage` -- it already references `document_id`

### 7. Retention and Records Management

**What it needs:** Retention policies enforcing document preservation, legal holds preventing deletion, disposition schedules for cleanup.

**New components:**
- `src/app/models/retention.py`
  - `RetentionPolicy` model: `name`, `retention_period_days`, `disposition_action` (delete/archive/review), `applies_to_lifecycle_state`
  - `RetentionAssignment` model: `document_id` (FK), `policy_id` (FK), `retention_start_date`, `disposition_date`, `is_record` (declared immutable)
  - `LegalHold` model: `name`, `reason`, `is_active`
  - `LegalHoldAssignment` model: `hold_id` (FK), `document_id` (FK)
- `src/app/services/retention_service.py`
  - `assign_policy()`, `declare_record()`, `apply_legal_hold()`, `release_hold()`
  - `process_dispositions()` -- handles expired retention (called by Celery Beat)
- `src/app/tasks/retention_tasks.py` -- Daily Beat task for disposition processing
- `src/app/routers/retention.py` -- REST endpoints

**Modifications to existing:**
- `document_service.py`: before delete/modify, check retention holds and record status
- `lifecycle_service.py`: auto-assign retention policy when entering ARCHIVED state
- `celery_app.py`: add `process-dispositions` to beat schedule (every 24 hours)

### 8. Digital Signatures

**What it needs:** Cryptographic signing of documents and workflow approvals for non-repudiation.

**New components:**
- `src/app/models/signature.py`
  - `DigitalSignature` model: `document_version_id` (FK), `signer_user_id` (FK), `signature_data` (base64), `certificate_fingerprint`, `signed_at`, `content_hash` (SHA-256 at signing time), `is_valid`
  - `SigningCertificate` model: `user_id` (FK), `certificate_pem`, `private_key_encrypted`, `valid_from`, `valid_until`, `is_active`
- `src/app/services/signature_service.py`
  - `sign_document(document_version_id, user_id)` -- download from MinIO, hash, create PKCS7/CMS signature
  - `verify_signature(signature_id)` -- re-download, verify hash, validate certificate chain
  - `sign_work_item(work_item_id, user_id)` -- sign a workflow approval action
  - Uses `cryptography` library (already transitive dependency via python-jose)
- `src/app/routers/signatures.py` -- REST endpoints (sign, verify, list)

**Modifications to existing:**
- `ActivityTemplate`: add `requires_signature` boolean
- `engine_service.complete_work_item`: if `requires_signature`, verify signature exists before allowing completion
- `pyproject.toml`: add `cryptography` as explicit dependency

## Component Boundary Summary

```
EXISTING (modify)                         NEW (create)
=================                         ============

models/
  enums.py ............ +SUB_WORKFLOW, +EVENT     timer.py
  workflow.py ......... +timer_config,            sub_workflow.py
                         +sub_process_template_id, event.py
                         +event_type,              notification.py
                         +requires_signature       rendition.py
  document.py ......... +is_virtual, +is_record   virtual_document.py
                                                   retention.py
                                                   signature.py

services/
  engine_service.py ... +sub-workflow spawn,       timer_service.py
                         +event wait,              event_bus.py
                         +notification hooks,      notification_service.py
                         +signature check          rendition_service.py
  document_service.py . +retention checks,         virtual_document_service.py
                         +rendition triggers,      retention_service.py
                         +event emission           signature_service.py
  lifecycle_service.py  +event emission,
                         +retention auto-assign

tasks/
  (auto_activity.py -- no changes)                 timer_tasks.py
  (metrics_aggregation -- no changes)              sub_workflow_tasks.py
                                                   event_tasks.py
                                                   notification_tasks.py
                                                   rendition_tasks.py
                                                   retention_tasks.py

routers/
  (existing -- no changes)                         notifications.py
                                                   renditions.py
                                                   virtual_documents.py
                                                   retention.py
                                                   signatures.py
                                                   events.py (webhook endpoint)

core/
  config.py ........... +notification settings
  minio_client.py ..... +renditions bucket

celery_app.py ......... +4 beat schedules
docker-compose.yml .... +rendition worker (LibreOffice)
```

## Recommended Architecture: Event-First Integration Layer

All 8 features benefit from a shared event bus. Build notifications + event bus first because:

1. **Notifications** subscribe to events (task_assigned, deadline_breached, workflow_completed)
2. **Timer escalations** emit events that notifications consume
3. **Event activities** are the primary event consumer
4. **Rendition completion** emits events that workflows can wait on
5. **Retention disposition** can notify admins via events

```
                         +-------------------+
                         |   Redis Pub/Sub   |
                         |   (Event Bus)     |
                         +--------+----------+
                                  |
         +------------------------+------------------------+
         |            |           |           |            |
   engine_service  document_svc  lifecycle  timer_tasks  external
   (emit: activity (emit: doc    (emit:     (emit:       webhooks
    completed,      uploaded,    state      deadline     (emit:
    work_item       checked_in)  changed)   breached)    custom)
    created)
         |
         v
   +-----+------+----+----------+-----------+
   |            |            |              |
  Event      Notification  Rendition     Sub-workflow
  Activities  Service      Triggers      Completion
  (complete   (email +     (auto-gen     Events
   on match)   in-app)     on upload)
```

## Patterns to Follow

### Pattern 1: Service-Layer Event Emission (Post-Commit)
**What:** Every state-changing operation emits a domain event after the DB transaction succeeds.
**When:** All service methods that mutate state.
**Example:**
```python
# In engine_service.py, after creating work items and flushing:
from app.services.event_bus import emit_event

await emit_event("work_item.created", {
    "work_item_id": str(work_item.id),
    "performer_id": str(perf_id),
    "workflow_id": str(workflow.id),
    "activity_name": target_at.name,
})
```

### Pattern 2: Celery Beat Polling for Time-Based Operations
**What:** Use Beat polling rather than individual delayed tasks (`apply_async(eta=...)`).
**When:** Timers, deadlines, retention dispositions, sub-workflow monitoring.
**Why:** Individual ETA tasks are lost on worker restart. Polling is idempotent and survives restarts. The existing auto-activity poll already uses this pattern successfully.
**Example:**
```python
# celery_app.py beat_schedule addition:
"check-timer-deadlines": {
    "task": "app.tasks.timer_tasks.check_timer_deadlines",
    "schedule": 30.0,
},
```

### Pattern 3: Model Extension via JSON Columns + Relationships
**What:** Add new capabilities to ActivityTemplate via JSON columns and separate relationship tables rather than subclassing.
**When:** Timer config, sub-workflow config, event config, signature requirements.
**Why:** Keeps the core workflow model stable. New features are additive. Migrations are non-destructive.
**Example:**
```python
# JSON column approach (simpler, good for config that does not need querying):
timer_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

# Relationship approach (better when you need to query across timers):
class TimerConfig(BaseModel):
    activity_template_id: Mapped[uuid.UUID] = mapped_column(FK)
    ...
```

### Pattern 4: Consistent Task Pattern (mirror auto_activity.py)
**What:** New Celery tasks follow the same sync-wrapper-over-async pattern as `auto_activity.py`.
**When:** All new tasks (timer, sub-workflow, event, rendition, retention, notification).
**Why:** Consistency. The pattern of `def task(): asyncio.run(_async())` with separate session factory is proven.
```python
@celery_app.task(name="app.tasks.timer_tasks.check_timer_deadlines")
def check_timer_deadlines():
    asyncio.run(_check_deadlines_async())
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Individual Delayed Celery Tasks for Timers
**What:** Scheduling `task.apply_async(eta=deadline)` for each work item.
**Why bad:** Lost on worker restart. Hard to cancel/modify. No visibility into pending timers.
**Instead:** Beat polls a deadlines query. Idempotent, restartable, queryable.

### Anti-Pattern 2: Synchronous Event Processing in Request Path
**What:** Processing notifications, renditions, or event matching inline during HTTP request handling.
**Why bad:** Slows API responses. Couples features tightly. Partial failure risk.
**Instead:** Emit to Redis pub/sub, background tasks consume asynchronously.

### Anti-Pattern 3: God Object Expansion
**What:** Adding sub_workflow_link, timer_state, signature_status columns directly onto `WorkflowInstance`.
**Why bad:** WorkflowInstance grows unboundedly. Every migration affects all rows. Conceptual bloat.
**Instead:** Separate linking tables (SubWorkflowLink, TimerConfig, DigitalSignature) with FK back to the relevant entity.

### Anti-Pattern 4: Unbounded Sub-Workflow Recursion
**What:** Allowing sub-workflows to spawn sub-workflows without depth tracking.
**Why bad:** Infinite loops, stack-like resource consumption, impossible debugging.
**Instead:** Track `depth` in SubWorkflowLink, enforce max (5 levels). Reject spawning beyond limit.

### Anti-Pattern 5: Rendition Processing in API Worker
**What:** Running LibreOffice conversion in the FastAPI process.
**Why bad:** CPU-bound, blocks async event loop, can crash the API server.
**Instead:** Always dispatch to Celery worker. Consider a dedicated rendition worker pool.

## Scalability Considerations

| Concern | At 100 workflows | At 10K workflows | At 1M workflows |
|---------|-------------------|-------------------|-------------------|
| Timer polling | Single Beat query, <100ms | Index on `(state, due_date)`, batch processing | Partition work_items by date, dedicated timer workers |
| Sub-workflow tracking | FK query in poll task | Indexed query, batch advancement | Separate status table with partitioned polling |
| Event bus throughput | Redis pub/sub trivially | Still fine (~100K msg/s) | Migrate to Redis Streams for persistence + consumer groups |
| Notification volume | Direct DB insert + email | Batch email, async writes | Read replica for queries, message queue for email |
| Rendition processing | Single Celery worker | Dedicated rendition worker pool (CPU-bound) | Separate rendition microservice |
| Digital signatures | Inline crypto, <50ms per sign | Background batch verification | HSM integration, cert cache |

## Suggested Build Order (Dependency-Driven)

```
Phase 1: Notifications + Event Bus Foundation
  Why first: Event bus is consumed by every subsequent feature.
  Notifications provide immediate UX value and are needed for timer escalation.
  Lowest engine complexity -- validates the integration pattern.
  Touches: new models, new service, new router, new tasks, minor engine hooks

Phase 2: Timer Activities & Escalation
  Depends on: Phase 1 (notifications for escalation alerts)
  Why second: Most requested missing feature. Validates Celery Beat pattern.
  Touches: ActivityTemplate modification, new beat task, engine_service hooks

Phase 3: Sub-Workflows
  Depends on: Stable engine (phases 1-2 validated engine modification patterns)
  Why third: Most complex engine change. Parent-child lifecycle management.
  Touches: new enum value, engine_service major addition, new beat task

Phase 4: Event-Driven Activities
  Depends on: Event bus (Phase 1)
  Why fourth: Second new activity type. Validates event bus under workflow load.
  Touches: new enum value, engine_service addition, event listener tasks

Phase 5: Document Renditions
  Independent of workflow engine changes.
  Why fifth: New Docker dependency (LibreOffice). Clear service boundary.
  Touches: new models/service/tasks, docker-compose, Dockerfile

Phase 6: Virtual Documents
  Depends on: Renditions (Phase 5) for assembled PDF output.
  Why sixth: Metadata-layer only, no engine changes. Lower risk.
  Touches: new models, document model modification

Phase 7: Retention & Records Management
  Independent of workflow engine.
  Why seventh: Policy enforcement via document_service hooks. Careful testing needed.
  Touches: document_service modification, lifecycle hooks, daily beat task

Phase 8: Digital Signatures
  Depends on: Stable document model (Phases 5-7).
  Why last: Cryptographic complexity. Optional workflow integration.
  Touches: new models, engine_service (requires_signature check), crypto deps
```

## Sources

- Codebase analysis: `src/app/services/engine_service.py` -- token-based Petri-net, activity type dispatch, ~1100 lines -- HIGH confidence
- Codebase analysis: `src/app/tasks/auto_activity.py` -- Celery worker pattern with asyncio.run wrapper -- HIGH confidence
- Codebase analysis: `src/app/celery_app.py` -- Beat schedule with 2 existing tasks -- HIGH confidence
- Codebase analysis: `src/app/models/workflow.py` -- ActivityTemplate has expected_duration_hours, WorkItem has due_date -- HIGH confidence
- Codebase analysis: `src/app/auto_methods/` -- decorator registry pattern for extensibility -- HIGH confidence
- Codebase analysis: `src/app/models/document.py` -- Document + DocumentVersion with MinIO keys -- HIGH confidence
- Codebase analysis: `src/app/core/minio_client.py` -- single bucket, asyncio.to_thread wrapping -- HIGH confidence
- Redis pub/sub for event bus: well-established pattern, redis-py async support -- HIGH confidence
- Celery Beat polling vs individual ETA tasks: Celery best practices documentation -- HIGH confidence
- LibreOffice headless for document conversion: standard server-side approach -- HIGH confidence
- Python `cryptography` library for PKCS7/CMS signatures: standard, mature -- HIGH confidence
