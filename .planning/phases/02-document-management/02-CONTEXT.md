# Phase 2: Document Management - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can upload, version, lock, and retrieve documents through the system with files stored in MinIO and metadata in PostgreSQL. Covers DOC-01 through DOC-08.

</domain>

<decisions>
## Implementation Decisions

### Version Numbering
- Major versions created on check-in after approval (lifecycle-triggered), minor versions on regular check-in — mirrors Documentum's model
- Initial version number is 0.1 for first upload (draft state) — becomes 1.0 on first major promotion
- No new version created if content is unchanged on check-in (SHA-256 hash comparison)

### MinIO Storage Layout
- Single bucket "documents" with UUID-based keys: {doc_id}/{version_id}
- Original filename stored in document metadata only, not in MinIO object key

### Custom Metadata
- JSONB column `custom_properties` on the document table — flexible, queryable via PostgreSQL operators
- Schema-free — any JSON key-value pairs allowed, no validation schema per document type

### Claude's Discretion
- Upload size limits and chunked upload strategy
- File type detection/MIME handling
- Download endpoint design (streaming vs buffered)
- Error handling for MinIO connectivity issues

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/app/models/base.py` — BaseModel with UUID PK, timestamps, soft delete
- `src/app/models/workflow.py` — Already contains DocumentVersion and Document skeleton models
- `src/app/services/audit_service.py` — create_audit_record for logging document operations
- `src/app/core/database.py` — Async session factory
- `src/app/schemas/common.py` — EnvelopeResponse, PaginatedResponse patterns

### Established Patterns
- Service layer pattern: services handle business logic, routers handle HTTP
- Envelope response format: {"data": ..., "meta": ..., "errors": [...]}
- Offset pagination: ?page=1&page_size=20
- JWT auth via get_current_user dependency

### Integration Points
- Document routers register at /api/v1/documents
- MinIO client initialized in app lifespan or config
- Audit trail calls on every document mutation

</code_context>

<specifics>
## Specific Ideas

- Version numbering should feel like Documentum's model — draft versions are minor (0.1, 0.2), approved versions are major (1.0, 2.0)
- Check-in/check-out is the core locking mechanism — no concurrent editing without explicit lock

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-document-management*
*Context gathered: 2026-03-30*
