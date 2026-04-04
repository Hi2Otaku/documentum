# Roadmap: Documentum Workflow Clone

## Overview

This roadmap delivers a near-complete clone of OpenText Documentum's Workflow Management system in 11 phases. It starts with the data foundation and user management, builds the document management layer, then constructs the workflow template system and process engine core before adding user-facing inbox and advanced routing. Document lifecycle, ACL, and the visual designer follow once the engine is stable. Auto activities, delegation/queues, dashboards, and the contract approval validation example round out v1. Every phase delivers a coherent, verifiable capability that builds on prior phases.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & User Management** - Docker Compose stack, database schema, user/group/role management, and cross-cutting audit trail
- [x] **Phase 2: Document Management** - File upload, versioning, check-in/check-out, and MinIO storage (completed 2026-03-30)
- [ ] **Phase 3: Workflow Template Design (API)** - Process template CRUD with activities, flows, variables, triggers, validation, and versioning
- [ ] **Phase 4: Process Engine Core** - Workflow execution runtime with sequential/parallel routing, state machine, and work item creation
- [ ] **Phase 5: Work Items & Inbox** - User inbox with task completion, rejection, comments, and basic performer assignment
- [ ] **Phase 6: Advanced Routing & Alias Sets** - Conditional routing, reject flows, sequential/runtime performer selection, and alias set resolution
- [x] **Phase 7: Document Lifecycle & ACL** - Document state machine, workflow-triggered lifecycle transitions, and object-level access control (completed 2026-03-31)
- [ ] **Phase 8: Visual Workflow Designer** - Drag-and-drop React Flow canvas for designing workflow templates
- [ ] **Phase 9: Auto Activities, Workflow Agent & Integration** - Automated activity execution, Celery beat agent, and external REST API integration
- [ ] **Phase 10: Delegation, Work Queues & Workflow Management** - User delegation, shared task pools, and admin workflow control
- [x] **Phase 11: Dashboards, Query Interface & Validation** - BAM dashboards, admin query interface, and contract approval end-to-end example (completed 2026-04-04)

## Phase Details

### Phase 1: Foundation & User Management
**Goal**: The system runs as a containerized stack with a complete data model and working user/group management, with every mutation audit-logged from day one
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, USER-01, USER-02, USER-03, USER-04, AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04
**Success Criteria** (what must be TRUE):
  1. Running `docker compose up` starts FastAPI, PostgreSQL, Redis, MinIO, and Celery workers, and the API responds to health checks
  2. Database schema contains tables for the 5 core Documentum object types (Process, Activity, Flow, Package, WorkItem) with audit columns on all tables
  3. Admin can create users, create groups, assign users to groups, and define roles through the API
  4. User can log in with username/password and receive a session token that authenticates subsequent API requests
  5. Every create/update/delete operation produces an append-only audit record with who, what, when, and affected object
**Plans:** 3 plans
Plans:
- [x] 01-01-PLAN.md — Infrastructure, Docker Compose, FastAPI app, all SQLAlchemy models, Alembic setup
- [x] 01-02-PLAN.md — Auth (JWT), user/group/role CRUD APIs, audit trail service integration
- [x] 01-03-PLAN.md — Integration tests for all Phase 1 requirements

### Phase 2: Document Management
**Goal**: Users can upload, version, lock, and retrieve documents through the system with files stored in MinIO and metadata in PostgreSQL
**Depends on**: Phase 1
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, DOC-08
**Success Criteria** (what must be TRUE):
  1. User can upload a file of any type and see it listed in the document repository
  2. User can check out a document (locking it), edit it locally, and check it back in, creating a new version with correct major/minor numbering
  3. Admin can force-unlock a document that another user has checked out
  4. User can view the version history of a document and download any previous version
  5. Documents have extensible metadata (title, author, custom properties) that can be set and queried via the API
**Plans**: 3 plans
Plans:
- [x] 02-01-PLAN.md — Document models, MinIO client, config, Pydantic schemas
- [x] 02-02-PLAN.md — Document service layer and HTTP router
- [x] 02-03-PLAN.md — Integration tests for DOC-01 through DOC-08

### Phase 3: Workflow Template Design (API)
**Goal**: Users can create complete workflow templates through the API, including activities, flows, variables, triggers, and validation, with templates versioned so running instances are never affected by edits
**Depends on**: Phase 1
**Requirements**: TMPL-01, TMPL-02, TMPL-03, TMPL-04, TMPL-05, TMPL-06, TMPL-07, TMPL-08, TMPL-09, TMPL-10, TMPL-11
**Success Criteria** (what must be TRUE):
  1. User can create a workflow template with manual activities, auto activities, start/end markers, and flows connecting them
  2. User can define process variables (string, int, boolean, date) and conditional routing expressions on a template
  3. User can configure AND-join and OR-join triggers on activities with multiple incoming flows
  4. Validation endpoint detects structural errors (disconnected activities, missing performers, unreachable nodes) and rejects invalid templates
  5. Installing a template creates an immutable version; editing creates a new version without affecting the installed one
**Plans**: 3 plans
Plans:
- [x] 03-01-PLAN.md — Model updates (TriggerType enum, relationships, method_name) and Pydantic schemas
- [x] 03-02-PLAN.md — Template service layer (CRUD, validation, install, versioning) and HTTP router
- [x] 03-03-PLAN.md — Integration tests for TMPL-01 through TMPL-11

### Phase 4: Process Engine Core
**Goal**: The process engine can start workflow instances from templates and automatically advance them through sequential and parallel paths, creating work items for manual activities
**Depends on**: Phase 1, Phase 3
**Requirements**: EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05, EXEC-06, EXEC-07, EXEC-12, EXEC-13, EXEC-14
**Success Criteria** (what must be TRUE):
  1. User can start a workflow instance from an installed template, attaching documents and assigning alias performers
  2. Workflow instance transitions through states (Dormant, Running, Halted, Failed, Finished) with correct state machine enforcement
  3. Sequential routing works: completing activity A activates activity B, then C, in order
  4. Parallel routing works: an AND-split activates multiple activities simultaneously, and the AND-join waits for all to complete before proceeding
  5. Process variables can be read and written by activities during execution and used in routing condition expressions
**Plans:** 3 plans
Plans:
- [x] 04-01-PLAN.md — Models (ActivityState, ExecutionToken, relationships), schemas, expression evaluator
- [x] 04-02-PLAN.md — Engine service (instantiation, advancement, tokens) and workflow router
- [x] 04-03-PLAN.md — Integration tests for EXEC-01 through EXEC-14
### Phase 5: Work Items & Inbox
**Goal**: Users have a functional inbox where they can view, complete, and reject tasks generated by the workflow engine, with basic performer assignment routing tasks to the right users
**Depends on**: Phase 4
**Requirements**: INBOX-01, INBOX-02, INBOX-03, INBOX-04, INBOX-05, INBOX-06, INBOX-07, PERF-01, PERF-02, PERF-03
**Success Criteria** (what must be TRUE):
  1. When the engine activates a manual activity, a work item appears in the assigned performer's inbox
  2. User can view their inbox with pending tasks, filter and sort them, and see priority and due date indicators
  3. User can open a work item, view attached documents and activity details, and add comments
  4. User can complete (forward) a work item, which advances the workflow to the next activity
  5. Activities correctly route to the workflow supervisor, a specific user, or users from a group based on performer configuration
**Plans:** 3 plans
Plans:
- [x] 05-01-PLAN.md — REJECTED enum, WorkItemComment model, inbox schemas, performer resolution in engine
- [x] 05-02-PLAN.md — Inbox service layer and HTTP router (8 endpoints)
- [x] 05-03-PLAN.md — Integration tests for INBOX-01 through INBOX-07 and PERF-01 through PERF-03
**UI hint**: yes

### Phase 6: Advanced Routing & Alias Sets
**Goal**: The engine supports all Documentum routing patterns including conditional paths, reject flows, advanced performer assignment, and alias-based performer resolution
**Depends on**: Phase 4, Phase 5
**Requirements**: EXEC-08, EXEC-09, EXEC-10, EXEC-11, PERF-04, PERF-05, ALIAS-01, ALIAS-02, ALIAS-03
**Success Criteria** (what must be TRUE):
  1. Performer-chosen conditional routing works: the completing user selects which outgoing path the workflow takes
  2. Condition-based routing works: the engine evaluates expressions against process variables to determine the next activity
  3. Reject flow works: a performer can reject a task, causing the workflow to loop back to a previous activity
  4. Sequential performers and runtime selection assignment modes correctly route tasks through ordered lists or let the previous performer choose the next
  5. Alias sets can be created, assigned to templates, and updated without editing the template, with the engine resolving aliases to actual users at runtime
**Plans**: 3 plans
Plans:
- [ ] 02-01-PLAN.md — Document models, MinIO client, config, Pydantic schemas
- [ ] 02-02-PLAN.md — Document service layer and HTTP router
- [ ] 02-03-PLAN.md — Integration tests for DOC-01 through DOC-08

### Phase 7: Document Lifecycle & ACL
**Goal**: Documents transition through defined lifecycle states with workflow-triggered transitions, and object-level permissions automatically change at workflow steps
**Depends on**: Phase 2, Phase 4
**Requirements**: LIFE-01, LIFE-02, LIFE-03, LIFE-04, ACL-01, ACL-02, ACL-03, ACL-04
**Success Criteria** (what must be TRUE):
  1. Documents transition through Draft, Review, Approved, and Archived states with transitions enforced by the lifecycle rules
  2. Completing a workflow activity can automatically trigger a document lifecycle transition (e.g., approval activity moves document from Review to Approved)
  3. ACL permissions automatically change when lifecycle state changes (e.g., document becomes read-only after Approved)
  4. Permission checks are enforced on all API operations, preventing unauthorized read/write/delete
  5. All lifecycle transitions and ACL changes are recorded in the audit trail
**Plans:** 3/3 plans complete
Plans:
- [x] 07-01-PLAN.md — Enums, models, schemas, lifecycle service, ACL service
- [x] 07-02-PLAN.md — Engine lifecycle hook, permission dependency, route protection
- [x] 07-03-PLAN.md — Integration tests for LIFE-01 through LIFE-04 and ACL-01 through ACL-04
### Phase 8: Visual Workflow Designer
**Goal**: Users can design workflow templates through a web-based drag-and-drop interface instead of raw API calls
**Depends on**: Phase 3
**Requirements**: DESIGN-01, DESIGN-02, DESIGN-03, DESIGN-04, DESIGN-05, DESIGN-06, DESIGN-07
**Success Criteria** (what must be TRUE):
  1. User can open a web-based canvas and drag activity nodes (Manual, Auto, Start, End) onto it
  2. User can draw flow connections (Normal Flow, Reject Flow) between activities by clicking and dragging
  3. User can configure activity properties (performer assignment, trigger conditions, routing expressions) through a side panel
  4. Designer validates the template before installation and shows structural errors visually on the canvas
  5. Templates designed in the visual editor save to and load from the backend API, and can be executed by the engine
**Plans**: 3 plans
Plans:
- [ ] 02-01-PLAN.md — Document models, MinIO client, config, Pydantic schemas
- [ ] 02-02-PLAN.md — Document service layer and HTTP router
- [ ] 02-03-PLAN.md — Integration tests for DOC-01 through DOC-08
**UI hint**: yes

### Phase 9: Auto Activities, Workflow Agent & Integration
**Goal**: Automated activities execute server-side Python methods without human intervention, and external systems can trigger and interact with workflows via REST API
**Depends on**: Phase 4
**Requirements**: AUTO-01, AUTO-02, AUTO-03, AUTO-04, AUTO-05, INTG-01, INTG-02, INTG-03
**Success Criteria** (what must be TRUE):
  1. Auto activities execute registered Python methods (send email, change lifecycle state, move documents, modify ACLs, call external APIs) without human intervention
  2. Workflow Agent (Celery beat worker) continuously polls for and executes queued auto activities with timeout and retry logic
  3. Failed auto activities are logged with error details and can be retried or skipped by an administrator
  4. External systems can start workflows, complete work items, and reject work items through documented REST API endpoints
**Plans**: 3 plans
Plans:
- [ ] 02-01-PLAN.md — Document models, MinIO client, config, Pydantic schemas
- [ ] 02-02-PLAN.md — Document service layer and HTTP router
- [ ] 02-03-PLAN.md — Integration tests for DOC-01 through DOC-08

### Phase 10: Delegation, Work Queues & Workflow Management
**Goal**: Users can delegate tasks when unavailable, shared work queues allow any qualified user to claim tasks, and admins can halt, resume, and abort workflow instances
**Depends on**: Phase 5
**Requirements**: USER-05, INBOX-08, QUEUE-01, QUEUE-02, QUEUE-03, QUEUE-04, MGMT-01, MGMT-02, MGMT-03, MGMT-04, MGMT-05, AUDIT-05
**Success Criteria** (what must be TRUE):
  1. User can mark themselves as unavailable and designate a delegate; new tasks automatically route to the delegate
  2. Admin can create work queues, assign qualified users, and activities assigned to a queue appear for all qualified users to claim
  3. Claimed tasks are locked to the claiming user until released or completed, preventing double-work
  4. Admin can halt a running workflow, resume a halted workflow, abort a workflow, and restart a failed workflow from Dormant state
  5. Admin can view all running workflow instances with current state and active activity, and query the audit trail by user, workflow, document, date range, or action type
**Plans**: 3 plans
Plans:
- [ ] 02-01-PLAN.md — Document models, MinIO client, config, Pydantic schemas
- [ ] 02-02-PLAN.md — Document service layer and HTTP router
- [ ] 02-03-PLAN.md — Integration tests for DOC-01 through DOC-08
**UI hint**: yes

### Phase 11: Dashboards, Query Interface & Validation
**Goal**: Admins have BAM dashboards for process metrics, a query interface for administration, and the contract approval example proves the entire system works end-to-end
**Depends on**: Phase 9, Phase 10
**Requirements**: BAM-01, BAM-02, BAM-03, BAM-04, BAM-05, QUERY-01, QUERY-02, QUERY-03, EXAMPLE-01, EXAMPLE-02, EXAMPLE-03
**Success Criteria** (what must be TRUE):
  1. Dashboard shows real-time counts of running, halted, finished, and failed workflows, plus average completion time per template
  2. Dashboard identifies bottleneck activities and shows workload per user and SLA compliance rate
  3. Admin can query workflow instances, work items, and documents by multiple criteria (template, state, date range, performer, metadata, lifecycle state)
  4. The pre-built contract approval template (7 steps: initiate, draft, parallel legal/financial review, director approval, digital signing, archival, end) can be executed end-to-end with test users
  5. The contract approval example demonstrates sequential, parallel, and conditional routing, reject flows, auto activities, and produces a complete audit trail
**Plans:** 7/7 plans complete
Plans:
- [x] 11-01-PLAN.md — Dashboard backend (services, router, schemas) and frontend (KPI cards, charts, SSE hook)
- [x] 11-02-PLAN.md — Query interface backend (query service, router) and frontend (three-tab query page)
- [x] 11-03-PLAN.md — Contract approval seed script and E2E test
- [x] 11-04-PLAN.md — Integration tests for dashboard and query services
- [x] 11-05-PLAN.md — Frontend query components (QueryResultTable, tab components)
- [x] 11-06-PLAN.md — Gap closure: restore audit router, fix dashboard admin auth
- [x] 11-07-PLAN.md — Gap closure: unified /metrics endpoint, SLA compliance, SSE /stream, Celery aggregation
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> ... -> 11

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & User Management | 0/3 | Planning complete | - |
| 2. Document Management | 3/3 | Complete   | 2026-03-30 |
| 3. Workflow Template Design (API) | 0/3 | Planning complete | - |
| 4. Process Engine Core | 0/3 | Planning complete | - |
| 5. Work Items & Inbox | 0/3 | Planning complete | - |
| 6. Advanced Routing & Alias Sets | 0/3 | Planning complete | - |
| 7. Document Lifecycle & ACL | 3/3 | Complete   | 2026-03-31 |
| 8. Visual Workflow Designer | 0/TBD | Not started | - |
| 9. Auto Activities, Workflow Agent & Integration | 0/TBD | Not started | - |
| 10. Delegation, Work Queues & Workflow Management | 0/TBD | Not started | - |
| 11. Dashboards, Query Interface & Validation | 7/7 | Complete   | 2026-04-04 |
