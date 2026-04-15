# Feature Landscape: v1.4 Enterprise Completeness

**Domain:** Enterprise ECM/BPM - Enterprise completeness features
**Researched:** 2026-04-15

## Table Stakes

Features enterprise users expect from a mature ECM/BPM system. Missing = product feels incomplete when compared against Documentum, Alfresco, or Nuxeo.

### Authentication & Integration

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| LDAP directory sync | Every enterprise ECM integrates with corporate directories; manual user creation is unacceptable in orgs with 100+ users | Med | Existing User model (add `auth_source`, `external_id` fields) | Sync users/groups on schedule via Celery Beat. Map LDAP groups to existing Group model. Do NOT replace local auth -- keep both. |
| SAML 2.0 SSO | SAML is THE enterprise SSO protocol; 90%+ of Fortune 500 use it via Okta/Azure AD/ADFS. | Med-High | User model, new IdP config table | SP-initiated flow: user hits app -> redirect to IdP -> SAML assertion -> JWT issued. Use `python3-saml` (OneLogin) library. Must handle: IdP metadata XML import, assertion parsing, attribute mapping, session management. |
| OAuth2/OIDC SSO | Required for cloud-native IdPs (Azure AD, Google Workspace, Keycloak). Complements SAML for modern stacks. | Med | User model, new IdP config table | Authorization code flow with PKCE. Use `authlib` library. Share IdP config table with SAML. |
| JIT user provisioning | When SSO user logs in for first time, auto-create local user record from IdP attributes | Low | SSO implementation | Map IdP claims/attributes to User fields. Auto-assign groups based on IdP group claims. |

### Standards Compliance

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| CMIS 1.1 Browser Binding | OASIS standard for ECM interoperability. Any system claiming ECM status must speak CMIS. Migration tools, third-party integrations, and compliance auditors expect it. | High | Document, Folder, ACL, Versioning, Search -- all existing | Implement the Browser Binding (JSON over HTTP GET/POST) -- simplest of the three bindings and most used by modern clients. 10 CMIS services: Repository, Navigation, Object, Discovery, Versioning, Multi-filing, Relationship, Policy, ACL, plus optional Change Log. Map existing models: Document -> cmis:document, Folder -> cmis:folder, DocumentRelationship -> cmis:relationship. 6 base types defined by spec: cmis:document, cmis:folder, cmis:relationship, cmis:policy, cmis:item, cmis:secondary. |
| CMIS query language | Users/tools expect `SELECT * FROM cmis:document WHERE cmis:name LIKE '%report%'` | Med | CMIS object model mapping | Parse CMIS SQL-92 subset, translate to SQLAlchemy queries. Support CONTAINS() for full-text (maps to existing PostgreSQL FTS), IN_FOLDER()/IN_TREE() for hierarchy (maps to existing folder model). Support WHERE, ORDER BY, JOIN (inner only). |

### Workflow Resilience

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| Workflow error handling (boundary events) | Production workflows WILL fail. Without declarative error handling, every failure requires manual intervention. Camunda, Flowable, jBPM all have this as a core feature. | High | ActivityTemplate, ActivityInstance, ProcessEngine | Add `error_handlers` JSON to ActivityTemplate: maps error_type to handler_activity_id. On activity failure: check for matching handler -> route to handler activity with error context variables. If no handler: escalate to process-level handler or halt workflow. Two error types: technical (system failures, timeouts) and business (validation failures, rejected approvals). |
| Compensation handlers | Long-running business processes need undo capability. The Saga pattern is the standard approach in BPM when transactions span multiple activities. Camunda implements this via BPMN compensation events. | High | Error handling must be built first, ActivityTemplate | Add `compensation_activity_id` to ActivityTemplate. On compensation trigger: walk completed activities in reverse order, execute each compensation handler. Track compensation state (compensating/compensated/compensation_failed). Key insight from Camunda: compensation handlers execute in reverse chronological order, not reverse topological order. |
| Workflow template versioning | Templates evolve while instances run. Without versioning, you cannot fix a bug in a template without breaking in-flight workflows. Every major BPM engine (Camunda, Flowable, Activiti, jBPM) supports this. | Med | ProcessTemplate (already has `version` field + `is_installed` flag) | Existing `version` field provides the base. Add: `is_latest` flag, `version_lineage_id` (groups versions of same template). New instances always start on latest installed version. Running instances continue on their original version. Optional instance migration: move stuck instances to new version (admin endpoint, not automatic). Camunda's approach: "deploy changed process definitions without worrying about running process instances." |

### Bulk Operations

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| Bulk document operations (move, delete, update metadata, reclassify) | Users managing thousands of documents cannot operate one-at-a-time. Every ECM has bulk select + bulk action. | Med | Document, Folder, Celery | New `BatchJob` model: job_id, type, status (pending/running/completed/failed/partial), total_items, completed_items, failed_items, error_log (JSONB). Submit bulk request -> create Celery task -> process items -> update progress via SSE. Handle partial failures: continue processing remaining items, log per-item failures, report summary at end. |
| Bulk workflow operations (cancel, reassign, retry) | Admins need to mass-cancel stuck workflows or reassign work items when an employee leaves | Med | WorkflowInstance, WorkItem, BatchJob model from above | Same BatchJob infrastructure. Operations: bulk cancel workflows, bulk reassign work items, bulk retry failed activities. |

### Import/Export

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| Document export (ZIP with metadata) | Migration, backup, compliance archival all require getting documents OUT of the system with their metadata intact. | Med | Document, DocumentVersion, MinIO | Export as ZIP: `/manifest.json` (format version, export date, source system) + `/metadata/` (per-document JSON) + `/content/` (files). Include version history, custom properties, ACLs, lifecycle state, relationships. Support single doc, folder tree, or search results export. |
| Document import (ZIP with metadata) | Complementary to export. Migration from other systems, bulk loading. | Med | Document, Folder, MinIO, BatchJob | Parse manifest.json, validate format version, create documents, upload files to MinIO, apply metadata. Handle conflicts: skip/overwrite/rename strategy (user selects). Use BatchJob for progress tracking. |
| Workflow template export/import | Move templates between environments (dev -> staging -> prod). | Med | ProcessTemplate, ActivityTemplate, FlowTemplate | Export as JSON including all activities, flows, alias sets, auto-method configs. Import with conflict resolution (skip/overwrite/rename). Version bump on import if template name already exists. |

### System Monitoring

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| Deep health check endpoints | Operations teams need `/health` (liveness) and `/ready` (readiness) for load balancers and container orchestration. Existing `/health` endpoint likely needs enhancement. | Low | PostgreSQL, Redis, MinIO, Celery connections | `/health` = app process alive (always 200). `/ready` = all dependencies reachable. Check: PostgreSQL query, Redis ping, MinIO bucket access, Celery worker heartbeat via `celery.control.inspect()`. Return JSON with per-component status, latency, and version info. |
| System metrics dashboard | Admins need visibility into queue depths, worker status, storage usage, active sessions without SSHing into servers. | Med | Redis, Celery, MinIO, PostgreSQL stats, existing SSE | Expose metrics: active workflows count, pending work items, Celery queue depth, worker count/status, MinIO storage usage per bucket, database size, table row counts, active user sessions. Display in admin dashboard using existing Recharts infrastructure. SSE for real-time updates. |
| Tamper-proof audit trail | Cryptographic guarantee that audit logs have not been modified. Required for SEC 17a-4, FINRA, SOX, HIPAA compliance. Standard is "tamper-evident" not "tamper-proof" -- detect modification, not prevent it. | Med | Existing AuditLog model (has id, timestamp, entity_type, entity_id, action, user_id, before_state, after_state, details) | Hash chain: each audit entry includes SHA-256 hash of (entry_data + previous_entry_hash), creating a linked chain. Add columns to AuditLog: `entry_hash` (VARCHAR 64), `previous_hash` (VARCHAR 64), `sequence_number` (BIGINT, monotonic). Verification endpoint: walk chain from any point, confirm hash continuity. Periodic integrity check via Celery Beat. Do NOT use blockchain -- a simple hash chain is sufficient and vastly simpler. |


## Differentiators

Features that set the product apart from basic ECM systems. Not expected by every user, but valued by sophisticated deployments. Build these AFTER table stakes.

### Desktop Integration

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| WebDAV file access | Mount repository as network drive in Windows/macOS/Linux. Edit documents in native apps (Word, Excel) without manual download/upload cycle. | High | Document, Versioning, ACL, Locking (all exist) | Implement RFC 4918 (WebDAV) + RFC 3253 (DeltaV for versioning). Map: collections -> folders, resources -> documents. PROPFIND returns document metadata, GET/PUT handle content, LOCK/UNLOCK map to check-in/check-out. Use `wsgidav` Python library as ASGI-compatible middleware. Key risk: WebDAV clients (Windows Explorer, macOS Finder) are notoriously quirky -- non-standard requests, caching issues, large file handling. Extensive client-specific testing required. |
| Email archiving | Capture business emails as managed documents. Required for compliance in financial services, legal, healthcare. | High | Document types (need Email type), Folder, FTS | Two capture mechanisms: (1) SMTP relay via `aiosmtpd` -- app receives emails, parses MIME, stores as documents; (2) Mailbox polling via IMAP (`aioimaplib`) on Celery Beat schedule. Extract metadata: From, To, CC, Subject, Date, Message-ID, In-Reply-To (for threading), X-headers. Store attachments as separate linked documents (DocumentRelationship). Create "Email" document type with email-specific properties. Build email threading view using In-Reply-To/References headers to reconstruct conversation trees. |

### Workflow Intelligence

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| Advanced join semantics (N-of-M, cancelling, timeout) | Model complex approval patterns: "2 of 3 approvers sufficient", "first response wins and cancel others", "wait max 48h then proceed with available results". Goes beyond basic AND/OR joins that exist today. | Med-High | ActivityTemplate, ProcessEngine, existing AND/OR join logic | Three new join types: (1) `N_OF_M` -- configurable threshold, e.g., 2-of-3; (2) `CANCELLING_DISCRIMINATOR` -- first completion cancels sibling activity instances and revokes their work items (from Workflow Patterns WCP-29); (3) `TIMEOUT_JOIN` -- AND-join with deadline, proceeds after timeout with whatever results are available. Store join config as JSON on ActivityTemplate. ProcessEngine evaluates join conditions when execution tokens arrive at the join point. Cancelling join must handle: terminating running activity instances, revoking open work items, cleaning up execution tokens. |
| Process analytics and mining | Discover actual process behavior from execution logs. Identify bottlenecks, measure cycle times per activity, detect deviations from template definition. Builds on process mining discipline (van der Aalst). | High | WorkflowInstance, ActivityInstance, WorkItem history, existing BAM dashboards | Three capabilities: (1) Event log extraction -- transform activity instance records into XES-compatible format (case_id, activity_name, timestamp, resource/performer, lifecycle:transition); (2) Conformance checking -- compare actual execution paths against template, flag deviations (skipped activities, unexpected loops, out-of-order execution); (3) Bottleneck analysis -- per-activity metrics: avg wait time (queue to start), avg processing time (start to complete), throughput, rework rate. Visualization: process map overlay with color-coded bottleneck indicators. Build on existing BAM dashboard + Recharts. |

### Storage Optimization

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| Tiered storage management | Reduce storage costs by migrating old/infrequently-accessed documents to cheaper storage. A 5-year-old archived contract does not need SSD-speed access. | Med-High | Document, DocumentVersion, MinIO, Celery Beat | Define tiers as separate MinIO buckets (or buckets with different storage class tags). Three tiers: hot (default, fast access), warm (>N months old or lifecycle=Archived), cold (>N years old, rare access). Policy rules stored in DB: condition (age, lifecycle_state, access_frequency, document_type) -> target_tier. Celery Beat job evaluates policies nightly. Track current tier + last_accessed in document metadata. On cold document access: retrieve transparently but display "retrieving from archive" indicator if latency is noticeable. |


## Anti-Features

Features to explicitly NOT build. These are traps that add complexity without proportional value for this project.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full CMIS SOAP binding | SOAP/WSDL is legacy technology. Browser Binding covers all modern needs. SOAP adds massive XML complexity (WSDL generation, MTOM for binary transfer, WS-Security headers). | Implement Browser Binding (JSON over HTTP). Add AtomPub only if a concrete integration partner requires it. |
| Full CMIS AtomPub binding (upfront) | AtomPub is XML-heavy and primarily used by older CMIS clients. Modern tools prefer Browser Binding. | Defer. Only build if a specific integration need arises. |
| Full PKI/CA certificate authority | Building a CA is a separate product-level effort. Self-signed certs are sufficient for internal use. | Keep existing self-signed cert approach in DB. SSO via SAML/OIDC handles enterprise authentication. |
| Real-time collaborative editing (OT/CRDT) | Google Docs/SharePoint-level engineering. Enormous complexity. Check-in/check-out model prevents conflicts adequately. | WebDAV + check-out/check-in gives desktop editing. No simultaneous editing needed. |
| BPMN 2.0 XML import/export | Full BPMN 2.0 compliance is a massive specification (hundreds of pages). The existing Petri-net JSON model serves the project well. | Export/import workflow templates as JSON (custom format). CMIS handles document interop. |
| AI-powered email classification | ML model training, accuracy tuning, false positive handling adds massive scope for marginal improvement over rules. | Rule-based classification using sender/subject/folder patterns for email archiving. Manual reclassification for edge cases. |
| Multi-tenant isolation | Project is internal/personal use. Multi-tenancy adds complexity to every query, every permission check, every storage path. | Single-tenant. Explicitly out of scope per PROJECT.md. |
| Process Integrator legacy protocols (JMS, FTP, SOAP) | Legacy protocol support is a rabbit hole with no end. Modern integrations use REST/webhooks. | REST/webhook integration already built. Out of scope per PROJECT.md. |
| Federated CMIS (cross-repository queries) | Extremely rare requirement, enormous complexity (distributed query planning, credential federation). | Single-repository CMIS. The CMIS standard itself scopes services to a single repository. |
| Blockchain-based audit | Massively over-engineered for the use case. A hash chain provides identical tamper-evidence guarantees without distributed consensus overhead. | SHA-256 hash chain on AuditLog entries. Simple, fast, verifiable. |


## Feature Dependencies

```
LDAP sync ──────────────────────┐
SAML SSO ───────────────────────┼──> User model extensions (auth_source, external_id)
OAuth2/OIDC SSO ────────────────┘
JIT provisioning ──> SSO implementation (any of the three above)

CMIS Browser Binding ──> Document + Folder + ACL + Versioning + Search (all exist)
CMIS Query Language ──> CMIS object model mapping + existing PostgreSQL FTS

WebDAV ──> Document + Versioning + Locking + ACL (all exist)

Email archiving ──> Document types (need Email type) + Folder + FTS

Error handling ──> ActivityTemplate + ProcessEngine (both exist)
Compensation ──> Error handling (MUST build error handling first)
Workflow versioning ──> ProcessTemplate (existing version field + is_installed)
Advanced joins ──> ProcessEngine + existing AND/OR join logic

Bulk operations ──> New BatchJob model + Celery (both straightforward)
Import/Export ──> Document + Folder + ProcessTemplate + MinIO + BatchJob

System monitoring ──> All infrastructure connections (PostgreSQL, Redis, MinIO, Celery)
Tamper-proof audit ──> Existing AuditLog model (extend with hash columns)
Tiered storage ──> Document + MinIO + Celery Beat

Process analytics ──> ActivityInstance execution history + BAM dashboards (both exist)
```

## Feature Grouping by Dependency Clusters

**Cluster 1: Frontend Gap Closure** (no new backend needed, wire existing features to UI)
- Digital signatures UI, Retention/legal hold management UI, Document-level ACL UI, Queue administration UI, Lifecycle state filter fix, Notification preferences UI
- These should come FIRST -- pure frontend work that closes embarrassing gaps visible to every user.

**Cluster 2: Identity & Access** (auth infrastructure)
- LDAP sync, SAML SSO, OAuth2/OIDC SSO, JIT provisioning
- Self-contained cluster. Can be built in parallel with other backend clusters.

**Cluster 3: Workflow Resilience** (engine extensions)
- Error handling -> Compensation -> Workflow versioning -> Advanced joins
- Sequential dependency: error handling must come first (compensation depends on it). Versioning and advanced joins are independent of each other but both extend the engine.

**Cluster 4: Operations & Compliance** (admin tooling)
- Bulk operations -> Import/Export (share BatchJob infrastructure), System monitoring, Tamper-proof audit
- BatchJob model shared between bulk ops and import/export. Monitoring and audit are independent.

**Cluster 5: Standards & Integration** (interop protocols)
- CMIS Browser Binding + Query Language, WebDAV, Email archiving
- Each is independent. CMIS is highest priority in this cluster. WebDAV and email are deferrable.

**Cluster 6: Advanced Analytics & Storage** (optimization)
- Process analytics & mining, Tiered storage management
- Build last: they benefit from a mature system with accumulated execution history and stored documents.

## MVP Recommendation

### Must-Have for v1.4:
1. **Frontend gap closure** (6 items) -- Zero new backend code, massive perceived completeness
2. **LDAP/SAML/OAuth2 SSO** -- Enterprise auth is non-negotiable for real deployment
3. **Workflow error handling + compensation** -- Production workflows need failure resilience
4. **Workflow template versioning** -- Cannot safely evolve templates without this
5. **Bulk operations** -- Managing documents one-at-a-time does not scale past 100 docs
6. **Import/Export** -- Migration in/out is essential for any real deployment
7. **System monitoring (deep health + metrics)** -- Ops visibility is table stakes
8. **Tamper-proof audit** -- Low complexity, high compliance value, builds on existing model

### Should-Have (v1.4 stretch goals):
9. **CMIS Browser Binding + Query Language** -- Standard compliance, high interop value but high cost
10. **Advanced join semantics** -- Important for sophisticated approval workflows
11. **Process analytics** -- High insight value, builds on existing execution data

### Defer to v1.5+:
12. **WebDAV** -- High complexity, client compatibility is a minefield
13. **Email archiving** -- Requires SMTP/IMAP infrastructure, niche compliance need
14. **Tiered storage** -- Only valuable with large document volumes over extended time
15. **CMIS AtomPub binding** -- Only if concrete integration partner requires XML binding

## Complexity Budget Estimates

| Feature | Backend Days | Frontend Days | Total | Risk |
|---------|-------------|---------------|-------|------|
| Frontend gap closure (6 items) | 1-2 | 8-10 | ~10-12 | Low |
| LDAP sync | 3-4 | 2-3 | ~6 | Med (LDAP quirks) |
| SAML SSO | 4-5 | 2-3 | ~7 | Med (IdP config) |
| OAuth2/OIDC SSO | 3-4 | 1-2 | ~5 | Low |
| Workflow error handling | 5-7 | 3-4 | ~10 | High (engine core) |
| Compensation handlers | 4-5 | 2-3 | ~7 | High (reverse execution) |
| Workflow versioning | 3-4 | 2-3 | ~6 | Med |
| Advanced join semantics | 4-5 | 2-3 | ~7 | Med-High (edge cases) |
| Bulk operations | 4-5 | 4-5 | ~9 | Med (partial failure) |
| Import/Export | 4-5 | 3-4 | ~8 | Med (format design) |
| System monitoring | 3-4 | 4-5 | ~8 | Low |
| Tamper-proof audit | 2-3 | 1-2 | ~4 | Low |
| CMIS Browser Binding | 8-12 | 0-1 | ~10-12 | High (spec compliance) |
| CMIS Query Language | 4-6 | 0 | ~5 | Med (SQL parsing) |
| Process analytics | 5-7 | 5-7 | ~12 | Med-High |
| WebDAV | 6-8 | 1-2 | ~8 | High (client compat) |
| Email archiving | 6-8 | 4-5 | ~11 | High (MIME parsing) |
| Tiered storage | 4-5 | 2-3 | ~7 | Med |

**Total estimated: ~140-160 developer-days for all features**
**Must-Have subset: ~75-85 developer-days**
**Should-Have adds: ~25-30 developer-days**

## Sources

- [CMIS 1.1 OASIS Specification](https://docs.oasis-open.org/cmis/CMIS/v1.1/cs01/CMIS-v1.1-cs01.html) -- HIGH confidence
- [Camunda Error Handling Best Practices](https://docs.camunda.io/docs/components/best-practices/development/dealing-with-problems-and-exceptions/) -- HIGH confidence
- [Workflow Patterns Initiative - Control Flow](http://www.workflowpatterns.com/patterns/control/) -- HIGH confidence
- [Cancelling Partial Join (WCP-32)](http://www.workflowpatterns.com/patterns/control/new/wcp32.php) -- HIGH confidence
- [Cancelling Discriminator (WCP-29)](http://www.workflowpatterns.com/patterns/control/new/wcp29.php) -- HIGH confidence
- [Camunda Versioning Process Definitions](https://docs.camunda.io/docs/components/best-practices/operations/versioning-process-definitions/) -- HIGH confidence
- [Flowable Model Versioning](https://documentation.flowable.com/latest/model/versioning-deployment) -- HIGH confidence
- [Alfresco CMIS API Reference](https://docs.alfresco.com/content-services/6.0/develop/reference/cmis-ref/) -- HIGH confidence
- [Cossack Labs - Tamper-Proof Audit Logs](https://www.cossacklabs.com/blog/audit-logs-security/) -- MEDIUM confidence
- [IBM Process Mining Overview](https://www.ibm.com/think/topics/process-mining) -- MEDIUM confidence
- [Mattermost - 18 Tips for Tamper-Proof Audit Logs](https://mattermost.com/blog/compliance-by-design-18-tips-to-implement-tamper-proof-audit-logs/) -- MEDIUM confidence
- [Enterprise SSO Playbook (US Gov)](https://www.idmanagement.gov/playbooks/sso/) -- MEDIUM confidence
- [Newgen Email Archiving](https://newgensoft.com/blog/email-archiving-for-compliance-governance-and-enterprise-recovery/) -- MEDIUM confidence
- [WebDAV Wikipedia](https://en.wikipedia.org/wiki/WebDAV) -- MEDIUM confidence
- [Hierarchical Storage Management Wikipedia](https://en.wikipedia.org/wiki/Hierarchical_storage_management) -- MEDIUM confidence
