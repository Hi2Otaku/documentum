# Requirements: Documentum Workflow Clone

**Defined:** 2026-03-30
**Core Value:** Every workflow use case in the Documentum specification can be modeled and executed end-to-end

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [x] **FOUND-01**: System runs via Docker Compose with FastAPI, PostgreSQL, Redis, MinIO, and Celery workers
- [x] **FOUND-02**: Database schema implements the 5 core Documentum object types: Process, Activity, Flow, Package, WorkItem
- [x] **FOUND-03**: All schema tables include created_at, updated_at, and created_by audit columns

### User Management

- [x] **USER-01**: Admin can create user accounts with username and password
- [x] **USER-02**: User can log in and receive a session token
- [x] **USER-03**: Admin can create groups and assign users to groups
- [x] **USER-04**: Admin can define roles (e.g., Reviewer, Approver, Director)
- [ ] **USER-05**: User can mark themselves as unavailable and designate a delegate

### Document Management

- [x] **DOC-01**: User can upload documents (any file type) to the repository
- [x] **DOC-02**: System tracks document versions with major (1.0, 2.0) and minor (1.1, 1.2) numbering
- [x] **DOC-03**: User can check out a document (locks it for editing)
- [x] **DOC-04**: User can check in a document (creates new version, releases lock)
- [x] **DOC-05**: Admin can force-unlock a checked-out document
- [x] **DOC-06**: User can view and download any version of a document
- [x] **DOC-07**: Documents have extensible metadata (title, author, custom properties)
- [x] **DOC-08**: Documents are stored in MinIO with metadata in PostgreSQL

### Document Lifecycle

- [ ] **LIFE-01**: Documents transition through defined states: Draft → Review → Approved → Archived
- [ ] **LIFE-02**: Lifecycle transitions can be triggered automatically by workflow activity completion
- [ ] **LIFE-03**: Lifecycle state changes are recorded in the audit trail
- [ ] **LIFE-04**: ACL permissions automatically change when lifecycle state changes (e.g., read-only after Approved)

### Workflow Template Design

- [x] **TMPL-01**: User can create a workflow template (dm_process equivalent) with a name and description
- [x] **TMPL-02**: User can add Manual Activities to a template with performer assignment configuration
- [x] **TMPL-03**: User can add Auto Activities to a template with a Python method reference
- [x] **TMPL-04**: User can connect activities with Normal Flows (forward) and Reject Flows (backward)
- [x] **TMPL-05**: User can define process variables (string, int, boolean, date types) on a template
- [x] **TMPL-06**: User can configure trigger conditions on activities: AND-join (all incoming) or OR-join (any incoming)
- [x] **TMPL-07**: User can configure conditional routing with expressions based on process variables
- [ ] **TMPL-08**: User can validate a template (check connectivity, performer assignment, unreachable activities)
- [ ] **TMPL-09**: User can install (activate) a validated template, making it available for use
- [ ] **TMPL-10**: Installed templates are versioned — editing creates a new version without affecting running instances
- [x] **TMPL-11**: Template supports Start Activity and End Activity markers

### Alias Sets

- [ ] **ALIAS-01**: User can create an Alias Set mapping logical roles to actual users/groups
- [ ] **ALIAS-02**: Alias Sets can be assigned to workflow templates for flexible performer assignment
- [ ] **ALIAS-03**: Updating an alias mapping does not require editing the workflow template

### Performer Assignment

- [ ] **PERF-01**: Activity can be assigned to Workflow Supervisor (workflow initiator)
- [ ] **PERF-02**: Activity can be assigned to a Specific User
- [ ] **PERF-03**: Activity can be assigned to users from a Group (parallel execution)
- [ ] **PERF-04**: Activity can use Multiple Sequential Performers (ordered list, can reject back)
- [ ] **PERF-05**: Activity can use Runtime Selection (previous performer chooses next)

### Workflow Execution

- [ ] **EXEC-01**: User can start a workflow instance from an installed template
- [ ] **EXEC-02**: User attaches documents to the workflow package at startup
- [ ] **EXEC-03**: User assigns performers for aliases (if Alias Set is used) at startup
- [ ] **EXEC-04**: Workflow instance transitions through states: Dormant → Running → Halted → Failed → Finished
- [ ] **EXEC-05**: Process Engine automatically advances workflow by evaluating flows and activating next activities
- [ ] **EXEC-06**: Sequential routing: activities execute one after another (A → B → C)
- [ ] **EXEC-07**: Parallel routing: activities execute simultaneously after a split, with AND-join at convergence
- [ ] **EXEC-08**: Conditional routing (performer-chosen): performer selects which path to take
- [ ] **EXEC-09**: Conditional routing (condition-based): system evaluates expressions to determine next activity
- [ ] **EXEC-10**: Conditional routing (broadcast): all connected activities are activated simultaneously
- [ ] **EXEC-11**: Reject flow: performer rejects task, document returns to previous activity
- [ ] **EXEC-12**: OR-join trigger: activity starts when any one incoming flow completes
- [ ] **EXEC-13**: Process variables can be read and written by activities during execution
- [ ] **EXEC-14**: Process variables can be used in routing condition expressions

### Work Items & Inbox

- [ ] **INBOX-01**: When an activity is activated, a work item appears in the assigned performer's inbox
- [ ] **INBOX-02**: User can view their inbox with all pending tasks (filterable, sortable)
- [ ] **INBOX-03**: User can open a work item to view attached documents and activity details
- [ ] **INBOX-04**: User can complete (forward) a work item, advancing the workflow
- [ ] **INBOX-05**: User can reject a work item (triggers reject flow if configured)
- [ ] **INBOX-06**: User can add comments to a work item
- [ ] **INBOX-07**: Work items show priority and due date indicators
- [ ] **INBOX-08**: If performer is unavailable, work item automatically routes to delegated user

### Work Queues

- [ ] **QUEUE-01**: Admin can create work queues and assign qualified users
- [ ] **QUEUE-02**: Activities can be assigned to a work queue instead of a specific user
- [ ] **QUEUE-03**: Any qualified user in the queue can claim a task
- [ ] **QUEUE-04**: Claimed tasks are locked to the claiming user until released or completed

### Auto Activities & Workflow Agent

- [ ] **AUTO-01**: Auto activities execute Python methods (equivalent of dm_method) without human intervention
- [ ] **AUTO-02**: Workflow Agent (Celery worker) continuously scans for auto activities to execute
- [ ] **AUTO-03**: Auto activities can: send emails, change lifecycle state, move documents to folders, modify ACLs, call external APIs
- [ ] **AUTO-04**: Workflow Agent logs execution results and handles errors (retry, fail)
- [ ] **AUTO-05**: Failed auto activities can be retried or skipped by an administrator

### Workflow Management

- [ ] **MGMT-01**: Admin can halt a running workflow (pause execution)
- [ ] **MGMT-02**: Admin can resume a halted workflow
- [ ] **MGMT-03**: Admin can abort a workflow (terminate, mark as Failed)
- [ ] **MGMT-04**: Admin can view all running workflow instances with current state and active activity
- [ ] **MGMT-05**: Admin can restart a failed workflow from Dormant state

### ACL & Security

- [ ] **ACL-01**: Objects (documents, workflows) have Access Control Lists defining who can read/write/delete
- [ ] **ACL-02**: Workflow activities can automatically modify document ACLs (e.g., remove write after approval)
- [ ] **ACL-03**: ACL changes are recorded in the audit trail
- [ ] **ACL-04**: Permission checks are enforced on all API operations

### Audit Trail

- [x] **AUDIT-01**: Every workflow action is logged: who, what, when, decision, and affected objects
- [x] **AUDIT-02**: Audit records include: task assignment, task completion, task rejection, workflow state changes
- [x] **AUDIT-03**: Audit records include: document upload, version creation, check-in/out, lifecycle transitions
- [x] **AUDIT-04**: Audit trail is append-only and cannot be modified or deleted
- [ ] **AUDIT-05**: Admin can query audit trail by user, workflow, document, date range, or action type

### Visual Workflow Designer

- [ ] **DESIGN-01**: Web-based drag-and-drop canvas for designing workflow templates (React Flow)
- [ ] **DESIGN-02**: User can drag activity nodes (Manual, Auto, Start, End) onto the canvas
- [ ] **DESIGN-03**: User can draw flow connections (Normal Flow, Reject Flow) between activities
- [ ] **DESIGN-04**: User can configure activity properties (performer, trigger, conditions) via side panel
- [ ] **DESIGN-05**: User can define process variables via the designer
- [ ] **DESIGN-06**: Designer validates the template and shows errors before installation
- [ ] **DESIGN-07**: Designer saves/loads templates to/from the backend API

### BAM Dashboards & Monitoring

- [ ] **BAM-01**: Dashboard shows count of running, halted, finished, and failed workflows
- [ ] **BAM-02**: Dashboard shows average completion time per workflow template
- [ ] **BAM-03**: Dashboard identifies bottleneck activities (longest average duration)
- [ ] **BAM-04**: Dashboard shows workload per user (tasks assigned, completed, pending)
- [ ] **BAM-05**: Dashboard shows SLA compliance rate (tasks completed within configured time limits)

### External Integration

- [ ] **INTG-01**: Auto activities can call external REST APIs (webhook-based)
- [ ] **INTG-02**: External systems can trigger workflow start via REST API
- [ ] **INTG-03**: External systems can complete/reject work items via REST API

### Query Interface

- [ ] **QUERY-01**: Admin can query workflow instances by template, state, date range, performer
- [ ] **QUERY-02**: Admin can query work items by assignee, state, workflow, priority
- [ ] **QUERY-03**: Admin can query documents by metadata, lifecycle state, version

### Contract Approval Example

- [ ] **EXAMPLE-01**: Pre-built contract approval template matching the 7-step example from the spec
- [ ] **EXAMPLE-02**: Example demonstrates: sequential routing (draft), parallel routing (legal + financial review), conditional routing (director approval), reject flows, auto activities (signing, archival)
- [ ] **EXAMPLE-03**: Example can be executed end-to-end with test users, producing a complete audit trail

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Notifications

- **NOTIF-01**: User receives in-app notification when a task is assigned
- **NOTIF-02**: User receives email notification for new tasks (configurable)
- **NOTIF-03**: User receives notification when a workflow they initiated completes
- **NOTIF-04**: Configurable notification preferences per user

### Advanced Security

- **SEC-01**: Digital signature support at approval activities
- **SEC-02**: Activity-level security (control who can see specific activities)
- **SEC-03**: IP-based access restrictions

### Advanced Analytics

- **ANALYTICS-01**: Historical trend analysis of workflow performance
- **ANALYTICS-02**: Predictive completion time estimates
- **ANALYTICS-03**: Exportable reports (CSV, PDF)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| BPMN 2.0 import/export | Enormous spec; this uses its own Documentum-inspired model |
| AI process optimization | Hype-driven, unclear value for internal tool |
| Low-code form builder | Scope explosion; use configurable JSON forms |
| Industry templates (xCelerators) | Domain-specific; contract approval example is sufficient |
| Mobile native app | Responsive web UI is sufficient |
| Legacy protocols (JMS, SOAP, FTP) | Modern REST/webhook instead |
| Multi-tenant SaaS | Internal/personal use only |
| Process simulation | Focus on real execution metrics |
| Case management (CMMN) | Different paradigm from structured workflows |
| DMN decision tables | Expression-based routing is sufficient |
| Real-time co-editing | Check-in/check-out locking is sufficient |
| Full-text search (Solr/ES) | Metadata search covers needs; add later if needed |
| OAuth/SSO | Simple built-in auth is sufficient for internal use |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| USER-01 | Phase 1 | Complete |
| USER-02 | Phase 1 | Complete |
| USER-03 | Phase 1 | Complete |
| USER-04 | Phase 1 | Complete |
| USER-05 | Phase 10 | Pending |
| DOC-01 | Phase 2 | Complete |
| DOC-02 | Phase 2 | Complete |
| DOC-03 | Phase 2 | Complete |
| DOC-04 | Phase 2 | Complete |
| DOC-05 | Phase 2 | Complete |
| DOC-06 | Phase 2 | Complete |
| DOC-07 | Phase 2 | Complete |
| DOC-08 | Phase 2 | Complete |
| LIFE-01 | Phase 7 | Pending |
| LIFE-02 | Phase 7 | Pending |
| LIFE-03 | Phase 7 | Pending |
| LIFE-04 | Phase 7 | Pending |
| TMPL-01 | Phase 3 | Complete |
| TMPL-02 | Phase 3 | Complete |
| TMPL-03 | Phase 3 | Complete |
| TMPL-04 | Phase 3 | Complete |
| TMPL-05 | Phase 3 | Complete |
| TMPL-06 | Phase 3 | Complete |
| TMPL-07 | Phase 3 | Complete |
| TMPL-08 | Phase 3 | Pending |
| TMPL-09 | Phase 3 | Pending |
| TMPL-10 | Phase 3 | Pending |
| TMPL-11 | Phase 3 | Complete |
| ALIAS-01 | Phase 6 | Pending |
| ALIAS-02 | Phase 6 | Pending |
| ALIAS-03 | Phase 6 | Pending |
| PERF-01 | Phase 5 | Pending |
| PERF-02 | Phase 5 | Pending |
| PERF-03 | Phase 5 | Pending |
| PERF-04 | Phase 6 | Pending |
| PERF-05 | Phase 6 | Pending |
| EXEC-01 | Phase 4 | Pending |
| EXEC-02 | Phase 4 | Pending |
| EXEC-03 | Phase 4 | Pending |
| EXEC-04 | Phase 4 | Pending |
| EXEC-05 | Phase 4 | Pending |
| EXEC-06 | Phase 4 | Pending |
| EXEC-07 | Phase 4 | Pending |
| EXEC-08 | Phase 6 | Pending |
| EXEC-09 | Phase 6 | Pending |
| EXEC-10 | Phase 6 | Pending |
| EXEC-11 | Phase 6 | Pending |
| EXEC-12 | Phase 4 | Pending |
| EXEC-13 | Phase 4 | Pending |
| EXEC-14 | Phase 4 | Pending |
| INBOX-01 | Phase 5 | Pending |
| INBOX-02 | Phase 5 | Pending |
| INBOX-03 | Phase 5 | Pending |
| INBOX-04 | Phase 5 | Pending |
| INBOX-05 | Phase 5 | Pending |
| INBOX-06 | Phase 5 | Pending |
| INBOX-07 | Phase 5 | Pending |
| INBOX-08 | Phase 10 | Pending |
| QUEUE-01 | Phase 10 | Pending |
| QUEUE-02 | Phase 10 | Pending |
| QUEUE-03 | Phase 10 | Pending |
| QUEUE-04 | Phase 10 | Pending |
| AUTO-01 | Phase 9 | Pending |
| AUTO-02 | Phase 9 | Pending |
| AUTO-03 | Phase 9 | Pending |
| AUTO-04 | Phase 9 | Pending |
| AUTO-05 | Phase 9 | Pending |
| MGMT-01 | Phase 10 | Pending |
| MGMT-02 | Phase 10 | Pending |
| MGMT-03 | Phase 10 | Pending |
| MGMT-04 | Phase 10 | Pending |
| MGMT-05 | Phase 10 | Pending |
| ACL-01 | Phase 7 | Pending |
| ACL-02 | Phase 7 | Pending |
| ACL-03 | Phase 7 | Pending |
| ACL-04 | Phase 7 | Pending |
| AUDIT-01 | Phase 1 | Complete |
| AUDIT-02 | Phase 1 | Complete |
| AUDIT-03 | Phase 1 | Complete |
| AUDIT-04 | Phase 1 | Complete |
| AUDIT-05 | Phase 10 | Pending |
| DESIGN-01 | Phase 8 | Pending |
| DESIGN-02 | Phase 8 | Pending |
| DESIGN-03 | Phase 8 | Pending |
| DESIGN-04 | Phase 8 | Pending |
| DESIGN-05 | Phase 8 | Pending |
| DESIGN-06 | Phase 8 | Pending |
| DESIGN-07 | Phase 8 | Pending |
| BAM-01 | Phase 11 | Pending |
| BAM-02 | Phase 11 | Pending |
| BAM-03 | Phase 11 | Pending |
| BAM-04 | Phase 11 | Pending |
| BAM-05 | Phase 11 | Pending |
| INTG-01 | Phase 9 | Pending |
| INTG-02 | Phase 9 | Pending |
| INTG-03 | Phase 9 | Pending |
| QUERY-01 | Phase 11 | Pending |
| QUERY-02 | Phase 11 | Pending |
| QUERY-03 | Phase 11 | Pending |
| EXAMPLE-01 | Phase 11 | Pending |
| EXAMPLE-02 | Phase 11 | Pending |
| EXAMPLE-03 | Phase 11 | Pending |

**Coverage:**
- v1 requirements: 105 total
- Mapped to phases: 105
- Unmapped: 0

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 after roadmap creation*
