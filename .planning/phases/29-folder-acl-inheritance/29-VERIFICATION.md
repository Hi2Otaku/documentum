---
phase: 29-folder-acl-inheritance
verified: 2026-04-14T12:00:00Z
status: passed
score: 3/3 must-haves verified
gaps: []
human_verification:
  - test: "Visual verification of folder permissions tab and access source badge"
    expected: "Permissions tab shows ACL entries with add/remove, AccessSourceBadge shows 'Inherited from [folder]' on document detail"
    why_human: "UI rendering, visual layout, and interactive flow (inline confirm) cannot be verified programmatically"
---

# Phase 29: Folder ACL Inheritance Verification Report

**Phase Goal:** Folder-level permissions flow down to documents, so users only see documents they are authorized to access when browsing
**Verified:** 2026-04-14T12:00:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths (from Success Criteria)

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | User with read permission on a folder can see all documents filed in that folder (and its subfolders) without per-document ACL entries | VERIFIED | `check_permission()` in acl_service.py (lines 229-265) walks ancestor folders via `_get_ancestor_folder_ids()` CTE and checks FolderACL entries for user/group. `get_folder_documents()` in folder_service.py filters via per-document `check_permission()`. `list_documents()` in document_service.py uses descendant CTE subqueries for folder ACL doc IDs. Tests: `test_folder_read_grants_document_access`, `test_nested_folder_inheritance`, `test_get_folder_documents_acl_filtered`. |
| 2   | User without folder permission cannot see documents that rely solely on inherited folder ACL for access | VERIFIED | `check_permission()` returns False when user has no direct ACL, no matching folder ACL, and no workflow participant access, AND ACL entries exist (lines 286-311). Tests: `test_no_folder_permission_hides_documents`, `test_get_folder_documents_acl_filtered` (regular user sees 0 docs). |
| 3   | Direct document-level ACL entries override inherited folder permissions when both exist | VERIFIED | `check_permission()` checks direct document ACL first (lines 198-227), then folder ACL as fallback (lines 229-265). Priority order is clearly documented. Test: `test_direct_acl_overrides_folder_acl`. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/app/models/acl.py` | FolderACL model | VERIFIED | FolderACL class with folder_id FK, principal_id, principal_type, permission_level, unique constraint (lines 31-49) |
| `src/app/services/acl_service.py` | Folder ACL inheritance logic | VERIFIED | `_get_ancestor_folder_ids()` CTE helper, `check_permission()` with 4-priority fallback, `get_access_source()`, `check_folder_permission()`, folder ACL CRUD (575 lines, fully substantive) |
| `src/app/routers/folders.py` | Folder ACL CRUD endpoints | VERIFIED | GET/POST/DELETE /{folder_id}/acl with ADMIN permission gating, `_resolve_principal_names` batch helper, ACL-filtered `get_folder_documents` (lines 273-351) |
| `src/app/schemas/acl.py` | FolderACL schemas | VERIFIED | `FolderACLEntryCreate` and `FolderACLEntryResponse` with principal_name field (lines 33-49) |
| `src/app/schemas/document.py` | access_source field on DocumentResponse | VERIFIED | `access_source: str | None = None` and `access_source_folder_name: str | None = None` (lines 40-41) |
| `src/app/routers/documents.py` | access_source in document detail | VERIFIED | Imports `get_access_source`, calls it, uses `model_copy(update=access_info)` (lines 113-120) |
| `src/app/services/document_service.py` | list_documents with folder ACL filtering | VERIFIED | FolderACL subqueries with descendant CTE, OR logic for direct ACL / folder ACL / open access (lines 215-279) |
| `src/app/services/folder_service.py` | get_folder_documents with ACL filtering | VERIFIED | user_id and is_superuser params, per-document check_permission filtering (lines 461-495) |
| `frontend/src/components/folders/FolderPermissionsTab.tsx` | Permissions tab component | VERIFIED | useQuery for ACL list, useMutation for remove, inline confirm-state pattern, empty state with shield icon, loading skeleton |
| `frontend/src/components/folders/AddPermissionDialog.tsx` | Add permission dialog | VERIFIED | User/Group toggle, principal selector from /api/v1/users, permission level dropdown, mutation with cache invalidation |
| `frontend/src/components/documents/AccessSourceBadge.tsx` | Inherited access badge | VERIFIED | Renders "Inherited from [folderName]" with blue styling when accessSource === "folder_inherited" |
| `frontend/src/api/folders.ts` | API client extensions | VERIFIED | FolderACLEntry type, folderKeys.acl(), fetchFolderAcls, addFolderAcl, removeFolderAcl functions |
| `frontend/src/pages/FoldersPage.tsx` | Tabs integration | VERIFIED | Tabs with Details and Permissions tabs, FolderPermissionsTab rendered in permissions TabsContent |
| `frontend/src/components/documents/DocumentDetailPanel.tsx` | AccessSourceBadge integration | VERIFIED | Import + render with accessSource and folderName props |
| `tests/test_folder_acl.py` | Comprehensive test suite | VERIFIED | 15 test functions covering service-level and API-level scenarios |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| folders.py router | acl_service.py | create_folder_acl_entry, get_folder_acls, remove_folder_acl_entry | WIRED | Import at line 31, called in all three ACL endpoints |
| folders.py router | acl schemas | FolderACLEntryCreate, FolderACLEntryResponse | WIRED | Import at line 20, used as request/response models |
| acl_service.py | _get_ancestor_folder_ids | Used by check_permission and get_access_source | WIRED | Called at lines 238 and 492 |
| documents.py router | acl_service.get_access_source | Import and call in get_document | WIRED | Lines 113-119 |
| FoldersPage.tsx | FolderPermissionsTab | Import and TabsContent render | WIRED | Import line 14, rendered line 247 |
| FolderPermissionsTab | folders.ts API | fetchFolderAcls, removeFolderAcl | WIRED | Imported line 7, used in useQuery/useMutation |
| DocumentDetailPanel | AccessSourceBadge | Import and conditional render | WIRED | Import line 11, rendered lines 129-132 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| FolderPermissionsTab | acls | fetchFolderAcls -> GET /folders/{id}/acl -> acl_service.get_folder_acls -> FolderACL DB query | Yes - queries folder_acl table | FLOWING |
| AccessSourceBadge | accessSource, folderName | document.access_source from GET /documents/{id} -> get_access_source -> recursive CTE + FolderACL queries | Yes - queries DocumentACL, FolderACL, Folder tables | FLOWING |
| get_folder_documents | filtered documents | folder_service -> check_permission per doc -> DB queries for DocumentACL, FolderACL | Yes - real permission checks | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED (requires running server with PostgreSQL, Redis, MinIO -- cannot test without external services)

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| FOLD-05 | 29-01, 29-02, 29-03 | Permissions assigned to a folder are inherited by all documents within it (folder-level ACL propagation) | SATISFIED | FolderACL model, recursive CTE ancestor walk in check_permission, ACL-filtered document listing, folder ACL CRUD endpoints, frontend permissions UI, access source badge. 15 tests covering all sub-requirements. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none found) | - | - | - | - |

No TODOs, FIXMEs, placeholders, empty implementations, or window.confirm() calls found in phase 29 files.

### Human Verification Required

### 1. Folder Permissions Tab UI

**Test:** Navigate to Folders page, select a folder, click Permissions tab. Verify empty state (shield icon, "No permissions set"), add a permission via dialog, verify entry appears with principal name/type/permission badges, click X to remove (should show inline "Confirm?" button, NOT native browser dialog), click Confirm to remove.
**Expected:** Full CRUD cycle works through the UI with inline confirmation pattern.
**Why human:** Visual rendering, interactive flow, and UX quality cannot be verified programmatically.

### 2. Access Source Badge on Document Detail

**Test:** File a document in a folder that has ACL entries, then view that document's detail panel as a user who gains access via folder ACL.
**Expected:** Blue badge reading "Inherited from [folder name]" appears alongside lifecycle and lock indicators.
**Why human:** Badge rendering, color, and positioning require visual verification.

### 3. ACL-Filtered Folder Browsing

**Test:** As a user without folder permission, browse a folder that has ACL entries restricting access. Verify documents are silently omitted (no error, no count of hidden documents).
**Expected:** User sees an empty or reduced document list without error messages.
**Why human:** End-to-end flow through UI with multiple user sessions requires manual testing.

### Gaps Summary

No gaps found. All three success criteria are verified through code inspection:

1. **Folder read grants document access** -- check_permission walks ancestor folders via recursive CTE and checks FolderACL entries. Both get_folder_documents (N+1 filter) and list_documents (subquery CTE) implement this.

2. **No folder permission hides documents** -- When FolderACL entries exist on ancestor folders but none match the user, check_permission returns False (the "open access" fallback only triggers when NO ACL entries exist anywhere).

3. **Direct document ACL overrides folder ACL** -- check_permission uses a priority-based approach: direct document ACL is checked first, folder ACL is the fallback. This was rewritten during plan 03 to fix a critical bug where the original branching logic prevented folder ACL from being checked when any direct ACL existed on the document (even for other users).

---

_Verified: 2026-04-14T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
