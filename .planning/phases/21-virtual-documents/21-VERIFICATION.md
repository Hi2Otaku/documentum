---
phase: 21-virtual-documents
verified: 2026-04-06T00:00:00Z
status: gaps_found
score: 5/9 must-haves verified
re_verification: false
gaps:
  - truth: "User can add existing documents as children to a virtual document"
    status: failed
    reason: "Frontend addChild sends { child_document_id } but backend AddChildRequest expects { document_id }. POST /children returns 422 Unprocessable Entity at runtime."
    artifacts:
      - path: "frontend/src/api/virtualDocuments.ts"
        issue: "Line 124: body sends `child_document_id` but backend schema field is `document_id`"
    missing:
      - "Change `{ child_document_id: childDocumentId }` to `{ document_id: childDocumentId }` in addChild() call"

  - truth: "User can reorder children using move-up/move-down buttons"
    status: failed
    reason: "Frontend reorderChildren sends { child_ids } but backend ReorderChildrenRequest expects { document_ids }. PUT /children/reorder returns 422 at runtime."
    artifacts:
      - path: "frontend/src/api/virtualDocuments.ts"
        issue: "Line 145: body sends `child_ids` but backend schema field is `document_ids`"
    missing:
      - "Change `{ child_ids: childIds }` to `{ document_ids: childIds }` in reorderChildren() call"
      - "The frontend also passes VirtualDocumentChild.id values (join-table PKs); backend reorder expects document UUIDs. VirtualDocumentChildrenList must pass child.child_document_id (which is itself misnamed — backend returns `document_id`) instead of child.id"

  - truth: "User can remove children from a virtual document"
    status: failed
    reason: "Frontend removeChild sends DELETE to .../children/{child.id} (VirtualDocumentChild PK), but backend route /{vdoc_id}/children/{document_id} expects the child document's UUID. Wrong ID passed — will 404 or silently delete wrong child."
    artifacts:
      - path: "frontend/src/components/virtual-documents/VirtualDocumentChildrenList.tsx"
        issue: "Line 110: onRemove(child.id) passes join-table row PK"
      - path: "frontend/src/components/virtual-documents/VirtualDocumentDetailPanel.tsx"
        issue: "Line 48: removeChild(virtualDocumentId!, childId) passes that PK to the API"
    missing:
      - "Pass child.document_id (child document UUID) to removeChild, not child.id"
      - "Frontend type VirtualDocumentChildResponse must expose `document_id` (currently named `child_document_id`, which doesn't exist on backend response)"

  - truth: "User can trigger PDF merge and download the combined file"
    status: failed
    reason: "Frontend downloadMergedPdf calls POST /api/v1/virtual-documents/{id}/merge-pdf but backend endpoint is GET /virtual-documents/{id}/merge. URL and HTTP method both wrong — will 404."
    artifacts:
      - path: "frontend/src/api/virtualDocuments.ts"
        issue: "Lines 150-151: mergePdfUrl returns '.../merge-pdf' and line 156 uses POST; backend is GET .../merge"
    missing:
      - "Change mergePdfUrl to return `/api/v1/virtual-documents/${virtualDocId}/merge`"
      - "Change downloadMergedPdf fetch to use method: 'GET'"

  - truth: "User can view a virtual document and see its ordered children list"
    status: partial
    reason: "VirtualDocumentResponse frontend type declares `document_title` and `document_id` but backend returns `title` and `owner_id`. Children are rendered using `child_title`, `child_filename`, `order_index` which are absent from backend response (backend returns `document_title`, `document_filename`, `sort_order`). All child rows display 'Untitled' with no filename and sort order is broken (NaN comparison)."
    artifacts:
      - path: "frontend/src/api/virtualDocuments.ts"
        issue: "VirtualDocumentResponse interface: uses `document_id`, `document_title` instead of `id`/`title`; VirtualDocumentChildResponse uses `child_document_id`, `order_index`, `child_title`, `child_filename` instead of `document_id`, `sort_order`, `document_title`, `document_filename`"
      - path: "frontend/src/components/virtual-documents/VirtualDocumentChildrenList.tsx"
        issue: "Line 25: sorts by a.order_index (undefined) — children appear in arbitrary order"
      - path: "frontend/src/components/virtual-documents/VirtualDocumentDetailPanel.tsx"
        issue: "Line 112: renders vdoc.document_title (undefined) — shows 'Untitled Virtual Document' always"
      - path: "frontend/src/pages/DocumentsPage.tsx"
        issue: "Line 263: renders vdoc.document_title (undefined) — table Title column is always blank"
    missing:
      - "Align VirtualDocumentChildResponse interface fields to match backend: document_id, sort_order, document_title, document_filename"
      - "Align VirtualDocumentResponse interface fields: remove document_id/document_title, use title"
      - "Update all component field access to use corrected names"
human_verification:
  - test: "Confirm merged PDF content correctness"
    expected: "Downloaded PDF contains pages from all child PDF documents in the defined sort order"
    why_human: "Cannot verify PDF binary content or page ordering programmatically without running the full stack"
  - test: "Confirm AddChildDialog search/filter works in the browser"
    expected: "Typing in the search box filters the displayed documents list"
    why_human: "Requires browser rendering and React Query debounce behaviour"
---

# Phase 21: Virtual Documents Verification Report

**Phase Goal:** Users can compose compound documents from multiple children in a defined order and generate a merged PDF output
**Verified:** 2026-04-06
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can create a virtual document from the documents page | VERIFIED | CreateVirtualDocumentDialog wired in DocumentsPage; useMutation calls createVirtualDocument which POSTs to /api/v1/virtual-documents/ |
| 2 | User can view a virtual document and see its ordered children list | PARTIAL | Detail panel fetches via useQuery/fetchVirtualDocument; but rendered fields (document_title, child_title, order_index) are absent from backend response — children display as "Untitled", sort is broken |
| 3 | User can add existing documents as children to a virtual document | FAILED | addChild sends `{ child_document_id }` but backend expects `{ document_id }` — 422 at runtime |
| 4 | User can reorder children using move-up/move-down buttons | FAILED | reorderChildren sends `{ child_ids }` but backend expects `{ document_ids }` — 422 at runtime |
| 5 | User can remove children from a virtual document | FAILED | removeChild passes VirtualDocumentChild.id (join-table PK) but endpoint path param is the child document's UUID |
| 6 | User can trigger PDF merge and download the combined file | FAILED | Frontend calls POST .../merge-pdf; backend is GET .../merge — 404 at runtime |
| 7 | System detects and prevents circular references (VDOC-03) | VERIFIED | _detect_cycle() implemented in service; called in add_child() with 409 response on cycle; structural guard in place |
| 8 | Backend CRUD and child management API is complete | VERIFIED | All 9 endpoints exist, registered in main.py under /api/v1/virtual-documents, wired to service layer with real DB queries |
| 9 | Virtual document models are defined and registered | VERIFIED | VirtualDocument and VirtualDocumentChild models in virtual_document.py, registered in models/__init__.py and Alembic migrations path |

**Score:** 5/9 truths verified (4 failed, 1 partial — all failures are in frontend-backend contract)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/app/models/virtual_document.py` | VirtualDocument + VirtualDocumentChild SQLAlchemy models | VERIFIED | Both models with proper FKs, UniqueConstraints, relationships, cascade |
| `src/app/schemas/virtual_document.py` | Pydantic request/response schemas | VERIFIED | VirtualDocumentCreate, Update, AddChildRequest, ReorderChildrenRequest, response schemas |
| `src/app/services/virtual_document_service.py` | Service layer with CRUD, child management, cycle detection, PDF merge | VERIFIED | Full implementation; pypdf merge with MinIO download, sort_order compaction, cycle detection guard |
| `src/app/routers/virtual_documents.py` | FastAPI router with all endpoints | VERIFIED | 9 endpoints, all wired to service, router included in main.py |
| `frontend/src/api/virtualDocuments.ts` | API client for all virtual document endpoints | STUB | File exists and exports 8 functions, but 5 contain wrong payload field names or wrong endpoint path/method — will produce runtime API errors |
| `frontend/src/components/virtual-documents/CreateVirtualDocumentDialog.tsx` | Dialog for creating virtual documents | VERIFIED | Substantive form with useMutation, shadcn components, toast |
| `frontend/src/components/virtual-documents/VirtualDocumentChildrenList.tsx` | Children list with reorder/remove buttons | STUB | Renders but uses wrong field names (child_title, child_filename, order_index absent in response) — all rows show "Untitled", sort is NaN |
| `frontend/src/components/virtual-documents/AddChildDialog.tsx` | Dialog to search and add child documents | STUB | Wired but underlying addChild call will 422 due to wrong payload key |
| `frontend/src/components/virtual-documents/VirtualDocumentDetailPanel.tsx` | Detail panel with info, children, PDF button | STUB | Uses vdoc.document_title (undefined), passes child.id instead of document_id to removeChild |
| `frontend/src/pages/DocumentsPage.tsx` | Tabs integration for virtual documents | VERIFIED | Tabs, VirtualDocumentTable, CreateVirtualDocumentDialog, VirtualDocumentDetailPanel all integrated correctly at structural level |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/src/api/virtualDocuments.ts` | `GET /api/v1/virtual-documents/` | fetch in fetchVirtualDocuments | WIRED | Correct path and method |
| `frontend/src/api/virtualDocuments.ts` | `POST /api/v1/virtual-documents/` | fetch in createVirtualDocument | WIRED | Correct path and method |
| `frontend/src/api/virtualDocuments.ts` | `POST /api/v1/virtual-documents/{id}/children` | fetch in addChild | BROKEN | Payload sends `child_document_id`; backend expects `document_id` |
| `frontend/src/api/virtualDocuments.ts` | `DELETE /api/v1/virtual-documents/{id}/children/{doc_id}` | fetch in removeChild | BROKEN | Frontend passes join-table child PK; backend expects document UUID in path |
| `frontend/src/api/virtualDocuments.ts` | `PUT /api/v1/virtual-documents/{id}/children/reorder` | fetch in reorderChildren | BROKEN | Payload sends `child_ids`; backend expects `document_ids` |
| `frontend/src/api/virtualDocuments.ts` | `GET /api/v1/virtual-documents/{id}/merge` | fetch in downloadMergedPdf | BROKEN | Frontend calls POST .../merge-pdf; backend is GET .../merge |
| `VirtualDocumentDetailPanel.tsx` | `frontend/src/api/virtualDocuments.ts` | useQuery + useMutation | WIRED | Imports and calls fetchVirtualDocument, reorderChildren, removeChild, downloadMergedPdf |
| `DocumentsPage.tsx` | `CreateVirtualDocumentDialog.tsx` | button in virtual tab toolbar | WIRED | Renders CreateVirtualDocumentDialog in the Virtual Documents tab |
| `src/app/routers/virtual_documents.py` | `virtual_document_service.py` | service function calls | WIRED | All 9 router handlers delegate to service; no stubs |
| `virtual_document_service.generate_merged_pdf` | MinIO + pypdf | download_object + PdfWriter | WIRED | Downloads latest document version, merges pages; graceful 501 if pypdf not installed |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `VirtualDocumentDetailPanel.tsx` | `vdoc` | `fetchVirtualDocument()` via useQuery → GET /api/v1/virtual-documents/{id} | Yes — backend queries DB with selectinload | FLOWING (but field names mismatched) |
| `DocumentsPage.tsx` (VirtualDocumentTable) | `virtualDocuments` | `fetchVirtualDocuments()` via useQuery → GET /api/v1/virtual-documents/ | Yes — backend queries DB with pagination | HOLLOW_FIELD — `vdoc.document_title` rendered but field is `title` in response |
| `VirtualDocumentChildrenList.tsx` | `sorted` children array | `vdoc.children` from fetchVirtualDocument | Yes — backend returns real children | HOLLOW_FIELD — `child_title`, `child_filename`, `order_index` are all absent from response shape |
| `virtual_document_service.generate_merged_pdf` | `pdf_bytes` | `download_object()` from MinIO + pypdf merge | Yes — real MinIO download + pypdf merge | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend router registered | grep "virtual_documents.router" src/app/main.py | Found at line 91 | PASS |
| TypeScript compiles | npx tsc --noEmit (frontend) | Exit 0, no errors | PASS |
| addChild payload field | grep "child_document_id" frontend/src/api/virtualDocuments.ts | Line 124 sends wrong key | FAIL |
| reorderChildren payload field | grep "child_ids" frontend/src/api/virtualDocuments.ts | Line 145 sends wrong key | FAIL |
| Merge PDF endpoint path | grep "merge-pdf" frontend/src/api/virtualDocuments.ts | Line 150-151 wrong path | FAIL |
| Backend merge endpoint path | grep "merge" src/app/routers/virtual_documents.py | "/{vdoc_id}/merge" GET | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| VDOC-01 | 21-01, 21-02 | User can create a virtual document and add child documents in a specified order | PARTIAL | Backend: fully satisfied. Frontend: create works; add child fails at runtime (wrong payload field) |
| VDOC-02 | 21-01, 21-02 | User can reorder or remove children from a virtual document | PARTIAL | Backend: fully satisfied. Frontend: reorder/remove both broken (wrong payload and wrong path param) |
| VDOC-03 | 21-01 | System detects and prevents circular references | SATISFIED | _detect_cycle() in service layer; called on every addChild; no frontend interaction needed |
| VDOC-04 | 21-01, 21-02 | User can generate a merged PDF from a virtual document's children | PARTIAL | Backend: fully satisfied (GET /merge, pypdf). Frontend: calls wrong URL (POST .../merge-pdf) — 404 at runtime |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/api/virtualDocuments.ts` | 64-70 | VirtualDocumentChildResponse type declares fields not present in backend response: `virtual_document_id`, `child_document_id`, `order_index`, `child_title`, `child_filename` | Blocker | Every consumer of child data renders undefined values |
| `frontend/src/api/virtualDocuments.ts` | 72-80 | VirtualDocumentResponse type declares `document_id`, `document_title` not present in backend; missing `title`, `owner_id` | Blocker | Virtual document title always renders as fallback "Untitled" |
| `frontend/src/api/virtualDocuments.ts` | 124 | addChild sends `child_document_id` payload key | Blocker | Backend returns 422; children cannot be added |
| `frontend/src/api/virtualDocuments.ts` | 145 | reorderChildren sends `child_ids` payload key | Blocker | Backend returns 422; reorder always fails |
| `frontend/src/api/virtualDocuments.ts` | 150-156 | mergePdfUrl returns `.../merge-pdf`; downloadMergedPdf uses POST | Blocker | Backend returns 404; PDF download never works |
| `frontend/src/components/virtual-documents/VirtualDocumentChildrenList.tsx` | 110 | onRemove(child.id) passes join-table PK instead of document UUID | Blocker | Wrong document removed or 404 |

---

### Human Verification Required

#### 1. Merged PDF Content and Order

**Test:** After fixing the frontend contract issues, upload two multi-page PDFs, create a virtual document with both as children, set a defined order, and click "Generate Merged PDF".
**Expected:** Downloaded PDF contains pages from both documents concatenated in the correct child sort order.
**Why human:** Cannot verify binary PDF content or page order programmatically without running the full stack.

#### 2. AddChildDialog Search Behaviour

**Test:** Open the Add Document dialog, type a partial document title in the search box.
**Expected:** The results list updates to show only documents matching the search term.
**Why human:** Requires browser interaction and React Query live re-fetch on input.

---

### Gaps Summary

All four failed truths share a single root cause: **the frontend API client (`virtualDocuments.ts`) was written with type definitions and payload field names that do not match the backend schema**. This is a systematic contract mismatch across the whole virtual document API surface:

1. **Type misalignment (read path):** `VirtualDocumentChildResponse` in the frontend uses `child_document_id`, `order_index`, `child_title`, `child_filename` — the backend serialises `document_id`, `sort_order`, `document_title`, `document_filename`. Every component that reads child data renders incorrect or undefined values.

2. **Payload misalignment (write path):**
   - `addChild`: sends `child_document_id`, backend expects `document_id`
   - `reorderChildren`: sends `child_ids`, backend expects `document_ids`

3. **Wrong path parameter (remove):** `removeChild` passes `child.id` (join-table row PK) as the URL segment `{document_id}` which expects the child document's UUID.

4. **Wrong merge endpoint:** Frontend calls `POST .../merge-pdf`; backend is `GET .../merge`.

The backend (Plan 01) is fully verified and production-ready. The frontend (Plan 02) requires targeted fixes to `frontend/src/api/virtualDocuments.ts` (type definitions, payload fields, merge URL/method) and one component fix in `VirtualDocumentChildrenList.tsx` / `VirtualDocumentDetailPanel.tsx` to pass `document_id` instead of `id` to remove/reorder operations.

---

_Verified: 2026-04-06_
_Verifier: Claude (gsd-verifier)_
