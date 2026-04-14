---
phase: 29-folder-acl-inheritance
plan: "03"
subsystem: frontend
tags: [acl, permissions, folders, react, typescript]
dependency_graph:
  requires: [29-02]
  provides: [folder-permissions-ui, access-source-badge]
  affects: [FoldersPage, DocumentDetailPanel]
tech_stack:
  added: []
  patterns:
    - inline confirm-state pattern (no window.confirm) for destructive actions
    - useQuery with folderKeys.acl() factory for ACL data
    - useMutation with cache invalidation for ACL CRUD
key_files:
  created:
    - frontend/src/components/folders/FolderPermissionsTab.tsx
    - frontend/src/components/folders/AddPermissionDialog.tsx
    - frontend/src/components/documents/AccessSourceBadge.tsx
  modified:
    - frontend/src/api/folders.ts
    - frontend/src/api/users.ts
    - frontend/src/pages/FoldersPage.tsx
    - frontend/src/components/documents/DocumentDetailPanel.tsx
    - src/app/schemas/acl.py
    - src/app/routers/folders.py
    - src/app/services/acl_service.py
    - src/app/services/document_service.py
decisions:
  - Use listUsers() from api/users.ts instead of inline fetch in AddPermissionDialog for proper auth handling and DRY
  - Lowercase permission_level values (read/write/delete/admin) to match backend PermissionLevel enum
  - Inline confirm-state pattern (confirmDeleteId state) for ACL entry removal — no native browser dialogs
  - Rewrote check_permission to use priority-based approach (direct -> folder -> workflow -> open) instead of branching on existence of any direct ACL entries
  - Added principal_name to FolderACLEntryResponse with batch resolution helper
metrics:
  duration: "~45 min"
  completed: "2026-04-14"
  tasks: 3
  files: 11
requirements-completed: [FOLD-05]
---

# Phase 29 Plan 03: Folder ACL Frontend Summary

**One-liner:** Folder permissions UI with FolderPermissionsTab (ACL list/CRUD with inline confirm), AddPermissionDialog (user selector + permission level), and AccessSourceBadge (blue inherited badge on document detail), integrated into FoldersPage via Tabs and DocumentDetailPanel.

## What Was Built

Three new React components and two modified pages providing full frontend ACL management for the folder system:

1. **`FolderPermissionsTab`** — Permissions tab content with a loading skeleton, empty state (shield icon + "No permissions set"), and a list of ACL entries showing principal icon, truncated ID, type badge, permission badge, and a two-step inline confirm delete button.

2. **`AddPermissionDialog`** — Modal dialog with a User/Group toggle, principal selector (populated from `/api/v1/users` via `listUsers()`), and permission level dropdown (read/write/delete/admin). Validates that a principal is selected before enabling submit.

3. **`AccessSourceBadge`** — Compact blue badge showing "Inherited from [folder name]" with a FolderOpen icon. Renders only when `accessSource === "folder_inherited"` and a folder name is available.

4. **`folders.ts` extensions** — Added `FolderACLEntry` type, `folderKeys.acl()` query key, and `fetchFolderAcls`, `addFolderAcl`, `removeFolderAcl` API functions.

5. **`FoldersPage.tsx`** — Wrapped folder detail content in Tabs with "Details" (existing content preserved verbatim) and "Permissions" tabs. FolderBreadcrumb stays above the Tabs.

6. **`DocumentDetailPanel.tsx`** — Added `AccessSourceBadge` import and render in the badge row section alongside `LifecycleStateBadge` and `LockIndicator`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] AddPermissionDialog used inline fetch instead of proper API client**
- **Found during:** Post-implementation verification
- **Issue:** The plan showed an inline `fetch("/api/v1/users", ...)` in AddPermissionDialog, which duplicated auth header logic and bypassed the existing `listUsers()` function in `api/users.ts`
- **Fix:** Imported `listUsers` and `UserSummary` from `../../api/users` instead; added `usersLoading` state for "Loading users..." placeholder text
- **Files modified:** `frontend/src/components/folders/AddPermissionDialog.tsx`
- **Commit:** 4c8c1a4

**2. [Rule 1 - Bug] Permission level values were uppercase (READ/WRITE/DELETE/ADMIN) but backend enum uses lowercase**
- **Found during:** Integration testing
- **Issue:** The plan's AddPermissionDialog used uppercase `<SelectItem value="READ">` etc., but the backend `PermissionLevel` enum uses lowercase values (`read`, `write`, `delete`, `admin`), causing API validation errors
- **Fix:** Changed all permission level SelectItem values to lowercase
- **Files modified:** `frontend/src/components/folders/AddPermissionDialog.tsx`
- **Commit:** f37a240

## Verification Fixes

**3. [Critical] listUsers 401 redirect to login**
- **Found during:** Human verification
- **Issue:** GET /api/v1/users without trailing slash caused Starlette 307 redirect; Vite proxy with changeOrigin made it cross-origin, stripping Authorization header
- **Fix:** Added trailing slash to BASE URL in listUsers
- **Files modified:** `frontend/src/api/users.ts`
- **Commit:** c6d8638

**4. [Critical] Folder ACL inheritance completely broken for documents with direct ACL entries**
- **Found during:** Human verification (john.legal saw no documents despite folder read permission)
- **Issue:** check_permission branched on whether ANY direct ACL entries existed on the document. Since uploaded documents auto-create owner ADMIN ACL, folder inheritance was always skipped for other users.
- **Fix:** Rewrote check_permission to always check folder ACL as fallback after direct ACL check fails. Also fixed list_documents SQL query which had the same gating condition.
- **Files modified:** `src/app/services/acl_service.py`, `src/app/services/document_service.py`
- **Commit:** c6d8638

**5. Permissions tab showed truncated UUIDs instead of usernames**
- **Found during:** Human verification
- **Issue:** FolderACLEntryResponse only had principal_id, no resolved name
- **Fix:** Added principal_name to schema, _resolve_principal_names batch helper in router
- **Files modified:** `src/app/schemas/acl.py`, `src/app/routers/folders.py`, `frontend/src/api/folders.ts`, `frontend/src/components/folders/FolderPermissionsTab.tsx`
- **Commit:** c6d8638

## Self-Check: PASSED

Files created/modified:
- FOUND: frontend/src/components/folders/FolderPermissionsTab.tsx
- FOUND: frontend/src/components/folders/AddPermissionDialog.tsx
- FOUND: frontend/src/components/documents/AccessSourceBadge.tsx
- FOUND: frontend/src/api/folders.ts (modified with ACL functions + principal_name type)
- FOUND: frontend/src/api/users.ts (modified with trailing slash fix)
- FOUND: frontend/src/pages/FoldersPage.tsx (modified with Tabs)
- FOUND: frontend/src/components/documents/DocumentDetailPanel.tsx (modified with AccessSourceBadge)
- FOUND: src/app/schemas/acl.py (modified with principal_name field)
- FOUND: src/app/routers/folders.py (modified with _resolve_principal_names)
- FOUND: src/app/services/acl_service.py (modified with rewritten check_permission + get_access_source)
- FOUND: src/app/services/document_service.py (modified with fixed folder ACL condition)

Commits verified:
- ed039ec: feat(29-03): add folder ACL API client and permission UI components
- 1e7ecdc: feat(29-03): integrate FolderPermissionsTab and AccessSourceBadge into pages
- f37a240: fix(29-03): lowercase permission_level values to match PermissionLevel enum
- 4c8c1a4: fix(29-03): use proper API client in AddPermissionDialog to fix silent empty users bug
- c6d8638: fix(29-03): fix folder ACL inheritance bugs found during verification

TypeScript: passes clean (`npx tsc --noEmit` exits 0)
