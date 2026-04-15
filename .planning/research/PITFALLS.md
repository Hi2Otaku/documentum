# Domain Pitfalls: v1.4 Enterprise Completeness

**Domain:** Adding enterprise features (SSO, CMIS, WebDAV, email archiving, workflow resilience, bulk ops, monitoring, tiered storage, tamper-proof audit, process analytics) to an existing FastAPI/SQLAlchemy ECM system
**Researched:** 2026-04-15

---

## Critical Pitfalls

Mistakes that cause rewrites, security vulnerabilities, or data corruption in an already-running system with 17K+ Python LOC and 33 completed phases.

---

### Pitfall 1: SSO Retrofit Breaks Existing JWT Flow for Service-to-Service Auth

**What goes wrong:** The existing auth pipeline (`get_current_user` in `dependencies.py`) assumes every token is a locally-issued HS256 JWT with `sub` = user UUID. Introducing SAML/OAuth2 SSO means tokens may come from external IdPs with different claim structures, different signing algorithms (RS256), and different subject identifiers (email or `nameID` instead of UUID). Developers add SSO but forget that Celery workers, the Workflow Agent, and internal service calls also use the JWT path -- these break because they cannot redirect to an IdP login page.

**Why it happens:** The `get_current_user` dependency is called in 28+ routers. SSO adds a second token source but the dependency only knows about one. Internal/service auth (Celery tasks calling API endpoints, Workflow Agent background execution) has no browser to do SAML redirects.

**Consequences:** All background task execution fails. Celery workers that call authenticated endpoints get 401s. Users authenticated via SSO get 401s if the IdP's claim format differs from the expected `{"sub": "uuid", "username": "..."}` structure.

**Prevention:**
- Create a `TokenPayload` abstraction that normalizes claims from both local JWT and SSO tokens into a common format (user_id UUID, username, groups, auth_source)
- The `get_current_user` dependency must detect token type (local vs SSO) by examining the `iss` (issuer) claim and dispatch to the correct decoder
- Add a separate `ServiceToken` / API key mechanism for Celery-to-API and Workflow Agent calls that bypasses browser-redirect flows entirely
- SSO-authenticated users MUST be provisioned in the local `users` table on first login (Just-In-Time provisioning) so that `user.id` FK relationships remain consistent
- Keep the existing username/password login as a fallback -- SSO is additive, not a replacement

**Detection:** Integration test that runs a full workflow (start -> auto activity -> manual task -> complete) with an SSO-provisioned user. If the Celery worker step fails, the abstraction is broken.

---

### Pitfall 2: Workflow Versioning Corrupts In-Flight Instances

**What goes wrong:** A process template is updated (new activity added, flow condition changed) while instances of the old version are still RUNNING. The engine loads the new template definition and applies it to the old instance, which has activity instances that reference template IDs that no longer exist or have changed semantics. Token routing breaks. Instances get stuck or advance to wrong activities.

**Why it happens:** The current `ProcessTemplate` model has a `version` integer field but `WorkflowInstance.process_template_id` points to a single template row. There is no snapshot mechanism -- if the template row is modified in place, all running instances see the change. The engine's `_advance_workflow` in `engine_service.py` loads `template.activity_templates` and `template.flow_templates` live from the current template state.

**Consequences:** Running workflows silently corrupt. Tokens arrive at activities that don't exist. AND-joins deadlock because the incoming flow count changed. Completed instances have audit trails that reference a template definition different from what they actually executed.

**Prevention:**
- NEVER modify an installed template in place. Create a new template row with an incremented version number. The old row stays immutable
- `WorkflowInstance.process_template_id` must always point to the exact template version it was started with -- this FK is the instance's frozen contract
- Add a `template_version` column to `WorkflowInstance` for quick version identification
- Template installation creates an immutable snapshot (set `is_installed = True` and disallow further edits on that row)
- Migration of in-flight instances to a new version is an EXPLICIT admin operation, not automatic. It must map old activity instance states to new template activities with a user-reviewed mapping table
- The existing `state: ProcessState.ACTIVE` / `DEPRECATED` enum already supports this pattern -- DEPRECATED templates cannot start new instances but existing instances continue on the old version

**Detection:** Regression test: start instance on template v1, update template to v2 with a new activity between existing ones, verify v1 instance completes on original path without seeing v2 changes.

---

### Pitfall 3: Advanced Join Semantics Introduce Deadlock and Token Leaks

**What goes wrong:** The current `_should_activate` function (engine_service.py line 777) counts tokens simply: AND-join needs tokens from ALL incoming flows, OR-join needs 1. Adding weighted joins, cancelling joins, or timeout-based sync introduces subtle bugs: (a) OR-join fires but leftover tokens from the other branches are never consumed, accumulating indefinitely; (b) cancelling join tries to cancel already-completed activities; (c) concurrent token arrivals at an AND-join cause double-activation due to race conditions in the check-then-act pattern.

**Why it happens:** The current implementation uses a simple count query (`SELECT COUNT(*)`) without row-level locking. Two concurrent Celery workers can both read `token_count = 2`, both determine `>= len(incoming_flows)`, and both fire the join activity. The `ExecutionToken.is_consumed` flag is checked without `FOR UPDATE`.

**Consequences:** Activity fires twice (duplicate work items created). Token leak causes memory/state bloat -- orphaned tokens accumulate in the database. Cancelling join tries to cancel a completed sub-workflow, triggering cascading errors.

**Prevention:**
- Add `SELECT ... FOR UPDATE` (pessimistic locking) on the token count query in `_should_activate`. SQLAlchemy: `select(...).with_for_update()`
- Consume ALL incoming tokens when a join fires, not just the triggering one. After activation, sweep and mark `is_consumed = True` for all tokens at that activity
- For cancelling joins: only cancel activities in DORMANT or ACTIVE state. Skip COMPLETE/ERROR states gracefully
- For OR-join with cleanup: after the winning branch fires the join, spawn a background task to cancel (not error) the losing branches' remaining activities
- Add a `token_consumed_at` timestamp column for debugging token lifecycle
- Implement a periodic Celery Beat task that detects orphaned tokens (unconsumed tokens for FINISHED/FAILED workflows) and cleans them up

**Detection:** Concurrent test: two Celery workers completing two branches of a parallel split simultaneously, targeting the same AND-join. Verify exactly one activation occurs. Run 100 times to catch race conditions.

---

### Pitfall 4: CMIS Implementation Scope Creep and Dual-API Inconsistency

**What goes wrong:** CMIS 1.1 defines ~60 operations across AtomPub and Browser (JSON) bindings. Developers start implementing the full spec and either (a) never finish because it is enormous, or (b) implement operations that duplicate existing REST API logic with subtle behavioral differences (e.g., CMIS `deleteTree` has different error semantics than the existing `DELETE /folders/{id}` endpoint). Users discover that creating a document via CMIS produces different metadata defaults than creating via the REST API.

**Why it happens:** CMIS mandates specific response formats (Atom XML or a specific JSON structure), specific query language (CMIS-QL), and specific property naming (`cmis:objectId`, `cmis:name`). These don't map 1:1 to the existing Pydantic schemas. Developers create parallel code paths instead of a translation layer.

**Consequences:** Two codepaths for document CRUD that drift apart. Bug fixes applied to REST API but not CMIS endpoint (or vice versa). CMIS compliance tests fail on edge cases. The CMIS implementation becomes unmaintainable.

**Prevention:**
- Implement CMIS as a TRANSLATION LAYER over existing services, not as new service logic. CMIS router calls `document_service.create_document()` the same way the REST router does
- Create a `cmis_mapper.py` module that translates between CMIS property names (`cmis:objectId` -> `id`, `cmis:name` -> `title`) and the internal model
- Start with Browser Binding (JSON) only -- it is simpler than AtomPub and what modern CMIS clients expect
- Implement only the operations that map to existing features: `getRepositoryInfo`, `getObject`, `createDocument`, `createFolder`, `getChildren`, `query` (mapped to existing DQL/search), `checkOut`, `checkIn`, `getContentStream`, `setContentStream`, `deleteObject`
- Explicitly mark unsupported CMIS capabilities in the repository info response (`capabilityACL: "none"` if not implementing CMIS ACL operations)
- Use the CMIS TCK (Technology Compatibility Kit) for validation, but accept partial compliance

**Detection:** Single integration test that creates a document via CMIS, reads it via REST API, and vice versa. If metadata differs, the translation layer is broken.

---

### Pitfall 5: Tamper-Proof Audit Trail Performance Destroys Write Throughput

**What goes wrong:** Every mutation in the system calls `create_audit_record()` in the same database transaction. Adding cryptographic hash chaining means each audit write must: (1) read the previous record's hash, (2) compute hash over current record + previous hash, (3) write the new record. This serializes ALL audit writes system-wide because each write depends on the previous one's hash. Under load, the audit table becomes a global bottleneck.

**Why it happens:** Hash chaining is inherently sequential -- record N's hash depends on record N-1. The current `AuditLog` model writes are already in the request transaction path. Adding hash computation and sequential dependency turns every API request into a serial queue.

**Consequences:** API response latency increases 2-10x under concurrent load. Deadlocks on the audit table as concurrent transactions compete for the "latest hash" row. Worst case: the entire system throughput drops to single-threaded audit write speed.

**Prevention:**
- Decouple hash chaining from the request path. Write audit records in the request transaction WITHOUT the hash (same as today). Compute hash chains asynchronously via a dedicated Celery worker that processes the audit queue in strict order
- Use a sequence number (`audit_sequence_id` BIGSERIAL) to guarantee ordering. The hash worker processes records by sequence number
- Store the chain hash in a separate column (`chain_hash`) that starts NULL and gets filled by the background worker
- Verification is an admin operation that reads the chain sequentially -- it does not need to happen on every write
- Consider Merkle tree structure instead of linear chain for faster verification of arbitrary subsequences (verify record N without scanning all N-1 predecessors)
- Partition the audit table by month (PostgreSQL declarative partitioning). Old partitions become read-only and can have their chain verified and sealed
- The existing `AuditLog` model has no `chain_hash` or `sequence` column -- these must be added via Alembic migration. Make `chain_hash` nullable so existing records are not affected

**Detection:** Load test: 100 concurrent document uploads (each triggers audit write). Measure p99 latency with and without hash chaining. If p99 > 500ms, the implementation is too synchronous.

---

## Moderate Pitfalls

---

### Pitfall 6: WebDAV Lock Semantics Conflict with Existing Check-In/Check-Out

**What goes wrong:** The existing document model has `locked_by` and `locked_at` fields for check-out locks. WebDAV RFC 4918 defines its own locking protocol with lock tokens, lock scopes (exclusive/shared), lock types, timeout values, and lock discovery. Implementing WebDAV locks as a separate system creates two incompatible locking mechanisms -- a document checked out via the web UI is not locked for WebDAV clients, and vice versa.

**Why it happens:** WebDAV locks and ECM check-out are conceptually similar but have different semantics. WebDAV locks have timeouts and tokens; ECM check-out is indefinite until explicit check-in. WebDAV supports shared locks; the existing system does not.

**Prevention:**
- Unify locking: WebDAV LOCK operation maps to the existing `locked_by`/`locked_at` fields. WebDAV UNLOCK maps to check-in
- Store the WebDAV lock token in a new `lock_token` column on `documents` (or a related `document_locks` table that also stores timeout and scope)
- WebDAV exclusive lock = existing check-out. Do not implement shared locks initially (return 409 Conflict for shared lock requests)
- WebDAV lock timeout: add a Celery Beat task that expires stale WebDAV locks after timeout. The existing check-out has no timeout, so WebDAV locks get an additional `lock_expires_at` column
- Mount WsgiDAV (a mature Python WebDAV server) via `WSGIMiddleware` (a2wsgi) at `/webdav/`. WsgiDAV provides a provider interface -- implement a custom `DAVProvider` that delegates to `document_service`

**Detection:** Test: lock document via WebDAV, verify it shows as checked-out in the web UI. Check out via web UI, verify WebDAV LOCK returns 423 Locked.

---

### Pitfall 7: Email Archiving MIME Parsing Fails on Real-World Email

**What goes wrong:** Python's `email.parser` handles well-formed MIME correctly but real-world email is full of violations: missing charset declarations, mixed encodings within a single message, broken base64 (Python's parser stops at first `==` padding), nested `message/rfc822` attachments, winmail.dat (TNEF) attachments, S/MIME encrypted bodies, and email threads with inconsistent `In-Reply-To` / `References` headers.

**Why it happens:** Email standards (RFC 5322, RFC 2045-2049) are complex and widely violated. Corporate email systems (Exchange, Notes) produce non-standard MIME. Python's built-in `email` module has known edge cases with base64 decoding (CPython issue #137687).

**Consequences:** Silently truncated message bodies. Missing attachments. Garbled non-ASCII subject lines. Threading algorithm fails, creating orphaned or mis-threaded messages. Ingestion pipeline crashes on malformed MIME, blocking entire archiving queue.

**Prevention:**
- Use `mail-parser` or `flanker` library instead of raw `email.parser` -- they handle real-world MIME quirks better
- Always decode with explicit error handling: `errors='replace'` for text, fallback charset chain (declared charset -> UTF-8 -> latin-1 -> raw bytes)
- Thread reconstruction: implement JWZ threading algorithm (use `In-Reply-To`, `References`, AND `Subject` matching as fallback). Do not rely solely on `Message-ID` chains
- Store the raw `.eml` file in MinIO verbatim before any parsing. If parsing fails, the original is preserved for manual recovery or later re-processing
- TNEF (winmail.dat): use `tnefparse` library to extract embedded attachments
- Implement a dead-letter queue: emails that fail parsing 3 times go to a review queue, not silently dropped
- Size limits: reject emails > 50MB (or configurable). Large attachments should be stored as separate document versions, not inline BLOBs

**Detection:** Curate a test corpus of 20+ real-world problem emails: mixed-encoding, broken base64, nested rfc822, TNEF, S/MIME envelope, empty body with attachment-only, non-ASCII filenames in Content-Disposition. Run parser against all. Any failure = parser is not production-ready.

---

### Pitfall 8: Bulk Operations Exhaust Memory and Create Unpredictable Lock Contention

**What goes wrong:** A bulk delete of 10,000 documents loads all 10K objects into SQLAlchemy's session, triggers 10K audit records, 10K MinIO delete calls, and holds a database transaction open for the entire duration. The session consumes gigabytes of memory. The long-running transaction blocks other users. If it fails at document 8,000, everything rolls back and the user has to retry all 10K.

**Why it happens:** The natural pattern (`for doc in documents: await delete_document(db, doc)`) within a single transaction. SQLAlchemy's identity map holds all loaded objects in memory. Each audit record adds to the transaction size. MinIO calls are synchronous-in-thread, adding latency.

**Consequences:** Worker OOM kill. Other users see lock wait timeouts. Partial failures waste all progress.

**Prevention:**
- Chunk-based processing: process in batches of 100-500 items per database transaction. Commit each chunk independently
- Track progress in a `bulk_job` table: `{id, total_items, processed_items, failed_items, status, error_log}`
- Each chunk commits its own transaction. Failed items are logged but don't block the batch. The job continues with remaining chunks
- Use `session.expire_all()` or a fresh session per chunk to prevent identity map memory growth
- MinIO deletes use `remove_objects()` (batch API) not individual `remove_object()` calls
- For bulk updates: use `UPDATE ... WHERE id IN (...)` raw SQL for performance instead of loading objects. SQLAlchemy `update().where().values()` construct
- Return a job ID immediately. Client polls `/jobs/{id}` for progress. Do NOT make bulk operations synchronous HTTP requests
- Implement a Celery task for the actual work. The API endpoint just creates the job record and enqueues the task

**Detection:** Test: bulk delete of 5,000 documents. Measure memory usage of Celery worker. Should stay under 500MB. Verify other API requests remain responsive during the operation.

---

### Pitfall 9: Import/Export Breaks on Circular References and Cross-Entity Dependencies

**What goes wrong:** Exporting a workflow template that references documents, which reference document types, which reference lifecycle policies, which reference workflows creates circular dependency chains. Naive JSON serialization hits infinite recursion or produces an export that cannot be re-imported because entity IDs don't match in the target system.

**Why it happens:** The data model has rich cross-references: `WorkflowPackage -> Document`, `ActivityTemplate.lifecycle_action`, `AliasSet -> User/Group`, `ProcessTemplate.sub_template_id -> ProcessTemplate`. UUID primary keys in the source system don't exist in the target.

**Consequences:** Import fails with FK constraint violations. Circular references cause infinite loops or stack overflow during export. Imported templates reference non-existent users/groups.

**Prevention:**
- Use a two-pass import: first pass creates all entities with new UUIDs, building an `{old_uuid: new_uuid}` mapping table. Second pass resolves all FK references using the mapping
- Export format: use a deterministic ordering (entities sorted topologically by dependency). Include a manifest listing all entities and their types
- Break circular references by allowing nullable FKs during import (e.g., import template without `sub_template_id`, then update it in second pass)
- For user/group references: export includes the username/group name, not UUID. Import resolves by name, prompting for mapping when names don't match
- Large file handling: stream documents to/from MinIO during import/export. Don't load file content into the export JSON -- include a reference and package files separately (ZIP archive with JSON manifest + file blobs)
- Maximum export size limit (e.g., 2GB compressed) with clear error when exceeded

**Detection:** Round-trip test: export a complete workflow template with attached documents, types, and alias sets. Import into a clean database. Start an instance of the imported template and run it to completion.

---

### Pitfall 10: Tiered Storage Migration Creates Inconsistent Reads

**What goes wrong:** A document is being migrated from hot (MinIO local) to cold (MinIO archive/S3 Glacier) storage while a user requests it. The migration deletes the object from hot storage, but the copy to cold storage hasn't completed. The `download_object()` call in `minio_client.py` returns a 404 from the hot bucket, and there's no fallback to check the cold bucket.

**Why it happens:** The current `minio_client.py` hardcodes `DOCUMENTS_BUCKET = "documents"` with no awareness of storage tiers. Migration is a delete-then-copy (or copy-then-delete) that is not atomic.

**Consequences:** Users see "Document not found" errors for documents that exist but are in transit. If migration crashes between delete and copy, the document is lost.

**Prevention:**
- Add a `storage_tier` column to `DocumentVersion` (or a separate `storage_location` table): `hot`, `warm`, `cold`
- NEVER delete from source tier until the copy to destination tier is verified (compare ETags/checksums)
- The `download_object()` function must become tier-aware: check `storage_tier` metadata, route to correct bucket
- For cold storage (e.g., Glacier): add a `restore_status` field. If `storage_tier = 'cold'`, the download endpoint returns 202 Accepted with a restore-in-progress message, not 404
- Use a state machine for migration: `SCHEDULED -> COPYING -> VERIFYING -> CUTOVER -> COMPLETE`. Only at CUTOVER does the `storage_tier` column change. Only after COMPLETE does the source copy get deleted
- Wrap the entire cutover in a PostgreSQL advisory lock per document to prevent concurrent reads during the tier switch

**Detection:** Race condition test: start a migration, simultaneously request the document 100 times. Zero requests should return 404 or error.

---

### Pitfall 11: Workflow Error Handling Compensation Corrupts Completed Activities

**What goes wrong:** A workflow with activities A -> B -> C fails at C. The compensation handler tries to "undo" B, but B completed a document lifecycle transition (Draft -> Approved) and sent a notification. The compensation reverses the lifecycle state but cannot unsend the notification. The document is now in Draft state but the audit trail shows it was Approved, and downstream systems that received the notification believe it is Approved.

**Why it happens:** Compensation is not true undo -- it is a "best effort reverse" that cannot roll back side effects (notifications, external webhook calls, email sends). The current engine has no concept of compensating activities.

**Consequences:** Inconsistent state between the workflow system and external systems. Audit trail becomes confusing (Approved -> Draft with no clear explanation). Users who acted on the notification are misled.

**Prevention:**
- Compensation activities are FORWARD actions, not rollbacks. Instead of "undo approval", the compensation creates a NEW "approval revoked" lifecycle transition. The audit trail shows the full history: Draft -> Approved -> Revoked
- External side effects (notifications, webhooks) CANNOT be compensated. Instead, send a COMPENSATING notification: "Document X approval has been revoked"
- Each activity template gets an optional `compensation_template_id` pointing to another activity template that runs as the compensation
- Compensation only applies to activities in the CURRENT workflow instance. Do not cascade compensation to parent or sibling workflows
- Add a `is_compensation` flag to `ActivityInstance` so the engine treats compensation activities differently (they don't fire normal triggers)
- Guard: only activities in COMPLETE state can be compensated. DORMANT/ACTIVE activities are simply cancelled (state -> ERROR)

**Detection:** Test: workflow A -> B -> C where B triggers lifecycle change and notification. Force C to fail. Verify compensation creates a new lifecycle event (not a state revert) and sends a compensating notification.

---

## Minor Pitfalls

---

### Pitfall 12: System Monitoring Metrics Cardinality Explosion

**What goes wrong:** Monitoring labels include `workflow_template_id`, `activity_name`, `user_id`, or `document_type`. With hundreds of templates and thousands of users, Prometheus metric cardinality explodes. A metric like `work_item_duration{template_id="...", activity_name="...", user_id="..."}` creates millions of time series. Prometheus OOMs.

**Prevention:**
- Use bounded labels only: `workflow_state` (5 values), `activity_type` (6 values), `work_item_state` (6 values)
- Template and user dimensions go into PostgreSQL-based analytics tables, NOT Prometheus labels
- For workflow throughput: `workflow_completed_total{template_name="..."}` is acceptable (bounded by template count, typically < 100). `workflow_completed_total{instance_id="..."}` is catastrophic (unbounded)
- Pre-aggregate in application code: push summary metrics (p50, p95 latency) not per-request histograms
- Set Prometheus `sample_limit` per scrape target as a safety valve

---

### Pitfall 13: Process Analytics Queries Kill Database Performance

**What goes wrong:** Process mining queries (e.g., "find the most common path through this workflow over the last 6 months") scan the entire `activity_instances` and `execution_tokens` tables with complex self-joins and window functions. On a system with 100K+ workflow instances, these queries take minutes and lock rows.

**Prevention:**
- Build a separate `process_events` materialized view (or table) specifically for analytics: `{case_id, activity_name, start_time, end_time, performer, outcome}`
- Populate it asynchronously via event bus subscription, not by querying the operational tables
- Partition by month. Index on `(case_id, start_time)`
- For "directly-follows" analysis: pre-compute the directly-follows relation during event ingestion, storing `{case_id, activity_a, activity_b, count}` in a summary table
- Run analytics queries on a read replica if available, or during off-peak hours
- Set `statement_timeout` on analytics queries (30 seconds max) to prevent runaway queries from affecting the operational database

---

### Pitfall 14: CMIS Query Language (CMIS-QL) vs Existing DQL Engine

**What goes wrong:** The system already has a DQL-like query interface (Phase 11). CMIS-QL has similar but not identical syntax. Building a separate CMIS-QL parser creates two query engines that support different subsets of functionality.

**Prevention:**
- Map CMIS-QL to the existing query engine. CMIS-QL's `SELECT * FROM cmis:document WHERE cmis:name = 'foo'` translates to the existing search/query service with property name mapping
- Use a thin CMIS-QL parser (pyparsing or lark) that outputs the same internal query AST that the DQL engine uses
- The CMIS-QL spec is a subset of SQL-92 -- the existing expression evaluator may handle most of it with property name remapping

---

### Pitfall 15: Import/Export Large Files Exhaust Server Memory

**What goes wrong:** Export packages all documents as a ZIP. If the export includes 500 documents averaging 10MB each, the server attempts to build a 5GB ZIP in memory before sending it to the client.

**Prevention:**
- Stream ZIP construction: use Python's `zipfile.ZipFile` with a streaming response. Write chunks to the HTTP response as they are generated
- For imports: accept multipart uploads with streaming parsing. Do not buffer the entire upload
- Set a maximum export size (item count or estimated size) with a clear error message
- For very large exports: create the ZIP in MinIO (server-side) and return a presigned download URL

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Severity | Mitigation |
|-------------|---------------|----------|------------|
| LDAP/SAML/OAuth2 SSO | JWT flow breakage for Celery/Agent (1) | CRITICAL | Token abstraction layer, service tokens for background tasks |
| CMIS API | Dual-API inconsistency (4) | CRITICAL | Translation layer over existing services, not parallel implementation |
| CMIS API | CMIS-QL duplication (14) | MINOR | Map to existing query engine |
| WebDAV | Dual locking mechanisms (6) | MODERATE | Unify WebDAV locks with check-in/check-out |
| Email archiving | MIME parsing failures (7) | MODERATE | Robust parser library, dead-letter queue, raw .eml preservation |
| Workflow error handling | Compensation side-effect corruption (11) | MODERATE | Forward-only compensation, compensating notifications |
| Workflow versioning | In-flight instance corruption (2) | CRITICAL | Immutable installed templates, explicit migration only |
| Advanced joins | Token race conditions and leaks (3) | CRITICAL | FOR UPDATE locking, token cleanup, concurrent testing |
| Bulk operations | Memory exhaustion and lock contention (8) | MODERATE | Chunked processing, async jobs, fresh sessions per chunk |
| Import/Export | Circular references and FK violations (9) | MODERATE | Two-pass import with UUID remapping |
| Import/Export | Memory exhaustion on large exports (15) | MINOR | Streaming ZIP, size limits |
| System monitoring | Cardinality explosion (12) | MINOR | Bounded labels only, analytics in PostgreSQL not Prometheus |
| Tiered storage | Inconsistent reads during migration (10) | MODERATE | State machine migration, never delete before verified copy |
| Tamper-proof audit | Write throughput bottleneck (5) | CRITICAL | Async hash chaining via Celery worker, not in request path |
| Process analytics | Query performance on operational tables (13) | MINOR | Separate analytics table, async population, read replica |

## Integration Pitfalls (Cross-Feature)

These pitfalls arise from interactions BETWEEN the new features and the existing system:

| Integration | Pitfall | Prevention |
|-------------|---------|------------|
| SSO + WebDAV | WebDAV clients (Windows Explorer, macOS Finder) use HTTP Basic Auth, not SAML. SSO users cannot mount the WebDAV share | WebDAV endpoint accepts Basic Auth against local password OR an app-specific password/token. SSO users generate app passwords in their profile |
| SSO + CMIS | CMIS clients may use HTTP Basic Auth or OAuth2 Bearer tokens. SAML browser redirect is incompatible | CMIS endpoint supports both Basic Auth and Bearer token. Add OAuth2 client credentials grant for programmatic CMIS access |
| Bulk ops + Audit trail | Bulk delete of 10K documents creates 10K audit records in rapid succession, overwhelming the hash chain worker | Bulk operations create a SINGLE "bulk_delete" audit record with a summary (count, IDs in JSONB). Individual item records are optional/configurable |
| Workflow versioning + Process analytics | Analytics queries must handle mixed-version instances. A process path analysis spanning v1 and v2 templates produces nonsensical results | Analytics always scopes to a single template version. Cross-version comparison is a separate explicit report |
| Tiered storage + WebDAV | WebDAV expects immediate file access. Cold storage retrieval takes minutes/hours | WebDAV PROPFIND exposes a `storage-tier` custom property. GET on cold-tier documents returns 503 with Retry-After header, not a hang |
| Email archiving + Full-text search | Archived emails need full-text search. The existing search pipeline expects document files, not parsed email bodies | Email body text extracted during archiving and stored as the document's searchable content. Attachments become separate linked documents with their own search vectors |
| Import/Export + Tamper-proof audit | Importing entities creates audit records. The hash chain must not be broken by bulk-imported audit history from another system | Imported audit history goes into a separate `imported_audit_log` table with its own chain. The system's native chain is unaffected |

## Sources

- Codebase analysis: `security.py`, `dependencies.py`, `engine_service.py`, `minio_client.py`, `audit.py`, `workflow.py` models -- HIGH confidence
- [Orkes: Workflow Versioning and Backward Compatibility](https://orkes.io/blog/workflow-versioning-and-backward-compatibility-in-conductor/) -- MEDIUM confidence
- [WorkflowEngine: Schema Versioning](https://workflowengine.io/documentation/execution/scheme-update/) -- MEDIUM confidence
- [FastAPI WSGI Integration](https://fastapi.tiangolo.com/advanced/wsgi/) -- HIGH confidence
- [RFC 4918: WebDAV](https://datatracker.ietf.org/doc/html/rfc4918) -- HIGH confidence
- [CMIS 1.1 Specification](https://docs.oasis-open.org/cmis/CMIS/v1.1/CMIS-v1.1.html) -- HIGH confidence
- [Cossack Labs: Tamper-Proof Audit Logs](https://www.cossacklabs.com/blog/audit-logs-security/) -- MEDIUM confidence
- [CPython Issue #137687: base64 parser edge case](https://github.com/python/cpython/issues/137687) -- HIGH confidence
- [Last9: Managing High Cardinality in Prometheus](https://last9.io/blog/how-to-manage-high-cardinality-metrics-in-prometheus/) -- MEDIUM confidence
- [Medium: Deadlocks in PostgreSQL Bulk Updates](https://medium.com/@harshiljani2002/deadlocks-while-bulk-updating-in-postgresql-4af4161b7ff8) -- MEDIUM confidence
- [Springer: Enabling Efficient Process Mining on Large Data Sets](https://link.springer.com/article/10.1007/s10619-019-07270-1) -- MEDIUM confidence
