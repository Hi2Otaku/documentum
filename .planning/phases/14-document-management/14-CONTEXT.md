# Phase 14: Document Management - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the Documents page where users manage the full document lifecycle — uploading files (drag-and-drop + multi-file), browsing with filters, viewing version history, checking out/in documents, and transitioning lifecycle states. This follows the same split-pane pattern established in the Inbox.

</domain>

<decisions>
## Implementation Decisions

### Page Layout
- **D-01:** Split-pane layout matching Inbox pattern — document table on left, detail panel on right. Consistent UX across the app.
- **D-02:** Detail panel shows document metadata, version history list with download buttons, and action buttons (checkout/checkin, lifecycle).

### Upload Experience
- **D-03:** Inline drop zone at the top of the page — dashed-border area with upload button. Users can drag files onto it or click to browse.
- **D-04:** Multi-file upload supported. Each file creates a separate document. Sequential API calls with per-file progress indication.

### Version & Checkout UX
- **D-05:** Version history displayed as a section within the detail panel (not a separate tab). List of versions with version number, date, author, SHA-256 hash, and download button per version.
- **D-06:** Lock indicator: lock icon + "Checked out by [user]" shown in the table row. Prominent visibility so other users know the doc is locked.
- **D-07:** Check-in flow: user uploads a new file version while checking in. Dialog with file picker + optional comment.

### Lifecycle Transitions
- **D-08:** Current lifecycle state shown as a colored badge in the detail panel.
- **D-09:** Click the badge/dropdown to see valid next states (Draft→Review→Approved→Archived). Selecting one opens a confirmation dialog before transitioning.

### Claude's Discretion
- Table column choices and widths
- Empty state for no documents
- Loading skeleton pattern
- Filter UX (search bar, lifecycle dropdown, author filter)
- Upload progress indicator style
- Version history sort order (newest first)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend APIs
- `src/app/routers/documents.py` — Document endpoints (upload, list, detail, checkout, checkin, unlock, versions, download)
- `src/app/routers/lifecycle.py` — Lifecycle transition endpoints
- `src/app/schemas/document.py` — Request/response schemas
- `src/app/services/document_service.py` — Document business logic
- `src/app/core/minio_client.py` — MinIO file storage

### Frontend Patterns
- `frontend/src/pages/InboxPage.tsx` — Split-pane layout to replicate
- `frontend/src/components/inbox/InboxTable.tsx` — TanStack Table pattern to follow
- `frontend/src/components/inbox/InboxDetailPanel.tsx` — Detail panel pattern
- `frontend/src/pages/DocumentsPage.tsx` — Placeholder to replace
- `frontend/src/api/inbox.ts` — API module pattern to follow

### UI Components Available
- `frontend/src/components/ui/table.tsx`, `badge.tsx`, `dialog.tsx`, `card.tsx`, `select.tsx`, `skeleton.tsx`, `input.tsx`, `button.tsx`, `textarea.tsx`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- InboxPage split-pane layout — replicate for documents
- InboxTable — TanStack Table with filter/pagination
- WorkItemStateBadge pattern — adapt for lifecycle state badges
- sonner toasts — use for all mutations
- api/inbox.ts — follow envelope unwrapping pattern

### Established Patterns
- TanStack Query for data fetching (useQuery, useMutation, useQueryClient)
- shadcn Dialog for confirmations
- State filter via shadcn Select
- Pagination component pattern from InboxTable

### Integration Points
- DocumentsPage.tsx at /documents (already routed)
- authStore provides token for API calls
- Download via presigned URLs or direct API download endpoint

</code_context>

<specifics>
## Specific Ideas

No specific external references. Standard document management UI with established patterns from Inbox phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-document-management*
*Context gathered: 2026-04-06*
