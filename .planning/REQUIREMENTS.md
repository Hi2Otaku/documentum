# Requirements: Documentum Workflow Clone

**Defined:** 2026-04-06
**Milestone:** v1.1 -- Full Frontend Experience
**Core Value:** Every backend capability accessible through the web UI -- users never need the API or Swagger to operate the system.

## v1.1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Navigation

- [ ] **NAV-01**: User can navigate between all pages (Templates, Inbox, Documents, Workflows, Dashboard, Query) via a persistent sidebar menu
- [ ] **NAV-02**: User can see which page is currently active via highlighted sidebar item
- [x] **NAV-03**: Admin-only pages (Dashboard, Query) are hidden from non-admin users
- [x] **NAV-04**: User can see their username, toggle availability, and log out from a user menu

### Inbox

- [ ] **INB-01**: User can view their pending work items in a filterable, paginated list with state badges
- [ ] **INB-02**: User can click a work item to view full details (activity info, workflow context, comments)
- [ ] **INB-03**: User can acquire, complete, or reject a work item with an optional comment
- [ ] **INB-04**: User can delegate a work item to another user
- [ ] **INB-05**: User can set themselves as unavailable so tasks auto-route to delegates
- [ ] **INB-06**: User can browse shared work queues and claim tasks from the queue pool

### Documents

- [ ] **DOC-01**: User can upload documents via drag-and-drop or file picker
- [ ] **DOC-02**: User can browse documents in a paginated list with title, author, and lifecycle state filters
- [ ] **DOC-03**: User can view version history for a document and download any specific version
- [ ] **DOC-04**: User can check out a document for editing and check in a new version
- [ ] **DOC-05**: User can transition a document's lifecycle state (Draft → Review → Approved → Archived) with confirmation

### Workflows

- [ ] **WF-01**: User can start a workflow by selecting a template, attaching documents, setting initial variables, and launching
- [ ] **WF-02**: User can view running workflow instances in a filterable, paginated list with state indicators
- [ ] **WF-03**: Admin can halt, resume, or terminate a workflow instance from the UI
- [ ] **WF-04**: User can view a workflow's progress on a read-only React Flow graph showing the current position

## Future Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Notifications

- **NOTF-01**: User receives real-time toast notifications when new work items arrive
- **NOTF-02**: Inbox badge count updates in real-time via WebSocket/SSE

### Document Enhancement

- **DOCE-01**: User can preview document content inline (PDF viewer, image preview)
- **DOCE-02**: User can add custom metadata properties to documents from the UI

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backend API changes | All APIs already exist from v1.0 -- this is frontend-only |
| Mobile-specific layouts | Web-responsive is sufficient per project constraints |
| Drag-and-drop file reordering | Over-engineering for v1.1; basic list is sufficient |
| Inline document preview | Requires PDF.js integration; defer to future |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| NAV-01 | Phase 12 | Pending |
| NAV-02 | Phase 12 | Pending |
| NAV-03 | Phase 12 | Complete |
| NAV-04 | Phase 12 | Complete |
| INB-01 | Phase 13 | Pending |
| INB-02 | Phase 13 | Pending |
| INB-03 | Phase 13 | Pending |
| INB-04 | Phase 13 | Pending |
| INB-05 | Phase 13 | Pending |
| INB-06 | Phase 13 | Pending |
| DOC-01 | Phase 14 | Pending |
| DOC-02 | Phase 14 | Pending |
| DOC-03 | Phase 14 | Pending |
| DOC-04 | Phase 14 | Pending |
| DOC-05 | Phase 14 | Pending |
| WF-01 | Phase 15 | Pending |
| WF-02 | Phase 15 | Pending |
| WF-03 | Phase 15 | Pending |
| WF-04 | Phase 15 | Pending |

**Coverage:**
- v1.1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---
*Requirements defined: 2026-04-06*
*Last updated: 2026-04-06 after roadmap creation*
