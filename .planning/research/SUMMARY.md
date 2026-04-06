# Project Research Summary

**Project:** Documentum Workflow Clone v1.2 — Advanced Engine & Document Platform
**Domain:** Business Process Management / Enterprise Content Management
**Researched:** 2026-04-06
**Confidence:** HIGH

## Executive Summary

This project extends an already-functional Documentum workflow clone with eight advanced features: timer/deadline activities, sub-workflow spawning, event-driven activities, in-app and email notifications, document renditions, virtual/compound documents, retention policies, and digital signatures. The existing architecture — FastAPI + SQLAlchemy async + PostgreSQL + Celery + Redis + MinIO + React/Vite SPA — requires no structural changes. Every v1.2 feature is additive: new models, new services, new Celery tasks, and targeted hooks into three proven engine extension points: (1) the ActivityType dispatch in `_advance_from_activity`, (2) the Celery Beat schedule, and (3) the auto_methods decorator registry.

The recommended build order is event-first. A shared Redis pub/sub event bus with a persistent `events` table is the architectural keystone for v1.2 — 6 of 8 features either emit or consume domain events. Building the event bus and notification framework first (Phase 1) means timers emit deadline events, sub-workflows emit completion events, renditions emit conversion-complete events, and retention dispositions notify admins — all through a single integration layer established once. Skipping the event bus and bolting notifications on per-feature is the primary structural risk to avoid.

The four highest-priority risks, each with clear prevention strategies: (1) using Celery ETA tasks for deadlines — they vanish on worker restart, and must be replaced by database-backed Beat polling per the pattern already in the codebase; (2) sub-workflow recursion without depth enforcement causing infinite cascades; (3) event circular chains causing Celery queue exhaustion if circuit breakers are not built into the event bus from day one; and (4) running LibreOffice rendition conversion in the FastAPI process, which will crash the API server. All four are well understood from codebase analysis and have unambiguous prevention strategies.

## Key Findings

### Recommended Stack

The v1.0 stack is fully adequate. V1.2 adds only five new Python packages and two system dependencies (in Docker only). No new infrastructure services. Redis expands its role to event bus via pub/sub. A dedicated `Dockerfile.worker` for the Celery rendition worker isolates LibreOffice from the lean API image.

**Core technologies (unchanged):**
- FastAPI 0.135.x: HTTP API — unchanged, all new features add routers following existing patterns
- SQLAlchemy 2.0.48 (async + asyncpg): ORM — all new models extend `BaseModel` (soft delete, timestamps, created_by)
- PostgreSQL 16+: primary store — JSONB for event payloads, timer config, process variables; recursive CTEs for virtual document cycle detection
- Redis 7.x: Celery broker + event bus pub/sub — dual role, no additional infrastructure required
- Celery 5.6.x + Beat: task execution and scheduling — adds 6 new Beat tasks (timer poll, sub-workflow poll, event processor, disposition, and notification flush)
- MinIO: object storage — adds a `renditions` bucket alongside the existing `documents` bucket
- React 19 + shadcn/ui: frontend — notification bell and rendition status use existing component patterns; no new frontend libraries required

**New Python packages (backend only):**
- Jinja2 3.1.x: email template rendering (already a transitive dep via Starlette)
- Pillow 11.x: image thumbnail generation
- pdf2image 1.17.x: PDF-to-image conversion (wraps poppler-utils system dep)
- cryptography 44.x: PKCS7/CMS digital signatures (already a transitive dep via python-jose)
- PyPDF 5.x: pure-Python PDF merge for virtual document assembly

**New system packages (in `Dockerfile.worker` only):**
- `libreoffice-headless`: Office document to PDF conversion
- `poppler-utils`: PDF rendering backend for pdf2image

See `.planning/research/STACK.md` for full Celery Beat schedule additions and alternatives considered.

### Expected Features

**Must have (table stakes — missing = incomplete Documentum clone):**
- Timer/deadline activities — deadline config on ActivityTemplate, Beat polling every 30s, escalation actions (reassign, notify, bump priority, auto-complete)
- Escalation on overdue — triggered by timer poll, consumes notification service, updates WorkItem audit trail
- Sub-workflow spawning — `ActivityType.SUB_WORKFLOW`, parent-child lifecycle management, input variable mapping, depth limit of 5
- Email notifications — Jinja2-rendered HTML dispatched via Celery (SMTP config already present in config.py)
- In-app notifications — `Notification` model + REST API + frontend bell with unread count

**Should have (differentiators, high value):**
- Event-driven activities — Redis pub/sub event bus, `ActivityType.EVENT` that completes on matching event, webhook endpoint for external triggers
- Document renditions — LibreOffice headless PDF generation, Pillow thumbnails, auto-trigger on upload/check-in, dedicated Celery worker
- Virtual/compound documents — metadata-layer document tree with cycle-safe resolution, optional PyPDF assembly
- Retention policies — policy engine, legal hold, two-phase disposition (mark then hard-delete after grace period), audit trail preservation
- Digital signatures — PKCS7/CMS signing on `DocumentVersion` (not `Document`), streaming hash from MinIO, post-signing version immutability

**Lower priority (implement later within their respective phases):**
- Notification preferences — per-user opt-in/out by type and channel (defer within Phase 1)
- Webhook-triggered activities — external systems firing workflow events (add after event bus is stable)

**Defer to v2+:**
- Real-time collaborative editing, calendar/scheduling UI for timers, full PKI/CA infrastructure, email-based workflow actions (reply to approve), multi-tenant isolation, rendition preview editing, complex retention schedule builder UI

See `.planning/research/FEATURES.md` for the full feature dependency graph and MVP scope recommendations per feature.

### Architecture Approach

The existing system is a clean layered architecture: React SPA → FastAPI routers → service layer → PostgreSQL/MinIO/Redis/Celery. The token-based Petri-net engine (`engine_service.py`, ~1100 lines) uses a `match` on `ActivityType` — new types `SUB_WORKFLOW` and `EVENT` slot into this dispatch directly. The architectural keystone for v1.2 is a shared event bus (Redis pub/sub + persistent `events` table) that every new feature either emits to or subscribes from. All new Celery tasks follow the proven `sync-wrapper-over-async` pattern from `auto_activity.py`.

**New major components:**
1. Event Bus (`event_bus.py` + `events` table) — cross-cutting; all state-changing services emit post-commit; `events` table provides durability and catch-up on worker startup
2. Notification Service (`notification_service.py` + `Notification` + `NotificationPreference` models + Celery tasks) — consumes event bus, renders Jinja2 templates, writes in-app records with batching and deduplication
3. Timer System (`TimerConfig` model + `timer_service.py` + `timer_tasks.py` Beat task every 30s) — extends ActivityTemplate; uses `WorkItem.due_date` which already exists
4. Sub-Workflow Engine (`SubWorkflowLink` model + `sub_workflow_tasks.py` Beat task + engine_service extension) — new ActivityType, parent-child cascade halt/fail, depth tracking on `WorkflowInstance`
5. Event-Driven Activities (`EventSubscription` + `EventLog` models + `event_tasks.py` + engine_service extension) — new ActivityType, `FOR UPDATE SKIP LOCKED` on completion, chain depth circuit breaker
6. Rendition Pipeline (`DocumentRendition` model + `rendition_service.py` + `rendition_tasks.py` + dedicated Celery rendition worker) — LibreOffice for Office/PDF, Pillow for images, isolated `-Q renditions` queue
7. Virtual Documents (`VirtualDocumentNode` model + `virtual_document_service.py`) — metadata-layer tree, PostgreSQL recursive CTE cycle detection at add-component time, optional PyPDF assembly
8. Retention & Records (`RetentionPolicy` + `RetentionAssignment` + `LegalHold` + `LegalHoldAssignment` models + `retention_service.py` + daily Beat task) — hooks into document_service before delete/modify, lifecycle_service for auto-assignment
9. Digital Signatures (`DigitalSignature` + `SigningCertificate` models + `signature_service.py`) — signs `DocumentVersion` (immutable), streaming SHA-256 from MinIO, 409 Conflict on post-signing modifications

**Key architectural patterns mandated by research:**
- Service-layer event emission post-commit (never inline in HTTP request handler)
- Celery Beat polling for all time-based operations (never `apply_async(eta=...)`)
- Model extension via JSON columns and separate linking tables, not WorkflowInstance expansion
- All new tasks mirror the `sync-wrapper-over-async` pattern from `auto_activity.py`

See `.planning/research/ARCHITECTURE.md` for component boundary diagram, full integration patterns, and scalability table.

### Critical Pitfalls

1. **Individual Celery ETA tasks for deadlines vanish on worker restart** — Use database-backed Beat polling (`check_timer_deadlines` every 30s queries `WHERE state='active' AND timer_deadline < NOW()`). Store all timer state in the database. Consider RedBeat for per-instance dynamic scheduling. Never use `apply_async(eta=...)` for deadline or escalation logic.

2. **Sub-workflow recursion cascades infinitely** — Enforce `max_depth = 5` on `WorkflowInstance`. Run DFS cycle detection at template installation time. Both checks are mandatory; neither alone is sufficient. Monitor for rapid growth in `workflow_instances` rows after starting specific templates.

3. **Sub-workflow lifecycle orphans and zombies** — Halting a parent must recursively halt all children. Child failure must error the parent's spawning activity. Child completion when parent is halted must be a graceful no-op. Wire via callback in `advance_workflow`, not polling.

4. **Event circular chains exhaust the Celery queue** — Add `chain_depth` counter and `source_event_id` to all emitted events from day one. Persist all events to the `events` table before pub/sub emission. Rate-limit per workflow instance. Circuit breakers cannot be added retroactively without re-architecting event emission.

5. **Rendition processing in the API worker crashes the server** — LibreOffice uses 500MB+ RAM, can segfault on malformed input, and blocks the async event loop if called in FastAPI. Always dispatch to a dedicated Celery queue (`-Q renditions`) with `max_tasks_per_child=20` and `max_memory_per_child=512000`.

6. **Digital signature linked to Document instead of DocumentVersion** — Signatures must reference `DocumentVersion.id` (immutable by construction). Hash must be computed by streaming from MinIO, not from DB fields. Signed versions must reject further check-in and metadata updates with 409 Conflict.

See `.planning/research/PITFALLS.md` for 14 pitfalls with phase-to-pitfall mapping, UX pitfalls, integration gotchas, performance traps, security mistakes, and a "Looks Done But Isn't" verification checklist.

## Implications for Roadmap

The architecture's event-first dependency graph maps cleanly to 8 sequential phases. This order is validated against the pitfall-to-phase mapping in PITFALLS.md and the build-order recommendation in ARCHITECTURE.md.

### Phase 1: Notifications + Event Bus Foundation
**Rationale:** The event bus is consumed by every subsequent feature. Building it first establishes the integration pattern once, prevents ad-hoc feature coupling, and provides immediate user-visible value. Lowest engine complexity of all 8 features — ideal validation of the integration approach before any engine modifications.
**Delivers:** Redis pub/sub event bus with persistent `events` table and worker catch-up on startup; `Notification` + `NotificationPreference` models; REST API for listing, marking read, and preference management; frontend notification bell with unread count; Jinja2 email templates dispatched via Celery; notification batching and per-user deduplication.
**Addresses:** In-app notifications (table stakes), email notifications (table stakes).
**Avoids:** Pitfall #7 (notification storm) — batching infrastructure established from the start.

### Phase 2: Timer Activities & Escalation
**Rationale:** Most immediately visible missing feature. Validates the Celery Beat polling pattern before sub-workflows require it at higher complexity. Depends on Phase 1 notifications for escalation alerts.
**Delivers:** `TimerConfig` model (linked to ActivityTemplate); deadline enforcement via existing `WorkItem.due_date`; `check_timer_deadlines` Beat task (every 30s); escalation actions (reassign, notify, bump priority, auto-complete); timer cancellation on ALL terminal paths (completion, rejection, halt, failure, parallel branch cancellation); template versioning test (extended by each subsequent phase).
**Addresses:** Timer/deadline activities (table stakes), escalation on overdue (table stakes).
**Avoids:** Pitfall #1 (ETA tasks lost on restart), Pitfall #11 (timer config lost on template versioning).

### Phase 3: Sub-Workflows
**Rationale:** Highest engine complexity. Placed after Phases 1-2 so engine modification patterns are proven and notification infrastructure is available for lifecycle events. Parent-child cascade semantics require careful design before coding begins.
**Delivers:** `ActivityType.SUB_WORKFLOW` enum value; `SubWorkflowLink` model with depth tracking; `parent_workflow_id` and `spawning_activity_instance_id` on `WorkflowInstance`; `poll_sub_workflows` Beat task (every 10s); cascade halt/fail logic in `engine_service`; variable mapping with type validation; DFS cycle detection at template installation time.
**Addresses:** Sub-workflow spawning (table stakes).
**Avoids:** Pitfall #2 (infinite recursion), Pitfall #3 (zombie workflows), Pitfall #12 (variable type mismatch).

### Phase 4: Event-Driven Activities
**Rationale:** Second new ActivityType. Depends on the event bus from Phase 1. Validates the event bus under real workflow load. Adds external webhook endpoint for third-party integration.
**Delivers:** `ActivityType.EVENT` enum value; `EventSubscription` and `EventLog` models; Redis pub/sub event listener with `FOR UPDATE SKIP LOCKED`; chain depth circuit breaker (`chain_depth` counter, rate-limit per workflow instance); webhook endpoint (`POST /events/external`); event emission hooks in `document_service` and `lifecycle_service`.
**Addresses:** Event-driven activities (differentiator), webhook-triggered activities (differentiator).
**Avoids:** Pitfall #4 (event race conditions), Pitfall #6 (infinite event loops), Pitfall #13 (event message loss).

### Phase 5: Document Renditions
**Rationale:** Independent of workflow engine changes. Introduces the only new Docker dependency (LibreOffice headless), isolated to a dedicated `rendition-worker` service to keep the API image lean. Foundational for Phase 6 (virtual document PDF assembly).
**Delivers:** `DocumentRendition` model with status lifecycle (pending/processing/completed/failed); `rendition_service.py`; LibreOffice headless PDF generation task; Pillow thumbnail task; dedicated Celery worker (`-Q renditions`) with `max_tasks_per_child=20` and `max_memory_per_child=512000`; `renditions` MinIO bucket; rendition status and retry button in document detail UI.
**Addresses:** Document renditions (differentiator).
**Avoids:** Pitfall #10 (rendition in API worker crashes server).

### Phase 6: Virtual/Compound Documents
**Rationale:** Metadata-layer only, no engine changes. Depends on Phase 5 renditions for optional PDF assembly. Lower risk than engine phases; clear service boundary.
**Delivers:** `VirtualDocumentNode` model (parent_document_id, child_document_id, sort_order, binding_type); `virtual_document_service.py` with `add_child`, `remove_child`, `reorder_children`, `resolve_tree` (cycle detection + depth limit of 10), `assemble_pdf` (via PyPDF); `is_virtual` boolean on `Document`; PostgreSQL recursive CTE cycle detection at add-component time.
**Addresses:** Virtual/compound documents (differentiator).
**Avoids:** Pitfall #8 (circular references crash rendering) — cycle detection happens at component add time, not render time.

### Phase 7: Retention & Records Management
**Rationale:** Independent of workflow engine. Hooks into `document_service` and `lifecycle_service`. The legal hold integration with `WorkflowPackage` must be designed before any disposition logic to prevent the most critical data loss scenario.
**Delivers:** `RetentionPolicy`, `RetentionAssignment`, `LegalHold`, `LegalHoldAssignment` models; `retention_service.py`; daily disposition Beat task with two-phase deletion (mark → 30-day grace → hard delete); legal hold blocks on documents attached to RUNNING/HALTED workflows; soft-delete guard checks; audit trail preservation (audit records never cascade-deleted on disposition).
**Addresses:** Retention policies (differentiator).
**Avoids:** Pitfall #9 (retention disposes documents in active workflows), Pitfall #14 (retention bypass via soft delete).

### Phase 8: Digital Signatures
**Rationale:** Placed last because it requires a stable document model (Phases 5-7), highest cryptographic care, and adds optional engine integration (`requires_signature` on ActivityTemplate with enforcement in `complete_work_item`). No other features depend on signatures.
**Delivers:** `DigitalSignature` and `SigningCertificate` models; `signature_service.py` with streaming MinIO hash (64KB chunks), PKCS7/CMS signing via `cryptography` library, PAdES format for PDFs via `endesive`; post-signing version immutability (409 Conflict on check-in and metadata updates for signed versions); `requires_signature` ActivityTemplate flag; sign and verify REST endpoints.
**Addresses:** Digital signatures (differentiator).
**Avoids:** Pitfall #5 (signature linked to Document instead of DocumentVersion).

### Phase Ordering Rationale

- Event bus first because 6 of 8 features depend on it; building it last would require retrofitting integration patterns into already-built features
- Timer activities before sub-workflows because they validate the Beat polling pattern at lower complexity, making the sub-workflow Beat task straightforward
- Sub-workflows before event-driven activities because both add new ActivityTypes to the engine dispatch; handling the more complex case (sub-workflows) first means the event activity addition is a familiar operation
- Renditions before virtual documents because virtual document PDF assembly consumes the rendition pipeline
- Retention before signatures because signed versions must be protected from retention disposition; having retention enforcement in place first means the signature immutability constraint is consistent with existing retention holds
- Template versioning test established in Phase 2 and extended in every subsequent phase, preventing the v1.2 config loss pitfall from silently accumulating

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Sub-Workflows):** Parent-child lifecycle cascade in `advance_workflow` / `_enforce_activity_transition` is the most complex cross-feature engine interaction in v1.2. Variable mapping type coercion semantics and failure propagation (auto-fail vs. allow retry) need explicit design decisions before coding. Recommend a brief design spike before Phase 3 planning.
- **Phase 4 (Event-Driven Activities):** Circuit breaker design has multiple valid approaches (chain depth tracking vs. Redis rate limiter vs. event deduplication table). The choice affects event bus schema. Confirm approach at the start of Phase 4 planning.
- **Phase 8 (Digital Signatures):** PAdES (PDF signing via `endesive`) vs. PKCS7/CMS (via `cryptography`) routing logic, certificate storage encryption strategy (env var passphrase vs. secrets manager), and concurrent signing edge cases (two users signing the same version simultaneously) should be researched before Phase 8 implementation begins.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Notifications + Event Bus):** Redis pub/sub, Jinja2 templates, and notification REST APIs are well-documented patterns. Existing Celery convention provides clear precedent.
- **Phase 2 (Timer Activities):** Beat polling is the established pattern in this codebase. Database-backed timer polling with idempotency guard is straightforward.
- **Phase 5 (Renditions):** LibreOffice headless, Pillow, and dedicated Celery queues are standard DevOps patterns.
- **Phase 6 (Virtual Documents):** PostgreSQL recursive CTEs for cycle detection and metadata-layer tree models are well-understood relational patterns.
- **Phase 7 (Retention):** Two-phase disposition and legal hold models follow standard records management patterns; FK query against `WorkflowPackage` is straightforward.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All existing v1.0 technologies confirmed stable. New packages sourced from official documentation. No experimental dependencies. |
| Features | HIGH | Derived from OpenText Documentum specification (primary reference) and direct codebase analysis of existing extension points. BPM comparison (Camunda, Flowable) used only for supplementary validation at MEDIUM confidence. |
| Architecture | HIGH | All integration points verified against direct codebase analysis of `engine_service.py`, `auto_activity.py`, `celery_app.py`, `workflow.py`, `document.py`. No inference — every extension point confirmed in existing code. |
| Pitfalls | HIGH | 14 pitfalls with prevention strategies. Critical pitfalls sourced from Celery official documentation, Temporal workflow engine design principles, Camunda patterns, and direct codebase analysis. Library-specific pitfalls (LibreOffice memory leaks, endesive PDF-only scope) confirmed by community documentation. |

**Overall confidence:** HIGH

### Gaps to Address

- **RedBeat adoption decision (Phase 2):** PITFALLS.md identifies RedBeat as a superior alternative to static Beat polling for per-activity-instance timer scheduling. The choice between Beat polling and RedBeat (`celery_app.conf.beat_scheduler = 'redbeat.RedBeatScheduler'`) affects the Celery Beat configuration globally. Decide at the start of Phase 2 planning.

- **Sub-workflow failure propagation semantics (Phase 3):** When a child workflow fails, should the parent activity auto-fail (propagate the error upward) or should it allow the supervisor to retry by re-spawning the child? This is a product decision that must be resolved before Phase 3 implementation begins, as it determines the `_enforce_activity_transition` path in `engine_service`.

- **Event bus durability mode (Phase 4):** ARCHITECTURE.md recommends Redis pub/sub + persistent `events` table now, migrating to Redis Streams later if message durability becomes critical at scale. Confirm this trade-off is acceptable at the start of Phase 4 planning.

- **LibreOffice concurrency in Docker (Phase 5):** Multiple LibreOffice instances in the same container can conflict on lock files. The mitigation (Celery concurrency=1 or per-worker `--user-installation` paths) should be verified in a Docker test environment before Phase 5 completes.

- **Certificate storage encryption strategy (Phase 8):** Storing encrypted private signing keys in the database is adequate for internal use, but the passphrase management approach (env var vs. secrets manager vs. project CA) should be decided before Phase 8 implementation to avoid post-implementation key rotation.

## Sources

### Primary (HIGH confidence)
- Codebase: `src/app/services/engine_service.py` — token-based Petri-net, ActivityType dispatch, ~1100 lines
- Codebase: `src/app/tasks/auto_activity.py` — Celery sync-wrapper-over-async pattern
- Codebase: `src/app/celery_app.py` — Beat schedule, `task_acks_late` configuration
- Codebase: `src/app/models/workflow.py` — ActivityTemplate, WorkItem.due_date, ExecutionToken
- Codebase: `src/app/models/document.py` — Document, DocumentVersion, content_hash, minio_object_key
- Codebase: `src/app/core/minio_client.py` — single bucket, asyncio.to_thread wrapping
- Codebase: `src/app/auto_methods/` — decorator registry pattern for extensibility
- OpenText Documentum Workflow Management specification — feature requirements and architecture reference
- Celery 5.6 official docs (periodic tasks, memory management, optimizing guide)
- Pillow, pdf2image, PyPDF, cryptography official documentation
- Redis pub/sub documentation
- endesive library (PyPI) — PDF digital signatures

### Secondary (MEDIUM confidence)
- BPM feature comparison: Camunda, Flowable, Activiti feature sets
- Temporal workflow engine design principles blog
- Orkes Conductor sub-workflow reference
- Event sourcing pitfalls (sylhare.github.io)
- Documentum Virtual Documents architecture (ArgonDigital)
- LibreOffice headless memory leak investigation (ask.libreoffice.org)
- Document retention policy best practices
- RedBeat: Redis-backed Beat Scheduler (GitHub)
- Python Celery Kubernetes and memory (dev.to)

### Tertiary (LOW confidence — needs validation)
- Django async ORM limitations in 2026 (Kraken Engineering) — used only to validate FastAPI choice, not a v1.2 decision input

---
*Research completed: 2026-04-06*
*Ready for roadmap: yes*
