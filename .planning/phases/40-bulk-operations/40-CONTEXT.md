# Phase 40: Bulk Operations - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous YOLO mode)

<domain>
## Phase Boundary

Users can select multiple documents and apply batch update (metadata, lifecycle, ACL), batch delete, with background job tracking and partial failure reporting. Job history with success/failure counts.

Requirements: BULK-01, BULK-02, BULK-03, BULK-04

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- New BulkJob model: id, job_type, status (pending/running/completed/failed), total_count, success_count, failure_count, created_by, created_at, completed_at, results_json
- Celery task processes items one by one, updating progress
- API: POST /api/v1/bulk/update, POST /api/v1/bulk/delete, GET /api/v1/bulk/jobs, GET /api/v1/bulk/jobs/{id}
- Frontend: checkbox selection on document tables, bulk action toolbar, job progress dialog, job history page
- Partial failure: continue processing remaining items, collect errors per item

</decisions>

<code_context>
## Existing Code Insights

- Celery workers already configured
- Document CRUD services exist
- BrowsePage and DocumentsPage have document tables

</code_context>

<specifics>
## Specific Ideas

None beyond research guidance.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
