# Phase 32: Document-First Navigation - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — recommended defaults selected)

<domain>
## Phase Boundary

This phase delivers a unified browse experience at `/browse` that becomes the primary entry point for the application. Users navigate a collapsible folder tree sidebar, view documents in a content grid, and open document detail panels inline — all without leaving the browse view. Every document shows its type, location, and relationships in context.

</domain>

<decisions>
## Implementation Decisions

### Browse Page Layout
- **D-01:** New `BrowsePage` at `/browse` with a three-panel layout: folder tree sidebar (left), document content grid (center), document detail panel (right, shown on selection).
- **D-02:** The folder tree sidebar is collapsible (toggle button). Tree nodes show folder name and document count badge. Expand/collapse with click on chevron.
- **D-03:** Default route (`/`) redirects to `/browse`. The existing `/folders` and `/documents` pages remain accessible but `/browse` is the primary entry point.

### Content Grid
- **D-04:** When a folder is selected, the content area shows documents filed in that folder using a grid/list view (reuse existing DocumentTable pattern).
- **D-05:** Documents in the grid show: title, document type badge, lifecycle state badge, last modified date.
- **D-06:** Clicking a document in the grid opens the detail panel on the right side without navigation — inline selection pattern.

### Detail Panel
- **D-07:** The detail panel shows all document context: metadata, type info, folder location breadcrumb, lifecycle state, relationships panel (from Phase 31), and version history.
- **D-08:** Reuse the existing `DocumentDetailPanel` component, extended with folder location display.

### Breadcrumb Navigation
- **D-09:** A breadcrumb bar above the content grid shows the full path: Cabinet > Folder > Subfolder. Each segment is clickable to navigate up.
- **D-10:** Reuse the existing folder path data from the `fetchFolder` API response which already returns `path` segments.

### Sidebar Navigation Update
- **D-11:** Add "Browse" as the first item in the sidebar navigation, with a FolderTree icon.
- **D-12:** Existing pages (Documents, Folders, Search) remain in the sidebar but Browse is the primary entry.

### Claude's Discretion
- Exact grid vs list toggle behavior
- Empty state when no folder is selected
- Animation for panel open/close
- Mobile/responsive breakpoints

</decisions>

<canonical_refs>
## Canonical References

### Existing Components to Reuse/Extend
- `frontend/src/pages/FoldersPage.tsx` — Existing folder tree + folder detail (pattern to draw from)
- `frontend/src/pages/DocumentsPage.tsx` — Document list with selection and detail panel
- `frontend/src/components/documents/DocumentDetailPanel.tsx` — Detail panel to reuse
- `frontend/src/components/documents/DocumentTable.tsx` — Table component
- `frontend/src/components/documents/RelationshipPanel.tsx` — Relationships display (Phase 31)
- `frontend/src/api/folders.ts` — Folder tree and folder documents API

### Backend
- `src/app/routers/folders.py` — Folder tree, folder documents endpoints
- `src/app/services/folder_service.py` — get_folder_documents with ACL filtering

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- FoldersPage already has a working folder tree component
- DocumentsPage has document selection + detail panel pattern
- DocumentDetailPanel already integrates type info, lifecycle badge, relationships
- fetchFolderTree, fetchFolderDocuments APIs exist and work with ACL

### Integration Points
- App.tsx routing — add /browse route, redirect / to /browse
- SidebarNav — add Browse entry as first item

</code_context>

<specifics>
## Specific Ideas

No specific requirements — autonomous mode used recommended defaults.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 32-document-first-navigation*
*Context gathered: 2026-04-14*
