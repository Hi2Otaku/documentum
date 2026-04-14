# Phase 33: Saved Searches & Smart Folders - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — recommended defaults selected)

<domain>
## Phase Boundary

This phase delivers saved search persistence and smart folder integration. Users can save a search query with a name for later reuse, and optionally mark a saved search to appear as a virtual "smart folder" node in the folder tree. Clicking a smart folder executes the saved search and displays results as if browsing a regular folder.

</domain>

<decisions>
## Implementation Decisions

### Saved Search Model
- **D-01:** Create a `SavedSearch` model with: name, query (search text), filters (JSONB — stores folder_id, document_type_id, lifecycle_state), is_smart_folder (boolean), user_id (owner), display_order (for tree positioning).
- **D-02:** Saved searches are per-user — each user has their own saved searches.
- **D-03:** Filters stored as JSONB so the filter combination is flexible and extensible.

### API Design
- **D-04:** REST endpoints at `/api/v1/saved-searches` — GET (list user's searches), POST (create), PUT (update), DELETE (remove).
- **D-05:** No special endpoint for smart folders — the folder tree API is extended to include smart folder nodes alongside real folders when `is_smart_folder=true`.
- **D-06:** When a smart folder is "browsed", the frontend calls the existing search API with the saved query + filters rather than the folder documents endpoint.

### Frontend
- **D-07:** "Save Search" button on the SearchPage that opens a dialog to name the search and optionally mark it as a smart folder.
- **D-08:** "Saved Searches" section in the search page showing previously saved searches with load/delete actions.
- **D-09:** Smart folder nodes appear in the BrowsePage folder tree sidebar below the real folders, visually distinguished with a different icon (e.g., SearchIcon or SparklesIcon).
- **D-10:** Clicking a smart folder node shows search results in the content grid using the same layout as regular folder browsing.

### Claude's Discretion
- Smart folder icon choice
- Ordering of smart folders in the tree
- Whether to show a "smart folder" badge in the content area header

</decisions>

<canonical_refs>
## Canonical References

### Search Infrastructure (Phase 30)
- `src/app/routers/search.py` — Search API endpoint to call from smart folders
- `src/app/services/search_service.py` — Search service
- `frontend/src/api/search.ts` — Search API client
- `frontend/src/pages/SearchPage.tsx` — Search page to add save button to

### Browse/Tree (Phase 32)
- `frontend/src/pages/BrowsePage.tsx` — Where smart folder nodes integrate
- `frontend/src/api/folders.ts` — Folder tree API to extend with smart folder nodes

### Models
- `src/app/models/base.py` — BaseModel pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Search API already supports query + filters — smart folders just replay saved params
- BrowsePage folder tree already renders folder nodes — extend with smart folder type
- SearchPage filter sidebar can populate saved search form

### Integration Points
- SearchPage — add save button and saved searches list
- BrowsePage folder tree — inject smart folder nodes
- App.tsx — no new routes needed (smart folders use existing browse + search)

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

*Phase: 33-saved-searches-smart-folders*
*Context gathered: 2026-04-14*
