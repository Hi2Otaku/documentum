# Architecture Patterns

**Domain:** Enterprise ECM platform -- v1.4 Enterprise Completeness integration
**Researched:** 2026-04-15

## Current Architecture Snapshot

The system is a well-structured monolith with clear separation of concerns, built over 33 phases (v1.0-v1.3):

```
                    +------------------+
                    |   React 19 SPA   |
                    |  (Vite + shadcn) |
                    |  12 pages, ~50   |
                    |  components      |
                    +--------+---------+
                             |
                    HTTP/SSE | REST /api/v1/*
                             |
                    +--------+---------+
                    |    FastAPI App    |
                    |  (Uvicorn ASGI)  |
                    +--------+---------+
                    |  Routers (26)    |
                    |  Services (22)   |
                    |  Models (12)     |
                    +--+-----+-----+--+
                       |     |     |
            +----------+  +--+--+  +-----------+
            |             |     |              |
      +-----+----+  +----+---+ +----+----+  +-+-------+
      |PostgreSQL |  | Redis  | |  MinIO  |  | Celery  |
      |  16       |  |  7     | | (S3)    |  | Workers |
      | (asyncpg) |  | broker | | 1 bucket|  | +Beat   |
      +-----------+  | pubsub | +---------+  | +Rend.  |
                     +--------+              +---------+
```

**Key architectural facts from code inspection:**

- **Auth:** JWT only (PyJWT + pwdlib/bcrypt). Single `get_current_user` dependency in `core/dependencies.py` that decodes JWT and does DB user lookup. No pluggable auth backend -- hardcoded DB user lookup by UUID from token `sub` claim.
- **Storage:** Single MinIO bucket ("documents"), single `core/minio_client.py` with `upload_object`/`download_object`/`delete_object`. All operations wrapped in `asyncio.to_thread()`. No storage abstraction layer.
- **Event bus:** In-process singleton `EventBus` class in `services/event_bus.py`. Persists events to `domain_events` table, dispatches to registered handlers synchronously within the request. Handlers registered via `@event_bus.on("event.type")` decorator.
- **Audit:** Simple `AuditLog` model with JSON `before_state`/`after_state` columns. No tamper detection, no hash chain, no sequence numbering.
- **Templates:** `ProcessTemplate` has `version` int field and `state` enum (DRAFT/VALIDATED/ACTIVE/DEPRECATED). No concurrent version management -- single row per template, version field incremented in place.
- **Engine:** Petri-net token-based execution in `engine_service.py`. Explicit state transition maps for workflows (5 states), activities (5 states), and work items (6 states). Only AND_JOIN and OR_JOIN trigger types.
- **Middleware:** Empty `middleware/` directory (only `__init__.py`).
- **Config:** `pydantic-settings` based `Settings` class with env vars. No auth backend config, no storage tier config, no monitoring thresholds.
- **Docker:** 6 containers: api, db, redis, minio, celery-worker, celery-beat, celery-rendition-worker.

---

## Integration Analysis: Feature by Feature

### 1. LDAP/SAML/OAuth2 SSO

**Integration point:** `core/dependencies.py` (`get_current_user`) and `core/security.py`

**What changes:**

| Type | File | Change |
|------|------|--------|
| NEW | `core/auth_backends.py` | Pluggable authentication backend interface (ABC) |
| NEW | `services/sso_service.py` | LDAP bind, SAML assertion parsing, OAuth2 code exchange |
| MODIFY | `core/dependencies.py` | `get_current_user` tries JWT first, delegates to configured backend on failure |
| MODIFY | `core/config.py` | Add `auth_backend`, `ldap_url`, `saml_metadata_url`, `oauth2_*` settings |
| MODIFY | `routers/auth.py` | Add `/auth/saml/callback`, `/auth/oauth2/callback`, `/auth/ldap/login` |
| MODIFY | `services/auth_service.py` | JIT user provisioning on first SSO login |
| MODIFY | `models/user.py` | Add `external_id`, `auth_provider` fields for SSO-provisioned users |
| MODIFY | Frontend `LoginPage.tsx` | SSO buttons, redirect flows |

**Architecture pattern:** Strategy pattern for auth backends. The `get_current_user` dependency remains the single entry point for all routers. Each backend implements `authenticate(credentials) -> User | None`. JWT stays the session token format even for SSO users -- SSO authenticates the user, then the system issues a JWT for subsequent requests.

```python
# core/auth_backends.py
class AuthBackend(ABC):
    @abstractmethod
    async def authenticate(self, db: AsyncSession, credentials: dict) -> User | None: ...

class DatabaseBackend(AuthBackend):
    """Current behavior -- username/password against users table."""

class LDAPBackend(AuthBackend):
    """LDAP bind + JIT user provisioning."""

class SAMLBackend(AuthBackend):
    """SAML assertion validation + JIT provisioning."""

class OAuth2Backend(AuthBackend):
    """OAuth2 authorization code exchange + JIT provisioning."""
```

**New Python dependencies:** `ldap3` (pure Python LDAP, no C deps), `python3-saml` (OneLogin SAML toolkit), `authlib` (OAuth2 code flow).

**Component boundary:** Auth backends are isolated behind an interface. The rest of the system never knows how the user authenticated -- it only sees the JWT. This is critical: CMIS, WebDAV, bulk operations, and every other feature that calls `get_current_user` works identically regardless of auth method.

### 2. CMIS API

**Integration point:** New API surface mounted parallel to existing REST API

**What changes:**

| Type | File | Change |
|------|------|--------|
| NEW | `routers/cmis.py` | CMIS AtomPub and Browser (JSON) bindings at `/cmis/` |
| NEW | `services/cmis_service.py` | Maps CMIS object model to existing Document/Folder/ACL models |
| NEW | `schemas/cmis.py` | CMIS type definitions, property mappings, CMIS error responses |
| MODIFY | `main.py` | Mount CMIS router at separate prefix (NOT under `/api/v1/`) |

**Architecture pattern:** Adapter/facade. CMIS service wraps existing `document_service`, `folder_service`, `acl_service`. No new database tables. CMIS types map to existing `DocumentType` model. CMIS "repository" is the entire system instance.

**Key design decision:** Mount CMIS at `/cmis/atom` (AtomPub binding) and `/cmis/browser` (JSON binding) as separate router groups. Do NOT mix with the internal REST API. The CMIS 1.1 spec prescribes its own URL patterns and response formats.

**CMIS service operations map to existing services:**

| CMIS Operation | Internal Service Call |
|---------------|----------------------|
| `getObject` | `document_service.get()` or `folder_service.get()` |
| `getChildren` | `folder_service.list_children()` |
| `createDocument` | `document_service.create()` |
| `createFolder` | `folder_service.create()` |
| `updateProperties` | `document_service.update()` |
| `deleteObject` | `document_service.delete()` or `folder_service.delete()` |
| `getContentStream` | `minio_client.download_object()` via `document_service` |
| `checkOut/checkIn` | `document_service.checkout()` / `document_service.checkin()` |
| `getACL` | `acl_service.get_permissions()` |
| `query` (CMIS SQL) | `query_service.execute()` (adapt DQL parser) |

**Component boundary:** CMIS introduces zero new domain models. It is purely a translation layer.

### 3. WebDAV

**Integration point:** New protocol endpoint, separate from REST API

**What changes:**

| Type | File | Change |
|------|------|--------|
| NEW | `routers/webdav.py` | WebDAV method handlers (PROPFIND, PROPPATCH, MKCOL, GET, PUT, DELETE, COPY, MOVE, LOCK, UNLOCK) |
| NEW | `services/webdav_service.py` | Maps WebDAV operations to existing document/folder services |
| NEW | `middleware/webdav_auth.py` | HTTP Basic Auth for WebDAV (OS clients don't do JWT) |
| MODIFY | `main.py` | Mount WebDAV handler at `/webdav/` prefix |

**Architecture pattern:** Protocol adapter. WebDAV is a different HTTP dialect over the same domain services. The critical nuance: WebDAV clients (Windows Explorer, macOS Finder, LibreOffice) use HTTP Basic Auth, not Bearer tokens. This requires the auth backend abstraction from feature #1 to support Basic Auth -> user lookup -> internal JWT issuance.

**Key design decision:** FastAPI can handle custom HTTP methods via `@router.api_route(methods=["PROPFIND"])`. For the `/webdav/` prefix, add a dedicated middleware that converts Basic Auth to an internal user context before the request reaches the router.

**Dependency on feature #1 (SSO):** The auth backend abstraction enables Basic Auth for WebDAV alongside JWT for REST and SSO callbacks. Without the abstraction, WebDAV would need a separate parallel auth implementation.

**WebDAV URL mapping:**

```
/webdav/                    -> root (list cabinets)
/webdav/{cabinet}/          -> cabinet contents
/webdav/{cabinet}/{folder}/ -> folder contents
/webdav/{cabinet}/.../{file} -> document content (GET/PUT)
```

### 4. Email Archiving

**Integration point:** New ingest pipeline, new Celery task

**What changes:**

| Type | File | Change |
|------|------|--------|
| NEW | `services/email_service.py` | Email parsing (headers, body, attachments), IMAP polling |
| NEW | `tasks/email_ingestion.py` | Celery periodic task to poll mailbox |
| NEW | `models/email.py` | `EmailMessage` model (from, to, subject, message_id, thread references) linking to Document |
| NEW | `routers/email.py` | Manual .eml import endpoint, mailbox configuration endpoints |
| MODIFY | `services/document_service.py` | Support creating documents from email (body as content, attachments as related docs) |
| MODIFY | Celery Beat schedule | Add email polling interval |

**Architecture pattern:** Ingest pipeline. Email arrives (IMAP poll or manual upload) -> parse headers/body/attachments -> create Document for email body -> create Documents for each attachment -> link via existing `DocumentRelationship` model (relationship_type: `IS_PART_OF`) -> store all in MinIO -> index for search via existing search infrastructure.

**Key design decision:** Use Celery Beat for IMAP polling (simpler than running an SMTP server, which requires port 25 and MX records). For demo/testing, support manual .eml file upload via REST endpoint. Use Python's built-in `email` module for parsing (stdlib, no external deps needed for basic RFC 5322 parsing).

### 5. Workflow Error Handling & Compensation

**Integration point:** `services/engine_service.py` -- core engine modifications

**What changes:**

| Type | File | Change |
|------|------|--------|
| MODIFY | `models/workflow.py` | Add `ExceptionHandler` model (linked to ActivityTemplate), add `is_compensation` flag to ActivityTemplate |
| MODIFY | `models/enums.py` | Add `COMPENSATING` to ActivityState |
| MODIFY | `services/engine_service.py` | Wrap activity execution in try/catch, look up exception handlers, execute compensation chain |
| MODIFY | `schemas/template.py` | Exception handler configuration in template design |
| MODIFY | Frontend designer | Exception handler nodes and compensation flow edges |

**Architecture pattern:** Exception handler chain. Each activity template can declare 0..N exception handlers with conditions (exception type match, max retry count). When an activity enters ERROR state:

1. Check handler chain for matching handler
2. If handler says "retry" -> retry with exponential backoff via Celery
3. If handler says "compensate" -> execute compensation activities in reverse order of completed activities
4. If handler says "halt" -> halt workflow for admin intervention
5. If no handler matches -> mark workflow FAILED (current behavior, backward compatible)

**Key design decision:** Compensation activities are regular ActivityTemplate rows with `is_compensation = True`. They execute in reverse order of the activities that completed. This reuses the existing activity execution infrastructure entirely.

### 6. Workflow Versioning

**Integration point:** `services/template_service.py` and `models/workflow.py`

**What changes:**

| Type | File | Change |
|------|------|--------|
| MODIFY | `models/workflow.py` | Add `template_family_id` UUID to ProcessTemplate, unique constraint on `(template_family_id, version)` |
| MODIFY | `services/template_service.py` | "Create new version" duplicates template with incremented version, old stays ACTIVE until deprecated |
| MODIFY | `services/engine_service.py` | `instantiate_workflow()` resolves latest ACTIVE version in family |
| MODIFY | `routers/templates.py` | Version listing, version comparison, deprecation, family-scoped queries |
| MODIFY | Frontend template list | Version history panel, create-new-version action |

**Architecture pattern:** Immutable versioned records. Each installed version is a separate `ProcessTemplate` row (with its own `ActivityTemplate`, `FlowTemplate`, `ProcessVariable` rows). `WorkflowInstance.template_id` FK points to a specific version row. The `template_family_id` groups all versions of the same logical process.

**Key design decision:** Do NOT migrate in-flight workflows to new template versions. Running instances keep their template version. New instances automatically use the latest ACTIVE version in the family. This is the Documentum approach and avoids the enormous complexity of runtime template migration. A `ProcessTemplate` in DEPRECATED state cannot spawn new instances but existing instances continue normally.

**Migration:** Backfill existing templates: `UPDATE process_templates SET template_family_id = id WHERE template_family_id IS NULL` (each existing template becomes the sole member of its own family).

### 7. Advanced Join Semantics

**Integration point:** `models/enums.py` and `services/engine_service.py`

**What changes:**

| Type | File | Change |
|------|------|--------|
| MODIFY | `models/enums.py` | Extend `TriggerType` with WEIGHTED_JOIN, CANCELLING_JOIN, TIMEOUT_JOIN, N_OF_M_JOIN |
| MODIFY | `models/workflow.py` | Add `join_config` JSONB field to `ActivityTemplate` |
| MODIFY | `services/engine_service.py` | Token counting logic in join evaluation becomes strategy-based |
| MODIFY | `schemas/template.py` | Join configuration schema |
| MODIFY | Frontend designer | Join type selector in activity properties panel |

**Architecture pattern:** Strategy on join evaluation. Current AND/OR logic is simple token counting. New types add configurable conditions:

| Join Type | Behavior | Config |
|-----------|----------|--------|
| AND_JOIN | All incoming tokens required (existing) | None |
| OR_JOIN | Any one token sufficient (existing) | None |
| N_OF_M_JOIN | N of M incoming paths must complete | `{"threshold": 2}` |
| WEIGHTED_JOIN | Sum of path weights >= threshold | `{"weights": {"flow_id": 3}, "threshold": 5}` |
| CANCELLING_JOIN | First token fires, cancels pending siblings | None |
| TIMEOUT_JOIN | AND-join with deadline, falls back to OR | `{"timeout_seconds": 3600}` |

**Component boundary:** All join logic stays in `engine_service.py`. No new services needed. This is a refinement of existing engine logic.

### 8. Bulk Operations

**Integration point:** New job tracking infrastructure

**What changes:**

| Type | File | Change |
|------|------|--------|
| NEW | `models/job.py` | `BulkJob` model (type, status, progress, error details) |
| NEW | `services/bulk_service.py` | Orchestrates bulk operations, creates job record, dispatches to Celery |
| NEW | `tasks/bulk_operations.py` | Celery tasks for bulk delete, update, reclassify, permission change |
| NEW | `routers/bulk.py` | POST to start job, GET status, GET list jobs |
| NEW | Frontend bulk operation UI | Multi-select -> action -> progress tracking |

**Architecture pattern:** Async job queue with progress tracking.

```
POST /api/v1/bulk/delete {document_ids: [...]}
  -> bulk_service.create_job(type="delete", items=ids) -> returns job_id immediately
  -> Celery task: process items sequentially
    -> for each: document_service.delete() + update job.completed_items
  -> Frontend polls GET /api/v1/bulk/jobs/{job_id} for progress
```

**Key design decision:** Always use Celery for bulk operations, never in-request. Even "small" batches (50 items) can timeout if each item has ACL checks, audit logging, event emission, and MinIO operations. Redis-backed result tracking for real-time progress.

### 9. Import/Export

**Integration point:** Serialization layer over existing models

**What changes:**

| Type | File | Change |
|------|------|--------|
| NEW | `services/import_export_service.py` | Serialize/deserialize templates, documents, folder trees, ACLs |
| NEW | `routers/import_export.py` | Export (GET -> ZIP), Import (POST ZIP) |
| NEW | `tasks/import_export.py` | Celery task for large imports |
| NEW | `schemas/import_export.py` | Package manifest schema |

**Architecture pattern:** Package-based serialization. Export creates a ZIP containing:

```
package.zip
  manifest.json          # metadata, checksums, ID mapping table
  templates/
    {family_id}.json     # template definition with activities, flows, variables
  documents/
    {doc_id}/
      metadata.json      # document properties, type, lifecycle state
      content/           # binary files (all versions)
      acl.json           # permission entries
  folders/
    tree.json            # folder hierarchy
  acls/
    folder_acls.json     # folder-level permissions
```

**Key design decision:** UUID remapping on import (new UUIDs generated, old-to-new mapping in manifest). This allows importing the same package multiple times without conflicts. SHA-256 checksums in manifest for integrity verification.

### 10. System Monitoring

**Integration point:** New observability layer, read-only

**What changes:**

| Type | File | Change |
|------|------|--------|
| NEW | `routers/monitoring.py` | Deep health checks, queue depths, connection pool stats |
| NEW | `services/monitoring_service.py` | Collect metrics from all subsystems |
| NEW | `tasks/monitoring.py` | Celery Beat task for periodic metric collection + alerting |
| MODIFY | `core/config.py` | Alerting thresholds (queue depth, error rate, storage usage) |
| NEW | Frontend monitoring dashboard page |

**Architecture pattern:** Self-contained pull-based monitoring. No external infrastructure (no Prometheus/Grafana). Monitoring endpoints expose current state on demand. Celery Beat task runs periodic checks and emits alert events through the event bus when thresholds exceeded.

**Metrics collected:**

| Subsystem | Metrics |
|-----------|---------|
| PostgreSQL | Connection pool size/available, query latency, table sizes |
| Redis | Memory usage, connected clients, queue lengths |
| MinIO | Bucket sizes, object counts per tier |
| Celery | Queue depths per queue, active/reserved task counts, worker status |
| Application | Active workflows, pending work items, error rate, event bus throughput |

**Key design decision:** If the user later wants Prometheus, add a `/metrics` endpoint in Prometheus exposition format. But for internal/personal use, the built-in monitoring dashboard is sufficient.

### 11. Tiered Storage

**Integration point:** `core/minio_client.py` -- requires a storage abstraction layer

**What changes:**

| Type | File | Change |
|------|------|--------|
| NEW | `core/storage.py` | `StorageBackend` abstract class (upload, download, delete, copy) |
| NEW | `core/storage_backends/minio_backend.py` | Wraps existing MinIO client operations |
| NEW | `core/storage_backends/filesystem_backend.py` | Local filesystem for cold/archive tier |
| NEW | `models/storage.py` | `StorageTier` config model, `StoragePolicy` model (rules) |
| NEW | `services/storage_service.py` | Policy evaluation, tier migration, transparent download routing |
| NEW | `tasks/storage_migration.py` | Celery task for background tier migration |
| MODIFY | `models/document.py` | Add `storage_tier` field to `DocumentVersion` (default "hot") |
| MODIFY | `services/document_service.py` | Route uploads/downloads through storage service |
| REFACTOR | `core/minio_client.py` | Extract into `storage_backends/minio_backend.py` |

**Architecture pattern:** Strategy pattern for storage backends.

```
                storage_service.download(version)
                        |
            +-----------+-----------+
            |           |           |
       hot (MinIO    warm (MinIO   cold (MinIO
       "documents"   "documents-   "documents-
        bucket)       warm")        cold" or
                                    filesystem)
```

**Tier definitions:**

| Tier | Backend | Use Case | Policy Trigger |
|------|---------|----------|----------------|
| Hot | MinIO `documents` bucket | Active documents, recent uploads | Default |
| Warm | MinIO `documents-warm` bucket | Infrequently accessed, still needs fast retrieval | No access in 90 days |
| Cold | MinIO `documents-cold` bucket or filesystem | Archived, regulatory retention | Lifecycle state = ARCHIVED |

**Key design decision:** All tiers use MinIO buckets initially (simplest). "Cold" can be swapped to filesystem backend for true cost savings on local deployment. The `StorageBackend` abstraction makes this a config change, not a code change.

### 12. Tamper-Proof Audit

**Integration point:** `models/audit.py` and `services/audit_service.py`

**What changes:**

| Type | File | Change |
|------|------|--------|
| MODIFY | `models/audit.py` | Add `hash` (SHA-256), `previous_hash`, `sequence_number` (monotonic) to AuditLog |
| MODIFY | `services/audit_service.py` | Compute hash chain on every new record |
| NEW | `services/audit_verification_service.py` | Walk chain and verify every hash |
| MODIFY | `routers/audit.py` | Add verification endpoint, tamper detection report |
| NEW | `tasks/audit_verification.py` | Celery Beat task for periodic chain verification |

**Architecture pattern:** Hash chain (blockchain-lite). Each audit record includes:

```
hash = SHA-256(
    sequence_number |
    entity_type |
    entity_id |
    action |
    user_id |
    timestamp.isoformat() |
    json.dumps(before_state, sort_keys=True) |
    json.dumps(after_state, sort_keys=True) |
    previous_hash
)
```

Any modification to any historical record breaks the chain from that point forward. Verification walks the chain and recomputes hashes.

**Key design decision:** Use PostgreSQL SEQUENCE for `sequence_number` (not application-level counter) to guarantee monotonic ordering even under concurrent writes. The first record's `previous_hash` is a well-known genesis value (e.g., SHA-256 of "GENESIS").

**Migration:** Backfill existing audit records with hash chain. Run a one-time migration task that walks all existing records in timestamp order, assigns sequence numbers, and computes the hash chain.

### 13. Process Analytics

**Integration point:** Event bus data + existing execution data

**What changes:**

| Type | File | Change |
|------|------|--------|
| NEW | `services/analytics_service.py` | Aggregate execution data, compute metrics |
| NEW | `routers/analytics.py` | Analytics query endpoints |
| NEW | `tasks/analytics.py` | Celery Beat task for periodic aggregation |
| NEW | `models/analytics.py` | `ProcessMetricsSummary` (pre-computed daily/weekly aggregates) |
| NEW | Frontend analytics page | Recharts visualizations |

**Architecture pattern:** Pre-computed aggregates. Raw data exists in `execution_log`, `audit_log`, `domain_events`. Analytics service aggregates into summary tables on a schedule. Frontend queries summaries for fast dashboard rendering. On-demand drill-down queries raw tables.

**Metrics:**

| Metric | Source | Computation |
|--------|--------|-------------|
| Cycle time per activity | execution_log timestamps | end_time - start_time per activity instance |
| Bottleneck detection | activity instance durations | Activities with highest average wait time |
| Throughput per template | workflow_instances | Completed instances per time period |
| SLA compliance rate | workflow_instances + timer config | % completed within deadline |
| Performer workload | work_items | Items per user per period |

**Key design decision:** Process mining (discovering workflows from execution logs) is a stretch goal. Start with descriptive analytics computed from existing data. No ML infrastructure needed.

### 14. Frontend Gap Closure (6 UI Panels)

**Integration point:** Frontend only -- all backend APIs already exist

**What changes (all frontend):**

| Component | Backend API | Status |
|-----------|-------------|--------|
| `pages/SignaturesPage.tsx` | `routers/signatures.py` | API exists, no UI |
| `pages/RetentionPage.tsx` | `routers/retention.py` | API exists, no UI |
| `components/documents/AclPanel.tsx` | ACL endpoints on documents router | API exists, no UI |
| `pages/QueueAdminPage.tsx` | `routers/queues.py` | API exists, no UI |
| Fix lifecycle state filter | `routers/documents.py` | API accepts filter, UI doesn't send it |
| `pages/NotificationPreferencesPage.tsx` | `routers/notifications.py` | API exists, no UI |
| `api/signatures.ts`, `api/retention.ts` | -- | API client files missing |

**Architecture pattern:** Standard CRUD pages consuming existing REST endpoints. No architectural novelty. Pure frontend work.

---

## Recommended Architecture: v1.4 Target State

### Layer Diagram

```
+---------------------------------------------------------------------+
|                         React 19 SPA                                |
|  18+ pages | analytics dashboard | bulk ops UI | SSO login          |
+---------------------------------------------------------------------+
        |              |              |              |
     REST API      CMIS API       WebDAV        SSE/Events
    /api/v1/*     /cmis/*        /webdav/*      /api/v1/events/stream
        |              |              |              |
+---------------------------------------------------------------------+
|                   Auth Layer (pluggable)                             |
|  JWT (default) | LDAP | SAML | OAuth2 | Basic Auth (WebDAV)        |
+---------------------------------------------------------------------+
|                                                                     |
|  +-----------------+  +------------------+  +--------------------+  |
|  | Domain Services |  | Protocol Adapters|  | Infrastructure Svc |  |
|  | engine, docs,   |  | CMIS facade      |  | monitoring, bulk   |  |
|  | templates,      |  | WebDAV adapter   |  | jobs, import/      |  |
|  | folders, search |  | email ingest     |  | export, analytics  |  |
|  +--------+--------+  +--------+---------+  +---------+----------+  |
|           |                     |                      |            |
|  +--------+--------+  +--------+---------+  +----------+---------+  |
|  | Storage Layer   |  | Event Bus        |  | Audit Chain        |  |
|  | tiered: hot/    |  | in-process +     |  | hash-linked SHA256 |  |
|  | warm/cold via   |  | Redis pub/sub    |  | with sequence nums |  |
|  | StorageBackend  |  |                  |  |                    |  |
|  +-----------------+  +------------------+  +--------------------+  |
+---------------------------------------------------------------------+
        |              |              |              |
   PostgreSQL      Redis          MinIO          Celery
   (data+audit     (broker+       (tiered         (workers per
    +analytics)     cache+         buckets:        queue: main,
                    pubsub)        hot/warm/       bulk, email,
                                   cold)           rendition,
                                                   storage)
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Auth Layer (`core/auth_backends.py`) | Authenticate users via JWT, LDAP, SAML, OAuth2, Basic Auth | All routers via `get_current_user` dependency |
| Protocol Adapters (CMIS, WebDAV) | Translate external protocols to internal service calls | Domain Services, Auth Layer |
| Domain Services (existing 22 + 2 new) | Core business logic -- workflows, documents, folders, templates | Models, Storage Layer, Event Bus, Audit |
| Storage Layer (`core/storage.py`) | Abstract file storage across hot/warm/cold tiers | MinIO backends, filesystem backend |
| Event Bus (existing) | Emit and dispatch domain events | All services (emitters), handlers (consumers) |
| Audit Chain (enhanced) | Tamper-proof audit logging with SHA-256 hash chain | Event Bus (listener), PostgreSQL |
| Job Queue (new) | Bulk operations, import/export, email ingestion, storage migration | Celery, Domain Services |
| Analytics (new) | Pre-computed process metrics | Execution logs, Event Bus, PostgreSQL |
| Monitoring (new) | Health checks, metrics, alerting | All infrastructure (DB, Redis, MinIO, Celery) |

### New Components vs Modifications

```
EXISTING (modify)                         NEW (create)
================================         ================================
core/
  config.py           [+15 settings]     auth_backends.py (ABC + 4 impls)
  dependencies.py     [+auth dispatch]   storage.py (ABC)
  security.py         [minor]            storage_backends/
  minio_client.py     [refactor out]       minio_backend.py
                                           filesystem_backend.py

models/
  audit.py            [+hash,seq,prev]   job.py (BulkJob)
  document.py         [+storage_tier]    storage.py (StorageTier, StoragePolicy)
  workflow.py         [+family_id,       email.py (EmailMessage)
                       +join_config,     analytics.py (ProcessMetricsSummary)
                       +is_compensation,
                       +ExceptionHandler]
  enums.py            [+5 new enums]
  user.py             [+external_id,
                       +auth_provider]

services/
  auth_service.py     [+JIT provision]   sso_service.py
  engine_service.py   [+error handling,  cmis_service.py
                       +advanced joins]  webdav_service.py
  template_service.py [+versioning]      email_service.py
  document_service.py [+storage tier]    bulk_service.py
  audit_service.py    [+hash chain]      import_export_service.py
                                         monitoring_service.py
                                         storage_service.py
                                         audit_verification_service.py
                                         analytics_service.py

routers/
  auth.py             [+SSO callbacks]   cmis.py
  audit.py            [+verify endpoint] webdav.py
  templates.py        [+version mgmt]    email.py
                                         bulk.py
                                         import_export.py
                                         monitoring.py
                                         analytics.py

middleware/
  (empty __init__.py)                    webdav_auth.py

tasks/
  (existing 5 unchanged)                 email_ingestion.py
                                         bulk_operations.py
                                         import_export.py
                                         monitoring.py
                                         storage_migration.py
                                         analytics.py
                                         audit_verification.py

frontend/pages/
  LoginPage.tsx       [+SSO buttons]     SignaturesPage.tsx
  DocumentsPage.tsx   [+lifecycle fix]   RetentionPage.tsx
  TemplateListPage.tsx [+versions]       QueueAdminPage.tsx
                                         NotificationPrefsPage.tsx
                                         MonitoringPage.tsx
                                         AnalyticsPage.tsx
                                         BulkJobsPage.tsx

frontend/api/
  (existing unchanged)                   signatures.ts
                                         retention.ts
                                         bulk.ts
                                         monitoring.ts
                                         analytics.ts
                                         importExport.ts
```

**Summary counts:** 12 files modified, 35+ new files created. 6 new Celery task modules. 8 new routers. 10 new services. 5 new models.

---

## Data Flow Diagrams for Key Integration Points

### SSO Login Flow

```
Browser -> "Login with SAML" button
  -> Redirect to IdP (identity provider)
  -> IdP authenticates user
  -> POST /auth/saml/callback (SAML assertion)
  -> sso_service.validate_saml_assertion(assertion)
  -> auth_service.find_or_create_user(external_id, provider="saml", attrs)
  -> security.create_access_token({"sub": user.id})
  -> JWT returned -> browser stores token -> all subsequent requests use JWT
```

### Tiered Storage Flow

```
Celery Beat (every hour) -> tasks/storage_migration.evaluate_policies()
  -> storage_service.find_migration_candidates(all_policies)
     [SQL: documents not accessed in 90 days AND storage_tier = "hot"]
  -> for each candidate:
     -> storage_service.migrate(doc_version, from="hot", to="warm")
       -> hot_backend.download(object_key)
       -> warm_backend.upload(object_key, data)
       -> hot_backend.delete(object_key)
       -> UPDATE document_versions SET storage_tier = "warm"
       -> audit_service.log("storage.migrated", ...)
```

### Bulk Operation Flow

```
User selects 200 documents -> clicks "Bulk Delete"
  -> POST /api/v1/bulk/delete {document_ids: [...200 UUIDs...]}
  -> bulk_service.create_job(type="delete", items=200) -> returns job_id
  -> Celery task dispatched to "bulk" queue
  -> Task processes items one by one:
     -> document_service.delete(id) + event_bus.emit + audit
     -> UPDATE bulk_jobs SET completed_items = completed_items + 1
     -> On error: log to job.errors JSONB, increment error_items
  -> Frontend polls GET /api/v1/bulk/jobs/{job_id}
     -> Returns {status: "running", total: 200, completed: 147, errors: 2}
```

### Email Archiving Flow

```
Celery Beat (every 5 min) -> tasks/email_ingestion.poll_mailbox()
  -> email_service.connect_imap(settings.imap_url, credentials)
  -> email_service.fetch_unseen_messages()
  -> for each message:
     -> email_service.parse(raw_email) -> EmailParsed(headers, body_html, body_text, attachments[])
     -> document_service.create(title=subject, content=body, type="email")
     -> for each attachment:
        -> document_service.create(title=filename, content=bytes)
        -> relationship_service.create(email_doc, attachment_doc, "IS_PART_OF")
     -> email_model = EmailMessage(document_id=email_doc.id, from=..., to=..., subject=...)
     -> Mark message as seen on IMAP server
     -> event_bus.emit("email.archived")
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Protocol Adapters Bypassing Service Layer
**What:** CMIS or WebDAV endpoints directly querying SQLAlchemy models or calling MinIO
**Why bad:** Skips ACL checks, audit logging, event emission, business validation. Creates parallel code paths that diverge from REST API behavior over time.
**Instead:** CMIS and WebDAV must ONLY call existing domain services. Protocol adapters translate request format and response format -- nothing more.

### Anti-Pattern 2: In-Request Bulk Processing
**What:** Processing 100+ items synchronously in an HTTP request handler
**Why bad:** HTTP timeouts (30s default), no progress visibility, no retry on partial failure, blocks the async event loop.
**Instead:** Always dispatch to Celery for operations over ~10 items. Return a job ID immediately. Frontend polls for progress.

### Anti-Pattern 3: Mutable Template Versioning
**What:** Overwriting `ProcessTemplate` fields to "update" a version, mutating rows that in-flight workflows reference via FK
**Why bad:** Changes the template definition for currently running workflows. Can cause token routing errors, missing activities, broken flows.
**Instead:** New version = new row. `template_family_id` groups versions. FKs point to immutable version rows. Never mutate an ACTIVE or DEPRECATED template.

### Anti-Pattern 4: Storage Tier Logic Scattered in Services
**What:** `if tier == "hot": use_minio_bucket_a() elif tier == "cold": use_filesystem()` throughout document_service, rendition_service, etc.
**Why bad:** Every new tier or backend change requires editing every file that touches storage.
**Instead:** `StorageBackend` abstract class. `storage_service.download(version)` resolves the tier from `version.storage_tier` and delegates transparently.

### Anti-Pattern 5: Separate Auth Per Protocol
**What:** WebDAV implementing its own user lookup, CMIS implementing its own token validation, REST keeping its own separate flow
**Why bad:** Auth bugs and inconsistencies multiply. A user disabled in one flow might still work in another.
**Instead:** All auth flows converge on `get_current_user` -> User object. Auth backends are the abstraction. WebDAV Basic Auth middleware converts credentials to a User object using the same backend chain.

### Anti-Pattern 6: Audit Hash Chain Without DB Sequence
**What:** Using application-level counters or timestamps for audit chain ordering
**Why bad:** Concurrent inserts can produce duplicate or out-of-order sequence numbers, breaking the hash chain verification
**Instead:** Use PostgreSQL SEQUENCE (CREATE SEQUENCE audit_log_seq) for guaranteed monotonic ordering even under concurrent writes.

---

## Suggested Build Order (Dependency-Driven)

The dependencies between features determine the build order:

```
Feature Dependency Graph:

  Auth Backends (#1)
    |-- CMIS (#2) needs pluggable auth
    |-- WebDAV (#3) needs Basic Auth backend
    '-- Email (#4) needs auth for IMAP config endpoints

  Storage Abstraction (#11)
    |-- Email (#4) creates documents via storage layer
    |-- Import/Export (#9) creates documents via storage layer
    '-- Bulk Ops (#8) deletes documents via storage layer

  Workflow Versioning (#6)
    '-- Error Handling (#5) compensation activities are part of templates

  Frontend Gap Closure (#14) -- no backend deps (APIs exist)
  Advanced Joins (#7) -- no cross-feature deps
  Tamper Audit (#12) -- no cross-feature deps (but schema change: do early)
  Monitoring (#10) -- no deps (read-only)
  Analytics (#13) -- no deps (reads existing data)
  Bulk Ops (#8) -- independent (new job model)
```

**Recommended phase sequence:**

| Phase | Feature | Rationale |
|-------|---------|-----------|
| 34 | Frontend Gap Closure (#14) | Pure UI, zero backend risk, immediate user value, can ship independently |
| 35 | Tamper-Proof Audit (#12) | Schema change to audit_log table -- do early before more audit records accumulate. Backfill migration is cheaper now. |
| 36 | Auth Backend Abstraction + SSO (#1) | Foundation: CMIS, WebDAV, email all depend on pluggable auth |
| 37 | Storage Abstraction + Tiered Storage (#11) | Foundation: refactors minio_client.py that email, import/export, bulk ops all use |
| 38 | Workflow Versioning (#6) | Must precede error handling. Template schema change. |
| 39 | Advanced Join Semantics (#7) | Engine internals, no external deps, pairs well with versioning phase |
| 40 | Workflow Error Handling & Compensation (#5) | Needs versioning from phase 38. Completes engine enhancements. |
| 41 | Bulk Operations (#8) | Independent job queue pattern. Needed before import/export. |
| 42 | CMIS API (#2) | Needs auth abstraction (phase 36). High integration value. |
| 43 | WebDAV (#3) | Needs auth abstraction (phase 36). Desktop integration. |
| 44 | Email Archiving (#4) | Needs auth (36) and storage (37). Ingest pipeline. |
| 45 | Import/Export (#9) | Needs stable models from all prior phases. Uses bulk job pattern from phase 41. |
| 46 | System Monitoring (#10) | Read-only, no deps, but benefits from seeing all subsystems in final form. |
| 47 | Process Analytics (#13) | Needs stable execution data. Benefits from monitoring infrastructure. |

**Phase ordering rationale:**

1. **Frontend gap closure first** -- zero backend risk, immediate user value, proves existing APIs work correctly (may uncover API bugs that inform later phases)
2. **Tamper audit early** -- adding `hash`, `previous_hash`, `sequence_number` columns to `audit_log` requires backfilling all existing records. The more records that exist, the longer the migration. Do it before the 13 remaining features each add more audit records.
3. **Auth + Storage abstractions next** -- these are the two foundational refactors. Auth abstraction is needed by CMIS, WebDAV, and email. Storage abstraction is needed by email, import/export, and bulk operations.
4. **Engine enhancements (versioning, joins, error handling)** -- grouped together as they all modify `engine_service.py`. Versioning must precede error handling because compensation activities are part of templates.
5. **Bulk operations before import/export** -- import/export reuses the bulk job tracking pattern.
6. **CMIS and WebDAV after auth** -- both are protocol adapters that depend on pluggable auth.
7. **Email after both auth and storage** -- needs IMAP credentials management (auth) and document creation (storage).
8. **Monitoring and analytics last** -- they are read-only observation layers that benefit from seeing the final system state.

---

## Docker Compose Changes (v1.4)

No new infrastructure services needed. All 14 features use existing PostgreSQL, Redis, MinIO, and Celery.

**New Celery queue isolation:**

```yaml
# Additions to docker-compose.yml

celery-bulk-worker:
  # ... same base config as celery-worker ...
  command: celery -A app.celery_app worker -Q bulk,import_export --concurrency=2 --loglevel=info

celery-email-worker:
  # ... same base config ...
  command: celery -A app.celery_app worker -Q email --concurrency=1 --loglevel=info
  # concurrency=1 prevents duplicate email processing
```

**MinIO additional buckets** (created at startup):

```python
# core/storage.py -- ensure_storage_buckets()
BUCKETS = ["documents", "documents-warm", "documents-cold"]
```

**New environment variables** (added to api + worker containers):

```yaml
# SSO
- AUTH_BACKEND=database  # or "ldap", "saml", "oauth2"
- LDAP_URL=ldap://ldap.example.com
- SAML_METADATA_URL=https://idp.example.com/metadata
- OAUTH2_CLIENT_ID=...
- OAUTH2_CLIENT_SECRET=...
# Email
- IMAP_URL=imaps://mail.example.com
- IMAP_USERNAME=...
- IMAP_PASSWORD=...
# Storage tiers
- STORAGE_WARM_BUCKET=documents-warm
- STORAGE_COLD_BUCKET=documents-cold
```

---

## Scalability Considerations

| Concern | Current (v1.3) | v1.4 Design | At Scale |
|---------|----------------|-------------|----------|
| Auth | JWT decode per request | Add Redis token cache (60s TTL) for SSO-validated users | Token cache eliminates repeated IdP round-trips |
| Storage | Single MinIO bucket | Multiple buckets per tier, `StorageBackend` abstraction | Add S3-compatible cloud backend without code changes |
| Bulk ops | N/A | Celery "bulk" queue, per-item processing | Add more bulk workers; chunk large jobs |
| Audit chain | Simple INSERT | `sequence_number` via PostgreSQL SEQUENCE, hash on every insert | Advisory lock or sequence guarantees ordering under concurrency |
| CMIS/WebDAV | N/A | Same FastAPI process | Separate worker processes via `--workers` if traffic justifies |
| Analytics | N/A | Pre-computed summaries avoid real-time aggregation | Partition summary tables by time period |
| Email ingest | N/A | Celery concurrency=1 per mailbox | One worker per mailbox prevents duplicates |
| Monitoring | N/A | Self-monitoring via /health/deep | Add Prometheus /metrics endpoint for external monitoring if needed |

---

## Sources

- Codebase inspection of all 12 model files, 22 service files, 26 router files, frontend structure (HIGH confidence)
- `core/dependencies.py` -- current auth flow analysis (HIGH confidence)
- `core/minio_client.py` -- current storage interface analysis (HIGH confidence)
- `services/engine_service.py` -- current engine state machines and join logic (HIGH confidence)
- `models/audit.py` -- current audit schema (HIGH confidence)
- `docker-compose.yml` -- current infrastructure topology (HIGH confidence)
- [CMIS 1.1 OASIS Standard](http://docs.oasis-open.org/cmis/CMIS/v1.1/CMIS-v1.1.html) -- MEDIUM confidence (training data)
- [WebDAV RFC 4918](https://tools.ietf.org/html/rfc4918) -- HIGH confidence (stable standard)
- [ldap3 Python library](https://ldap3.readthedocs.io/) -- MEDIUM confidence (library recommendation from training data)
- [authlib OAuth2](https://docs.authlib.org/) -- MEDIUM confidence (library recommendation from training data)
- [python3-saml](https://github.com/SAML-Toolkits/python3-saml) -- MEDIUM confidence (library recommendation from training data)
