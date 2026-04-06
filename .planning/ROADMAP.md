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

- [x] **Phase 16: Notifications & Event Bus** - Domain event bus with persistent storage, in-app and email notifications, notification UI with unread badge (completed 2026-04-06)
- [ ] **Phase 17: Timer Activities & Escalation** - Deadline configuration on activities, due date enforcement, Beat-driven overdue detection, escalation actions
- [ ] **Phase 18: Sub-Workflows** - SUB_WORKFLOW activity type, child instance spawning, parent-child lifecycle, variable mapping, depth limits
- [ ] **Phase 19: Event-Driven Activities** - EVENT activity type, event subscription matching, auto-completion on domain events
- [ ] **Phase 20: Document Renditions** - Auto-generated PDF and thumbnail renditions via LibreOffice headless worker, rendition status in document UI
- [ ] **Phase 21: Virtual Documents** - Parent-child document assembly, ordering, cycle detection, merged PDF generation
- [ ] **Phase 22: Retention & Records Management** - Retention policies, document assignment, deletion blocking, legal holds
- [ ] **Phase 23: Digital Signatures** - PKCS7/CMS signing on document versions, verification, signature listing, post-signing immutability

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
**Requirements**: NOTIF-03, TIMER-01, TIMER-02, TIMER-03, TIMER-04
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

## Progress

**Execution Order:**
Phases execute in numeric order: 16 -> 17 -> 18 -> 19 -> 20 -> 21 -> 22 -> 23

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 16. Notifications & Event Bus | 4/4 | Complete   | 2026-04-06 |
| 17. Timer Activities & Escalation | 0/? | Not started | - |
| 18. Sub-Workflows | 0/? | Not started | - |
| 19. Event-Driven Activities | 0/? | Not started | - |
| 20. Document Renditions | 0/? | Not started | - |
| 21. Virtual Documents | 0/? | Not started | - |
| 22. Retention & Records Management | 0/? | Not started | - |
| 23. Digital Signatures | 0/? | Not started | - |
