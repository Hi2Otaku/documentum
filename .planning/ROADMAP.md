# Roadmap: Documentum Workflow Clone

## Milestones

- ✅ **v1.0 Core Engine** — Phases 1-11 (shipped)
- ✅ **v1.1 Full Frontend Experience** — Phases 12-15 (shipped 2026-04-06)
- ✅ **v1.2 Advanced Engine & Document Platform** — Phases 16-26 (shipped 2026-04-13)
- ✅ **v1.3 Document-Centric ECM** — Phases 27-33 (shipped 2026-04-14)
- 🚧 **v1.4 Enterprise Completeness** — Phases 34-44 (in progress)

## Phases

<details>
<summary>✅ v1.0 Core Engine (Phases 1-11) — SHIPPED</summary>

Phases 1-11 delivered the complete workflow engine backend: Docker stack, database schema, authentication, audit trail, document management, workflow templates, process engine, visual designer, lifecycle/ACL integration, auto activities, delegation, work queues, BAM dashboards, and the contract approval demo workflow.

</details>

<details>
<summary>✅ v1.1 Full Frontend Experience (Phases 12-15) — SHIPPED 2026-04-06</summary>

Phases 12-15 delivered the complete web UI: navigation shell, inbox with work item management, document management pages, and workflow operations with start wizard and progress visualization.

</details>

<details>
<summary>✅ v1.2 Advanced Engine & Document Platform (Phases 16-26) — SHIPPED 2026-04-13</summary>

- [x] Phase 16: Notifications & Event Bus (4/4 plans) — 2026-04-06
- [x] Phase 17: Timer Activities & Escalation (3/3 plans) — 2026-04-06
- [x] Phase 18: Sub-Workflows (3/3 plans) — 2026-04-06
- [x] Phase 19: Event-Driven Activities (2/2 plans) — 2026-04-06
- [x] Phase 20: Document Renditions (3/3 plans) — 2026-04-06
- [x] Phase 21: Virtual Documents (2/2 plans) — 2026-04-06
- [x] Phase 22: Retention & Records Management (2/2 plans) — 2026-04-06
- [x] Phase 23: Digital Signatures (2/2 plans) — 2026-04-06
- [x] Phase 24: Infrastructure Wiring & Event Bus Integration (3/3 plans) — 2026-04-07
- [x] Phase 25: Virtual Documents Frontend Fix (1/1 plan) — 2026-04-07
- [x] Phase 26: Digital Signatures Alignment (1/1 plan) — 2026-04-07

See `.planning/milestones/v1.3-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v1.3 Document-Centric ECM (Phases 27-33) — SHIPPED 2026-04-14</summary>

Phases 27-33 delivered document-centric ECM: custom document types with JSON Schema validation, cabinet/folder hierarchy with tree navigation, folder ACL inheritance, full-text search with content extraction, document relationships, document-first browse UI, and saved searches with smart folders. 7 phases, 19 plans, 22 requirements fulfilled.

See `.planning/milestones/v1.3-ROADMAP.md` for full phase details.

</details>

### v1.4 Enterprise Completeness (In Progress)

**Milestone Goal:** Close all functional gaps identified in the Documentum comparison audit -- wire up existing backend features to the frontend, and build the missing enterprise capabilities (SSO, CMIS, bulk operations, workflow resilience, desktop integration, and operational tooling).

- [x] **Phase 34: Frontend Gap Closure** - Wire 6 existing backend features to the web UI and fix lifecycle filter (completed 2026-04-15)
- [x] **Phase 35: Tamper-Proof Audit Trail** - Cryptographic hash chaining for audit log integrity (completed 2026-04-15)
- [x] **Phase 36: Identity & SSO** - LDAP/SAML/OAuth2 authentication with JIT provisioning and service tokens (completed 2026-04-15)
- [x] **Phase 37: Workflow Error Handling & Compensation** - Declarative exception handlers and rollback activities (completed 2026-04-15)
- [x] **Phase 38: Workflow Versioning** - Concurrent active template versions with immutable installed snapshots (completed 2026-04-15)
- [x] **Phase 39: Advanced Join Semantics** - N-of-M, cancelling, timeout joins with race-condition-free locking (completed 2026-04-15)
- [x] **Phase 40: Bulk Operations** - Mass update, delete, reclassify with background job tracking (completed 2026-04-15)
- [ ] **Phase 41: Import/Export** - ZIP package export/import with hierarchy preservation and conflict resolution
- [ ] **Phase 42: System Monitoring & Health** - Deep health checks, queue metrics, Prometheus endpoint, alerting
- [ ] **Phase 43: CMIS Standard API** - OASIS CMIS 1.1 Browser Binding for content interoperability
- [ ] **Phase 44: Process Analytics & Mining** - Execution path discovery, cycle time analysis, bottleneck identification

## Phase Details

### Phase 34: Frontend Gap Closure
**Goal**: Users can access all existing backend capabilities (signatures, retention, document ACLs, queues, lifecycle filter, notification preferences) through the web UI
**Depends on**: Phase 33 (v1.3 complete)
**Requirements**: FEGAP-01, FEGAP-02, FEGAP-03, FEGAP-04, FEGAP-05, FEGAP-06, FEGAP-07, FEGAP-08
**Success Criteria** (what must be TRUE):
  1. User can sign a document with a digital certificate and view signature details (signer, timestamp, validity) from the document detail page
  2. Admin can create retention policies, assign them to documents, and place/release legal holds from a management UI
  3. User can add and remove ACL entries (users/groups with permission levels) on individual documents from the UI
  4. Admin can create, edit, and delete work queues and manage queue membership from a dedicated admin page
  5. User can filter the documents list by lifecycle state (Draft/Review/Approved/Archived) and the filter actually produces results; user can configure which event types trigger notifications in a preferences panel
**Plans**: 4 plans

Plans:
- [ ] 34-01-PLAN.md — Lifecycle state filter fix + Document ACL panel
- [ ] 34-02-PLAN.md — Retention admin page + Queue admin page + routing
- [ ] 34-03-PLAN.md — Digital signatures UI + Retention status panel on document detail
- [ ] 34-04-PLAN.md — Notification preferences backend + frontend

**UI hint**: yes

### Phase 35: Tamper-Proof Audit Trail
**Goal**: Audit logs are cryptographically chained so tampering or gaps are detectable
**Depends on**: Phase 34
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03
**Success Criteria** (what must be TRUE):
  1. Every new audit record includes a SHA-256 hash incorporating its content and the previous record's hash, forming an unbroken chain
  2. Admin can trigger an audit trail integrity verification from the UI and see a clear pass/fail result with details of any breaks
  3. Hash computation runs asynchronously (Celery worker) so write throughput to the main application is not degraded
**Plans**: 2 plans

Plans:
- [x] 35-01-PLAN.md -- DB migration + model + Celery hash chaining task
- [x] 35-02-PLAN.md -- Verification API endpoint + admin verification UI

**UI hint**: yes

### Phase 36: Identity & SSO
**Goal**: Users can authenticate via enterprise identity providers (LDAP, SAML, OAuth2/OIDC) alongside existing local auth, with background services using service tokens
**Depends on**: Phase 35
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06
**Success Criteria** (what must be TRUE):
  1. Admin can configure an LDAP directory connection and map LDAP groups to system groups from an admin settings page
  2. User can log in via SAML 2.0 redirect flow and via OAuth2/OIDC authorization code flow with PKCE, landing in the application with a valid session
  3. A user authenticating via SSO for the first time is automatically provisioned (JIT) with correct group memberships
  4. Existing local username/password login continues to work unchanged when SSO providers are configured
  5. Celery workers and the Workflow Agent authenticate using service tokens that do not require a browser flow
**Plans**: 3 plans

Plans:
- [x] 36-01-PLAN.md — Auth backend abstraction + service tokens + DB migration
- [x] 36-02-PLAN.md — LDAP/SAML/OIDC identity service + SSO endpoints
- [x] 36-03-PLAN.md — Admin SSO settings page + Login page SSO buttons

**UI hint**: yes

### Phase 37: Workflow Error Handling & Compensation
**Goal**: Workflow designers can define how workflows recover from failures, and operators can intervene on failed activities
**Depends on**: Phase 36
**Requirements**: WFERR-01, WFERR-02, WFERR-03, WFERR-04
**Success Criteria** (what must be TRUE):
  1. Template designer can attach an error handler activity to any activity in the workflow designer, and the engine executes it when that activity fails
  2. Template designer can define compensation activities that undo completed work, and the engine runs them in reverse chronological order when a flow-level failure triggers compensation
  3. Failed activities display error details in the workflow operations UI and allow an operator to retry or skip the failed activity
**Plans**: 3 plans

Plans:
- [x] 37-01-PLAN.md — DB migration + models + engine error handler & compensation logic
- [ ] 37-02-PLAN.md — Operator UI: error details, retry/skip, compensation trigger
- [x] 37-03-PLAN.md — Designer UI: error handler & compensation activity selection

**UI hint**: yes

### Phase 38: Workflow Versioning
**Goal**: Multiple template versions can coexist -- new instances use latest, running instances stay on their original version
**Depends on**: Phase 37
**Requirements**: WFVER-01, WFVER-02, WFVER-03
**Success Criteria** (what must be TRUE):
  1. Admin can install a new version of a template while instances of the previous version continue running without interruption
  2. Starting a new workflow always uses the latest installed version; existing running instances reference their original immutable template snapshot
  3. Admin can view which template version each running workflow instance is using from the workflow operations UI
**Plans**: 2 plans

Plans:
- [x] 38-01-PLAN.md -- Backend: template_family_id migration, family-based install/start, version API
- [x] 38-02-PLAN.md -- Frontend: version column in workflow table, version badge in designer & template list
**UI hint**: yes

### Phase 39: Advanced Join Semantics
**Goal**: Workflow designers can model complex synchronization patterns beyond basic AND/OR joins, with race-condition-free execution
**Depends on**: Phase 38
**Requirements**: JOIN-01, JOIN-02, JOIN-03, JOIN-04
**Success Criteria** (what must be TRUE):
  1. Template designer can configure an N-of-M join that activates when a specified number of incoming flows complete (not necessarily all)
  2. Template designer can configure a cancelling join that cancels remaining branches when the join fires, and a timeout join that fires after a configured duration even if not all branches have completed
  3. Concurrent token arrivals at a join never produce duplicate activations or lost tokens (verified by concurrent execution tests with row-level locking)
**Plans**: 2 plans

Plans:
- [x] 39-01-PLAN.md — Backend: migration, enum extensions, engine logic, Celery timeout task, concurrency tests
- [x] 39-02-PLAN.md — Frontend: advanced join type controls in workflow designer
**UI hint**: yes

### Phase 40: Bulk Operations
**Goal**: Users can perform mass operations on documents with background job tracking and partial failure reporting
**Depends on**: Phase 39
**Requirements**: BULK-01, BULK-02, BULK-03, BULK-04
**Success Criteria** (what must be TRUE):
  1. User can select multiple documents in the browse UI and apply batch metadata update, lifecycle state change, or ACL modification
  2. User can select multiple documents and batch delete with a confirmation dialog
  3. Bulk operations execute as background jobs with a progress indicator showing completion percentage and partial failure details
  4. User can view bulk job history showing success/failure counts for past operations
**Plans**: 2 plans

Plans:
- [x] 40-01-PLAN.md — Backend: BulkJob model, migration, Celery task, service layer, API endpoints
- [x] 40-02-PLAN.md — Frontend: checkbox selection, bulk action toolbar, job progress dialog, job history page
**UI hint**: yes

### Phase 41: Import/Export
**Goal**: Admins can export and import document packages (with content, metadata, hierarchy, and relationships) for migration and backup
**Depends on**: Phase 40 (shares BatchJob infrastructure)
**Requirements**: IOEX-01, IOEX-02, IOEX-03, IOEX-04
**Success Criteria** (what must be TRUE):
  1. Admin can export selected documents as a ZIP package containing content files and metadata JSON
  2. Admin can export entire folder trees preserving hierarchy, ACLs, and document relationships in the package
  3. Admin can import a ZIP package that recreates documents with metadata and files them into the correct folders
  4. Import detects conflicts (duplicate names, missing references) and applies a configurable strategy (skip, overwrite, or rename)
**Plans**: 2 plans

Plans:
- [ ] 41-01-PLAN.md — TBD
- [ ] 41-02-PLAN.md — TBD
**UI hint**: yes

### Phase 42: System Monitoring & Health
**Goal**: Admins have real-time visibility into system health with proactive alerting
**Depends on**: Phase 41
**Requirements**: MON-01, MON-02, MON-03, MON-04
**Success Criteria** (what must be TRUE):
  1. Admin can view a system health dashboard showing status of database connections, Redis, Celery workers, and MinIO
  2. Admin can view queue depths, active task counts, and worker utilization metrics on the dashboard
  3. System exposes a Prometheus-compatible /metrics endpoint that external monitoring tools can scrape
  4. Admin receives alerts (in-app notification) when health checks fail or configurable thresholds are exceeded
**Plans**: 2 plans

Plans:
- [ ] 42-01-PLAN.md — TBD
- [ ] 42-02-PLAN.md — TBD
**UI hint**: yes

### Phase 43: CMIS Standard API
**Goal**: External CMIS clients can connect to the repository and perform document and folder operations using the OASIS CMIS 1.1 Browser Binding
**Depends on**: Phase 36 (requires auth backend abstraction for CMIS authentication)
**Requirements**: CMIS-01, CMIS-02, CMIS-03, CMIS-04, CMIS-05
**Success Criteria** (what must be TRUE):
  1. CMIS 1.1 Browser Binding endpoints handle document CRUD (create, read, update, delete, checkout, checkin)
  2. CMIS 1.1 Browser Binding endpoints handle folder and navigation operations (getChildren, getDescendants, getFolderTree, moveObject)
  3. CMIS-QL queries are accepted and mapped to the existing search infrastructure, returning correct results
  4. All CMIS endpoints enforce existing ACL permissions and support both local and SSO-backed authentication
  5. At least one standard CMIS client (CMIS Workbench or LibreOffice) can connect and perform basic CRUD operations
**Plans**: 2 plans

Plans:
- [ ] 43-01-PLAN.md — TBD
- [ ] 43-02-PLAN.md — TBD

### Phase 44: Process Analytics & Mining
**Goal**: Admins can discover actual execution patterns, identify bottlenecks, and analyze cycle times from workflow execution data
**Depends on**: Phase 42 (benefits from monitoring infrastructure and accumulated execution data)
**Requirements**: ANLYT-01, ANLYT-02, ANLYT-03, ANLYT-04
**Success Criteria** (what must be TRUE):
  1. Admin can view a process mining dashboard showing actual execution paths discovered from workflow audit/execution logs
  2. Admin can view cycle time breakdowns per activity and per template, identifying where time is spent
  3. Admin can identify bottleneck activities through frequency and duration analysis visualizations
  4. Analytics data refreshes from execution logs via background processing without impacting live workflow performance
**Plans**: 2 plans

Plans:
- [ ] 44-01-PLAN.md — TBD
- [ ] 44-02-PLAN.md — TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 34 -> 35 -> 36 -> 37 -> 38 -> 39 -> 40 -> 41 -> 42 -> 43 -> 44
Note: Phase 43 (CMIS) depends on Phase 36 (SSO) but is sequenced after Phase 42 for operational readiness.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-11 | v1.0 | 47/47 | Complete | 2026-03-30 |
| 12-15 | v1.1 | 4/4 | Complete | 2026-04-06 |
| 16-26 | v1.2 | 26/26 | Complete | 2026-04-13 |
| 27-33 | v1.3 | 19/19 | Complete | 2026-04-14 |
| 34. Frontend Gap Closure | v1.4 | 0/4 | Complete    | 2026-04-15 |
| 35. Tamper-Proof Audit | v1.4 | 2/2 | Complete    | 2026-04-15 |
| 36. Identity & SSO | v1.4 | 3/3 | Complete    | 2026-04-15 |
| 37. Error Handling & Compensation | v1.4 | 1/3 | Complete    | 2026-04-15 |
| 38. Workflow Versioning | v1.4 | 2/2 | Complete    | 2026-04-15 |
| 39. Advanced Join Semantics | v1.4 | 2/2 | Complete    | 2026-04-15 |
| 40. Bulk Operations | v1.4 | 2/2 | Complete   | 2026-04-15 |
| 41. Import/Export | v1.4 | 0/? | Not started | - |
| 42. System Monitoring | v1.4 | 0/? | Not started | - |
| 43. CMIS Standard API | v1.4 | 0/? | Not started | - |
| 44. Process Analytics | v1.4 | 0/? | Not started | - |
