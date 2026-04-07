# Roadmap: Documentum Workflow Clone

## Milestones

- v1.0 Core Engine (Phases 1-11) -- shipped
- v1.1 Full Frontend Experience (Phases 12-15) -- shipped
- v1.2 Advanced Engine & Document Platform (Phases 16-23) -- in progress

## Phases

<details>
<summary>v1.0 Core Engine (Phases 1-11) -- SHIPPED</summary>

Phases 1-11 delivered the complete workflow engine backend: Docker stack, database schema, authentication, audit trail, document management, workflow templates, process engine, visual designer, lifecycle/ACL integration, auto activities, delegation, work queues, BAM dashboards, and the contract approval demo workflow.

</details>

<details>
<summary>v1.1 Full Frontend Experience (Phases 12-15) -- SHIPPED 2026-04-06</summary>

Phases 12-15 delivered the complete web UI: navigation shell, inbox with work item management, document management pages, and workflow operations with start wizard and progress visualization.

</details>

### v1.2 Advanced Engine & Document Platform (In Progress)

**Milestone Goal:** Close the major functional gaps between this system and Documentum -- timer-driven automation, sub-workflow orchestration, event-driven activities, notifications, document renditions, virtual documents, retention policies, and digital signatures.

**Phase Numbering:**
- Continues from v1.1 (Phases 12-15 complete)
- Integer phases (16-23): Planned milestone work
- Decimal phases (16.1, 16.2): Urgent insertions if needed

- [ ] **Phase 16: Notifications & Event Bus** - Domain event bus with persistent storage, in-app and email notifications, notification UI with unread badge
- [ ] **Phase 17: Timer Activities & Escalation** - Deadline configuration on activities, due date enforcement, Beat-driven overdue detection, escalation actions
- [ ] **Phase 18: Sub-Workflows** - SUB_WORKFLOW activity type, child instance spawning, parent-child lifecycle, variable mapping, depth limits
- [ ] **Phase 19: Event-Driven Activities** - EVENT activity type, event subscription matching, auto-completion on domain events
- [ ] **Phase 20: Document Renditions** - Auto-generated PDF and thumbnail renditions via LibreOffice headless worker, rendition status in document UI
- [ ] **Phase 21: Virtual Documents** - Parent-child document assembly, ordering, cycle detection, merged PDF generation
- [ ] **Phase 22: Retention & Records Management** - Retention policies, document assignment, deletion blocking, legal holds
- [x] **Phase 23: Digital Signatures** - PKCS7/CMS signing on document versions, verification, signature listing, post-signing immutability (completed 2026-04-06)
- [x] **Phase 24: Infrastructure Wiring & Event Bus Integration** - Mount missing routers, register event handlers, wire Celery tasks, add missing model columns, emit missing events, trigger renditions, linearize migrations (gap closure) (completed 2026-04-07)
- [ ] **Phase 25: Virtual Documents Frontend Fix** - Align frontend API types/payloads with backend schemas, create missing migration (gap closure)
- [ ] **Phase 26: Digital Signatures Alignment** - Fix migration table/column names, add missing enums, align tests with router paths (gap closure)

## Phase Details

### Phase 16: Notifications & Event Bus
**Goal**: Users receive timely in-app and email notifications for workflow events, and the system has a durable event bus that all subsequent features build on
**Depends on**: Nothing (first phase of v1.2; foundational for all subsequent phases)
**Requirements**: NOTIF-01, NOTIF-02, NOTIF-03, NOTIF-04, NOTIF-05, NOTIF-06, EVENT-01, EVENT-02
**Success Criteria** (what must be TRUE):
  1. User sees a notification bell in the UI header with an unread count that updates when new work items are assigned or delegated
  2. User can open a notification list, see all notifications, and mark them as read individually or in bulk
  3. User receives email notifications for task assignments and approaching deadlines
  4. System emits and persists domain events for document uploads, lifecycle changes, and workflow state transitions -- visible in the events table
**Plans**: TBD
**UI hint**: yes

### Phase 17: Timer Activities & Escalation
**Goal**: Work items automatically enforce deadlines and escalate when overdue, so tasks do not silently stall
**Depends on**: Phase 16 (notifications deliver escalation alerts)
**Requirements**: TIMER-01, TIMER-02, TIMER-03, TIMER-04
**Success Criteria** (what must be TRUE):
  1. Admin can set a deadline duration on an activity template in the workflow designer, and it persists across template saves
  2. When a workflow reaches a timed activity, the resulting work item automatically receives a due date calculated from the template configuration
  3. A Celery Beat task periodically detects overdue work items and triggers the configured escalation action (priority bump, reassignment, or notification)
  4. Escalated work items show updated priority or reassigned performer, and the affected user receives a notification
**Plans**: TBD
**UI hint**: yes

### Phase 18: Sub-Workflows
**Goal**: Workflow designers can compose complex processes from reusable sub-workflows, with the parent pausing until the child completes
**Depends on**: Phase 16 (event bus for lifecycle events), Phase 17 (validates Beat polling pattern)
**Requirements**: SUBWF-01, SUBWF-02, SUBWF-03, SUBWF-04, SUBWF-05
**Success Criteria** (what must be TRUE):
  1. Admin can add a SUB_WORKFLOW activity node in the workflow designer and configure it to reference another installed template
  2. When execution reaches a SUB_WORKFLOW activity, a child workflow instance is spawned and the parent workflow visibly pauses at that activity
  3. When the child workflow completes, the parent workflow automatically resumes from the SUB_WORKFLOW activity
  4. Variables mapped from parent to child are available in the child workflow at startup
  5. System rejects template installation if sub-workflow nesting would exceed the depth limit, preventing infinite recursion
**Plans**: TBD
**UI hint**: yes

### Phase 19: Event-Driven Activities
**Goal**: Workflow activities can wait for and react to domain events (document uploads, lifecycle changes, workflow completions) instead of requiring manual user action
**Depends on**: Phase 16 (event bus provides event delivery), Phase 18 (validates engine dispatch pattern for new ActivityTypes)
**Requirements**: EVTACT-01, EVTACT-02, EVTACT-03
**Success Criteria** (what must be TRUE):
  1. Admin can add an EVENT activity node in the workflow designer and configure which event type and filter it listens for
  2. When a matching domain event fires (document.uploaded, lifecycle.changed, or workflow.completed), the EVENT activity completes automatically and the workflow advances
  3. EVENT activities that do not receive a matching event remain waiting without blocking other parallel branches
**Plans**: TBD
**UI hint**: yes

### Phase 20: Document Renditions
**Goal**: Users get automatic PDF and thumbnail renditions for uploaded documents, with clear status visibility
**Depends on**: Phase 16 (event bus triggers rendition on document upload)
**Requirements**: REND-01, REND-02, REND-03, REND-04
**Success Criteria** (what must be TRUE):
  1. When a user uploads a document, the system automatically queues PDF rendition generation via a LibreOffice headless Celery worker
  2. Thumbnail images are auto-generated for uploaded documents and visible in the document list
  3. User can download the PDF rendition of any document version from the document detail view
  4. Rendition status (pending, ready, failed) is clearly displayed in the document detail view, with a retry option on failure
**Plans**: TBD
**UI hint**: yes

### Phase 21: Virtual Documents
**Goal**: Users can compose compound documents from multiple children in a defined order and generate a merged PDF output
**Depends on**: Phase 20 (rendition pipeline provides PDF source files for assembly)
**Requirements**: VDOC-01, VDOC-02, VDOC-03, VDOC-04
**Success Criteria** (what must be TRUE):
  1. User can create a virtual document and add existing documents as children in a specified order
  2. User can reorder children via drag-and-drop or controls, and remove children from the virtual document
  3. System detects and prevents circular references when adding children (no document can be its own ancestor)
  4. User can generate a merged PDF from all children of a virtual document, downloading a single combined file
**Plans**: TBD
**UI hint**: yes

### Phase 22: Retention & Records Management
**Goal**: Admins can enforce document retention policies and legal holds, preventing premature deletion of governed documents
**Depends on**: Nothing (independent policy layer; hooks into existing document service)
**Requirements**: RET-01, RET-02, RET-03, RET-04
**Success Criteria** (what must be TRUE):
  1. Admin can create retention policies specifying a retention period and disposition action (archive or delete)
  2. Admin can assign a retention policy to one or more documents, and the assignment is visible in the document detail view
  3. System blocks any attempt to delete a document that is under active retention, displaying a clear error message
  4. Admin can place a legal hold on a document, which overrides retention expiration and prevents deletion until the hold is released
**Plans**: TBD
**UI hint**: yes

### Phase 23: Digital Signatures
**Goal**: Users can cryptographically sign document versions and verify signatures, with the system enforcing immutability on signed content
**Depends on**: Phase 20 (stable document version model), Phase 22 (retention holds respected for signed documents)
**Requirements**: SIG-01, SIG-02, SIG-03, SIG-04
**Success Criteria** (what must be TRUE):
  1. User can digitally sign a specific document version using PKCS7/CMS, with the signature stored alongside the version
  2. User can verify the validity of any signature on a signed document version
  3. User can view a list of all signatures on a document with signer identity, timestamp, and validity status
  4. System prevents re-upload, check-in, or metadata modification of a signed document version, returning a clear error
**Plans**: TBD
**UI hint**: yes

### Phase 24: Infrastructure Wiring & Event Bus Integration
**Goal**: Wire all v1.2 phase code into the application infrastructure so every feature is reachable at runtime -- mount missing routers, register event handlers, connect Celery tasks, add missing ORM columns, emit missing events, trigger renditions on upload, and linearize the Alembic migration chain
**Depends on**: Phases 16-23 (fixes integration gaps across all prior phases)
**Requirements**: NOTIF-01, NOTIF-02, NOTIF-03, NOTIF-04, NOTIF-05, NOTIF-06, EVENT-01, TIMER-01, TIMER-03, TIMER-04, SUBWF-03, EVTACT-02, EVTACT-03, REND-01, REND-02, REND-03, REND-04, RET-01, RET-02, RET-04, SIG-04
**Gap Closure**: Closes integration gaps from v1.2 milestone audit
**Success Criteria** (what must be TRUE):
  1. All 10 routers (including notifications, events, renditions, virtual_documents, retention) are mounted in main.py and return non-404 responses
  2. Event handlers module is imported at startup and all @event_bus.on handlers fire when their events are emitted
  3. app.tasks.notification is in Celery include list and check_approaching_deadlines runs on Beat schedule
  4. WorkItem model declares is_escalated and deadline_warning_sent; ActivityTemplate declares warning_threshold_hours and escalation_action
  5. document_service.upload_document() emits document.uploaded event and triggers rendition creation
  6. workflow_mgmt_service.abort_workflow() emits workflow.failed event
  7. checkout_document() calls _check_version_not_signed guard
  8. All new models exported from models/__init__.py
  9. Alembic migration chain is linear (single head) and alembic upgrade head succeeds
**Plans**: 3 plans
Plans:
- [x] 24-01-PLAN.md — Infrastructure wiring: mount routers, import event handlers, register Celery tasks, add model columns, export models
- [x] 24-02-PLAN.md — Service fixes: emit document.uploaded event, trigger renditions on upload/checkin, add checkout signature guard
- [x] 24-03-PLAN.md — Migration chain: linearize down_revision chain, create phase21 virtual documents migration

### Phase 25: Virtual Documents Frontend Fix
**Goal**: Align the virtual documents frontend API client and components with backend schema so all CRUD operations, reordering, and PDF merge work at runtime
**Depends on**: Phase 24 (virtual_documents router must be mounted first)
**Requirements**: VDOC-01, VDOC-02, VDOC-04
**Gap Closure**: Closes frontend-backend contract mismatches from v1.2 milestone audit
**Success Criteria** (what must be TRUE):
  1. VirtualDocumentResponse and VirtualDocumentChildResponse types match backend schema field names exactly
  2. addChild sends { document_id } matching AddChildRequest schema
  3. reorderChildren sends { document_ids } matching ReorderChildrenRequest schema
  4. removeChild passes child document UUID (not join-table PK) in URL path
  5. downloadMergedPdf calls GET .../merge (not POST .../merge-pdf)
  6. Virtual document children display correct titles, filenames, and sort order
  7. Phase 21 Alembic migration exists and creates virtual_documents + virtual_document_children tables
**Plans**: TBD

### Phase 26: Digital Signatures Alignment
**Goal**: Fix migration/model/test mismatches so digital signature sign, verify, and list operations work end-to-end and all tests pass
**Depends on**: Phase 24 (missing enums added, migration chain linearized)
**Requirements**: SIG-01, SIG-02, SIG-03
**Gap Closure**: Closes phase 23 verification gaps from v1.2 milestone audit
**Success Criteria** (what must be TRUE):
  1. Migration table name matches model __tablename__ (document_signatures)
  2. Migration column names match model columns (version_id, algorithm -- no is_valid)
  3. DocumentVersion model declares is_signed column
  4. RenditionStatus and RenditionType enums exist in enums.py
  5. All test endpoint paths and HTTP methods match router definitions
  6. All test field name assertions match schema response fields
  7. All 12 signature tests pass (pytest collection succeeds, assertions pass)
**Plans**: TBD

## Progress

**Execution Order:**
Phases 16-23 complete (code written). Phases 24-26 close integration gaps.
Execution order: 24 -> 25 -> 26

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 16. Notifications & Event Bus | 4/4 | Code complete | 2026-04-06 |
| 17. Timer Activities & Escalation | 3/3 | Code complete | 2026-04-06 |
| 18. Sub-Workflows | 3/3 | Code complete | 2026-04-06 |
| 19. Event-Driven Activities | 2/2 | Code complete | 2026-04-06 |
| 20. Document Renditions | 3/3 | Code complete | 2026-04-06 |
| 21. Virtual Documents | 2/2 | Code complete | 2026-04-06 |
| 22. Retention & Records Management | 2/2 | Code complete | 2026-04-06 |
| 23. Digital Signatures | 2/2 | Code complete | 2026-04-06 |
| 24. Infrastructure Wiring | 3/3 | Complete   | 2026-04-07 |
| 25. Virtual Docs Frontend Fix | 0/? | Not started | - |
| 26. Signatures Alignment | 0/? | Not started | - |
