# Requirements: Documentum Workflow Clone

**Defined:** 2026-04-06
**Core Value:** Any workflow use case described in the Documentum specification can be modeled and executed end-to-end through the system.

## v1.2 Requirements

Requirements for milestone v1.2: Advanced Engine & Document Platform.

### Notifications & Event Bus

- [x] **NOTIF-01**: User receives in-app notification when a work item is assigned to them
- [x] **NOTIF-02**: User receives in-app notification when a task is delegated to them
- [x] **NOTIF-03**: User receives in-app notification when a work item deadline is approaching
- [x] **NOTIF-04**: User receives email notification for task assignment and deadline events
- [x] **NOTIF-05**: User can view notification list with unread count badge in the UI
- [x] **NOTIF-06**: User can mark notifications as read individually or in bulk
- [x] **EVENT-01**: System emits domain events on document upload, lifecycle change, and workflow state transitions
- [ ] **EVENT-02**: Events are persisted in a durable event table for reliability

### Timer Activities & Escalation

- [x] **TIMER-01**: Admin can configure deadline duration on activity templates in the workflow designer
- [ ] **TIMER-02**: Work items automatically receive due dates based on activity template deadline configuration
- [x] **TIMER-03**: Celery Beat periodically checks for overdue work items and triggers escalation
- [x] **TIMER-04**: Overdue work items are automatically escalated (priority bump, reassignment, or notification)

### Sub-Workflows

- [ ] **SUBWF-01**: Admin can add a SUB_WORKFLOW activity type in the workflow designer that references another template
- [ ] **SUBWF-02**: When a SUB_WORKFLOW activity executes, a child workflow instance is spawned from the referenced template
- [x] **SUBWF-03**: Parent workflow pauses at the SUB_WORKFLOW activity until the child workflow completes
- [ ] **SUBWF-04**: Variables can be mapped from parent to child workflow on spawn
- [ ] **SUBWF-05**: System enforces depth limits to prevent recursive sub-workflow chains

### Event-Driven Activities

- [ ] **EVTACT-01**: Admin can add an EVENT activity type in the workflow designer with event filter configuration
- [x] **EVTACT-02**: EVENT activities complete automatically when a matching domain event fires
- [x] **EVTACT-03**: Supported event types include document.uploaded, lifecycle.changed, and workflow.completed

### Document Renditions

- [x] **REND-01**: System auto-generates PDF rendition when a document is uploaded (via LibreOffice headless worker)
- [x] **REND-02**: System auto-generates thumbnail image for uploaded documents
- [x] **REND-03**: User can download the PDF rendition of any document version
- [x] **REND-04**: Rendition status is visible in the document detail view (pending, ready, failed)

### Virtual Documents

- [x] **VDOC-01**: User can create a virtual document and add child documents in a specified order
- [x] **VDOC-02**: User can reorder or remove children from a virtual document
- [ ] **VDOC-03**: System detects and prevents circular references in virtual document trees
- [x] **VDOC-04**: User can generate a merged PDF from a virtual document's children

### Retention & Records Management

- [x] **RET-01**: Admin can create retention policies with retention period and disposition action
- [x] **RET-02**: Admin can assign retention policies to documents
- [ ] **RET-03**: System blocks deletion of documents under active retention
- [x] **RET-04**: Admin can place legal holds on documents that override retention expiration

### Digital Signatures

- [x] **SIG-01**: User can digitally sign a specific document version (PKCS7/CMS signature)
- [x] **SIG-02**: User can verify the signature on a signed document version
- [x] **SIG-03**: User can view all signatures on a document with signer, timestamp, and validity
- [ ] **SIG-04**: System enforces immutability on signed document versions (no re-upload or modification)

## Future Requirements

Deferred beyond v1.2.

### Notifications (deferred)

- **NOTIF-07**: User can configure notification preferences (opt-in/out per type and channel)
- **NOTIF-08**: User receives push notifications via browser push API

### Timer Activities (deferred)

- **TIMER-05**: Admin can configure recurring timer activities
- **TIMER-06**: Admin can use expression-based deadline calculation
- **TIMER-07**: Multi-level escalation chains (escalate -> reassign -> notify supervisor)

### Sub-Workflows (deferred)

- **SUBWF-06**: Output variable mapping from child back to parent on completion
- **SUBWF-07**: Partial completion (wait for any-of-N children)
- **SUBWF-08**: Parallel sub-workflows spawned from a single activity

### Event-Driven Activities (deferred)

- **EVTACT-04**: Complex filter expressions on event payloads
- **EVTACT-05**: Event replay for debugging
- **EVTACT-06**: External webhook authentication for inbound events

### Renditions (deferred)

- **REND-05**: Custom rendition profiles (resolution, format options)
- **REND-06**: Rendition for image format conversions

### Virtual Documents (deferred)

- **VDOC-05**: Nested virtual documents (depth > 1)
- **VDOC-06**: Late-bound version resolution (always use latest child version)

### Digital Signatures (deferred)

- **SIG-05**: Certificate management UI
- **SIG-06**: Sign-on-checkin automation
- **SIG-07**: requires_signature flag on workflow activities
- **SIG-08**: Certificate revocation checking

## Out of Scope

Explicitly excluded from v1.2.

| Feature | Reason |
|---------|--------|
| Real-time collaborative editing | Massive OT/CRDT complexity; check-in/check-out prevents conflicts |
| Calendar/scheduling UI for timers | Timer durations configured in template designer; no calendar needed |
| Full PKI/CA infrastructure | Internal tool; self-signed certs stored in DB suffice |
| Email-based workflow actions | Web UI is the interaction point; email parsing too complex |
| Multi-tenant isolation | Internal/personal use; adds complexity everywhere |
| Rendition preview editing | View-only; editing happens on source document |
| Complex retention schedule builder UI | Simple form suffices; retention policies rarely change |

## Traceability

| Requirement | Phase | Gap Closure | Status |
|-------------|-------|-------------|--------|
| NOTIF-01 | Phase 16 | Phase 24 | Pending |
| NOTIF-02 | Phase 16 | Phase 24 | Pending |
| NOTIF-03 | Phase 17 | Phase 24 | Pending |
| NOTIF-04 | Phase 16 | Phase 24 | Pending |
| NOTIF-05 | Phase 16 | Phase 24 | Pending |
| NOTIF-06 | Phase 16 | Phase 24 | Pending |
| EVENT-01 | Phase 16 | Phase 24 | Pending |
| EVENT-02 | Phase 16 | -- | Satisfied |
| TIMER-01 | Phase 17 | Phase 24 | Pending |
| TIMER-02 | Phase 17 | -- | Satisfied |
| TIMER-03 | Phase 17 | Phase 24 | Pending |
| TIMER-04 | Phase 17 | Phase 24 | Pending |
| SUBWF-01 | Phase 18 | -- | Satisfied |
| SUBWF-02 | Phase 18 | -- | Satisfied |
| SUBWF-03 | Phase 18 | Phase 24 | Pending |
| SUBWF-04 | Phase 18 | -- | Satisfied |
| SUBWF-05 | Phase 18 | -- | Satisfied |
| EVTACT-01 | Phase 19 | -- | Satisfied |
| EVTACT-02 | Phase 19 | Phase 24 | Pending |
| EVTACT-03 | Phase 19 | Phase 24 | Pending |
| REND-01 | Phase 20 | Phase 24 | Pending |
| REND-02 | Phase 20 | Phase 24 | Pending |
| REND-03 | Phase 20 | Phase 24 | Pending |
| REND-04 | Phase 20 | Phase 24 | Pending |
| VDOC-01 | Phase 21 | Phase 25 | Pending |
| VDOC-02 | Phase 21 | Phase 25 | Pending |
| VDOC-03 | Phase 21 | -- | Satisfied |
| VDOC-04 | Phase 21 | Phase 25 | Pending |
| RET-01 | Phase 22 | Phase 24 | Pending |
| RET-02 | Phase 22 | Phase 24 | Pending |
| RET-03 | Phase 22 | Phase 24 | Pending |
| RET-04 | Phase 22 | Phase 24 | Pending |
| SIG-01 | Phase 23 | Phase 26 | Pending |
| SIG-02 | Phase 23 | Phase 26 | Pending |
| SIG-03 | Phase 23 | Phase 26 | Pending |
| SIG-04 | Phase 23 | Phase 24 | Pending |

**Coverage:**
- v1.2 requirements: 36 total
- Satisfied: 8/36
- Pending (gap closure): 28/36
- Unmapped: 0

---
*Requirements defined: 2026-04-06*
*Last updated: 2026-04-07 after milestone audit gap closure planning*
