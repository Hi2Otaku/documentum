# Phase 41: Import/Export - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous YOLO mode)

<domain>
## Phase Boundary

Admin can export documents as ZIP packages (content + metadata JSON), export folder trees preserving hierarchy/ACLs/relationships. Admin can import ZIP packages recreating documents with conflict resolution (skip/overwrite/rename).

Requirements: IOEX-01, IOEX-02, IOEX-03, IOEX-04

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- ZIP format: manifest.json at root with metadata, content files in docs/ directory, folder structure in folders.json
- Export runs as Celery task (can be large), stores ZIP in MinIO temp bucket
- Import runs as Celery task, processes manifest, creates documents/folders
- Conflict strategies: skip (log and continue), overwrite (update existing), rename (append suffix)
- Reuse BulkJob model from Phase 40 for job tracking
- API: POST /api/v1/import-export/export, POST /api/v1/import-export/import, GET /api/v1/import-export/jobs
- Frontend: Export dialog on folder context menu + import page with file upload and strategy selection

</decisions>

<code_context>
## Existing Code Insights

- BulkJob model from Phase 40 reusable for job tracking
- MinIO client for file storage
- Document/folder services for CRUD

</code_context>

<specifics>
None.
</specifics>

<deferred>
None.
</deferred>
