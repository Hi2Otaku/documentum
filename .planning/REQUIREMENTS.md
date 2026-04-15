# Requirements: Documentum Workflow Clone

**Defined:** 2026-04-15
**Core Value:** Any workflow or document management use case described in the Documentum specification can be modeled and executed end-to-end.

## v1.4 Requirements

Requirements for Enterprise Completeness milestone. Each maps to roadmap phases.

### Frontend Gap Closure

- [ ] **FEGAP-01**: User can sign documents with digital certificate and verify signatures from the web UI
- [ ] **FEGAP-02**: User can view signature details (signer, timestamp, certificate, validity status) on signed documents
- [ ] **FEGAP-03**: Admin can create, edit, and delete retention policies and assign them to documents from the UI
- [ ] **FEGAP-04**: Admin can place and release legal holds on documents from the UI
- [ ] **FEGAP-05**: User can manage document-level ACL entries (add/remove users and groups with permission levels)
- [ ] **FEGAP-06**: Admin can create, edit, and delete work queues and manage queue membership from the UI
- [ ] **FEGAP-07**: User can filter documents by lifecycle state (Draft/Review/Approved/Archived) in the documents list
- [ ] **FEGAP-08**: User can configure notification preferences (which event types trigger notifications)

### Identity & Access

- [x] **AUTH-01**: Admin can configure LDAP directory connection and map LDAP groups to system groups
- [x] **AUTH-02**: User can authenticate via SAML 2.0 SSO (redirect to IdP, consume assertion, create session)
- [x] **AUTH-03**: User can authenticate via OAuth2/OIDC (authorization code flow with PKCE)
- [x] **AUTH-04**: System provisions user accounts on first SSO login (JIT provisioning)
- [x] **AUTH-05**: Existing local authentication continues to work alongside SSO providers
- [x] **AUTH-06**: Background services (Celery workers, Workflow Agent) authenticate via service tokens without browser flow

### Workflow Error Handling

- [x] **WFERR-01**: Template designer can attach error handlers to activities that execute when the activity fails
- [x] **WFERR-02**: Template designer can define compensation activities that undo completed work when a flow fails
- [x] **WFERR-03**: Engine executes compensation handlers in reverse chronological order on workflow failure
- [ ] **WFERR-04**: Failed activities show error details and allow manual retry or skip from the workflow operations UI

### Workflow Versioning

- [x] **WFVER-01**: Admin can install a new template version while previous version's instances continue running
- [x] **WFVER-02**: New workflow instances use the latest installed version; running instances remain on their original version
- [x] **WFVER-03**: Admin can view which template version each running instance uses

### Advanced Join Semantics

- [x] **JOIN-01**: Template designer can configure N-of-M joins (activate when N of M incoming flows complete)
- [x] **JOIN-02**: Template designer can configure cancelling joins (remaining branches cancelled when join fires)
- [x] **JOIN-03**: Template designer can configure timeout joins (join fires after duration even if not all branches complete)
- [x] **JOIN-04**: Engine handles concurrent token arrivals at joins without race conditions (row-level locking)

### Bulk Operations

- [x] **BULK-01**: User can select multiple documents and apply batch update (metadata, lifecycle state, ACL)
- [x] **BULK-02**: User can select multiple documents and batch delete with confirmation
- [x] **BULK-03**: Bulk operations run as background jobs with progress tracking and partial failure reporting
- [x] **BULK-04**: User can view bulk job history with success/failure counts

### Import/Export

- [ ] **IOEX-01**: Admin can export selected documents as a ZIP package including content files and metadata JSON
- [ ] **IOEX-02**: Admin can export folder trees preserving hierarchy, ACLs, and document relationships
- [ ] **IOEX-03**: Admin can import a ZIP package, recreating documents with metadata and filing into folders
- [ ] **IOEX-04**: Import handles conflicts (duplicate names, missing references) with configurable strategy (skip/overwrite/rename)

### System Monitoring

- [ ] **MON-01**: Admin can view system health dashboard (database connections, Redis status, Celery worker status, MinIO health)
- [ ] **MON-02**: Admin can view queue depths, active task counts, and worker utilization
- [ ] **MON-03**: System exposes Prometheus-compatible metrics endpoint for external monitoring integration
- [ ] **MON-04**: Admin receives alerts when health checks fail or thresholds are exceeded

### Tamper-Proof Audit

- [x] **AUDIT-01**: Each audit record includes a SHA-256 hash of its content chained to the previous record's hash
- [x] **AUDIT-02**: Admin can verify audit trail integrity (detect gaps or tampering) from the UI
- [x] **AUDIT-03**: Audit hash computation runs asynchronously without impacting write throughput

### CMIS Standard API

- [ ] **CMIS-01**: System exposes CMIS 1.1 Browser Binding endpoints for document CRUD operations
- [ ] **CMIS-02**: System exposes CMIS 1.1 Browser Binding endpoints for folder/navigation operations
- [ ] **CMIS-03**: System supports CMIS-QL queries mapped to existing search infrastructure
- [ ] **CMIS-04**: CMIS endpoints respect existing ACL enforcement and authentication
- [ ] **CMIS-05**: CMIS clients (CMIS Workbench, LibreOffice) can connect and perform basic operations

### Process Analytics

- [ ] **ANLYT-01**: Admin can view process mining dashboard showing actual execution paths discovered from workflow logs
- [ ] **ANLYT-02**: Admin can view cycle time analysis per activity and per template
- [ ] **ANLYT-03**: Admin can identify bottleneck activities via frequency and duration analysis
- [ ] **ANLYT-04**: Analytics data refreshes from workflow execution logs without impacting live performance

## Future Requirements (v1.5+)

- WebDAV file access — deferred due to client compatibility complexity across OS versions
- Email archiving — deferred, requires SMTP/IMAP infrastructure decision
- Tiered storage management — deferred, only valuable at scale (100K+ docs)
- CMIS AtomPub/SOAP bindings — Browser Binding is sufficient for v1.4

## Out of Scope

- Multi-tenancy — internal/personal use, adds complexity everywhere
- Multi-level security (MLS) — government/defense requirement, not relevant
- Information Rights Management (IRM/DRM) — post-download control not needed for internal use
- Repository replication / HA — single-instance deployment sufficient
- xCP platform bundling — too broad, focus on engine
- Mobile native app — web-responsive UI is sufficient

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| FEGAP-01 | Phase 34 | Pending |
| FEGAP-02 | Phase 34 | Pending |
| FEGAP-03 | Phase 34 | Pending |
| FEGAP-04 | Phase 34 | Pending |
| FEGAP-05 | Phase 34 | Pending |
| FEGAP-06 | Phase 34 | Pending |
| FEGAP-07 | Phase 34 | Pending |
| FEGAP-08 | Phase 34 | Pending |
| AUDIT-01 | Phase 35 | Complete |
| AUDIT-02 | Phase 35 | Complete |
| AUDIT-03 | Phase 35 | Complete |
| AUTH-01 | Phase 36 | Complete |
| AUTH-02 | Phase 36 | Complete |
| AUTH-03 | Phase 36 | Complete |
| AUTH-04 | Phase 36 | Complete |
| AUTH-05 | Phase 36 | Complete |
| AUTH-06 | Phase 36 | Complete |
| WFERR-01 | Phase 37 | Complete |
| WFERR-02 | Phase 37 | Complete |
| WFERR-03 | Phase 37 | Complete |
| WFERR-04 | Phase 37 | Pending |
| WFVER-01 | Phase 38 | Complete |
| WFVER-02 | Phase 38 | Complete |
| WFVER-03 | Phase 38 | Complete |
| JOIN-01 | Phase 39 | Complete |
| JOIN-02 | Phase 39 | Complete |
| JOIN-03 | Phase 39 | Complete |
| JOIN-04 | Phase 39 | Complete |
| BULK-01 | Phase 40 | Complete |
| BULK-02 | Phase 40 | Complete |
| BULK-03 | Phase 40 | Complete |
| BULK-04 | Phase 40 | Complete |
| IOEX-01 | Phase 41 | Pending |
| IOEX-02 | Phase 41 | Pending |
| IOEX-03 | Phase 41 | Pending |
| IOEX-04 | Phase 41 | Pending |
| MON-01 | Phase 42 | Pending |
| MON-02 | Phase 42 | Pending |
| MON-03 | Phase 42 | Pending |
| MON-04 | Phase 42 | Pending |
| CMIS-01 | Phase 43 | Pending |
| CMIS-02 | Phase 43 | Pending |
| CMIS-03 | Phase 43 | Pending |
| CMIS-04 | Phase 43 | Pending |
| CMIS-05 | Phase 43 | Pending |
| ANLYT-01 | Phase 44 | Pending |
| ANLYT-02 | Phase 44 | Pending |
| ANLYT-03 | Phase 44 | Pending |
| ANLYT-04 | Phase 44 | Pending |
