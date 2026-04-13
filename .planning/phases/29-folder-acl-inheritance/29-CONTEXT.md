# Phase 29: Folder ACL Inheritance - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Folder-level permissions that propagate down to documents. A `folder_acl` table stores principal → folder permission grants; `check_permission` in `acl_service` is extended to walk ancestor folders via recursive CTE when a document has no direct ACL entries. Browsing endpoints filter document results by resolved ACL. Frontend adds a Permissions tab to the existing folder admin panel with user/group picker and shows an "inherited from folder" badge on document detail when access derives from folder ACL.

</domain>

<decisions>
## Implementation Decisions

### Inheritance Resolution Logic
- OR logic for multi-folder: if user has access via ANY folder's ACL chain, grant access (most permissive)
- Recursive CTE walks all ancestor folders — no depth limit
- Folder with no ACL entries → open access (backward compat: no entries = open, consistent with existing `check_permission` pattern)
- Document with direct ACL entries → folder ACL is skipped entirely; document-level ACL is authoritative (override, not merge)

### Folder ACL Model & Storage
- New `folder_acl` table (mirrors `document_acl` — clean separation, consistent pattern)
- Superuser bypass: superusers see everything regardless of folder ACL
- Folder ACL management requires ADMIN permission on the folder OR superuser status
- `get_folder_tree` always returns the full tree regardless of folder ACL — only document content is filtered (browsability preserved)

### Frontend Folder Permission Management
- Permissions tab/section inline within the existing folder admin panel (FolderTree page)
- Principal picker supports both users and groups (same pattern as document ACL UI)
- Document detail shows "Access inherited from folder: [name]" badge when access comes from folder ACL
- Documents the user can't access are silently omitted from folder browsing results (standard ECM behavior, no placeholder count)

### Claude's Discretion
- Exact SQL shape of the folder ACL inheritance join in `check_permission` (subquery vs EXISTS vs CTE)
- Whether to add a `folder_acl_service.py` or extend `acl_service.py`
- Alembic migration naming and column ordering
- Test fixture design for multi-folder and multi-ancestor scenarios

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DocumentACL` model in `src/app/models/acl.py` — exact template for `FolderACL` model
- `acl_service.check_permission()` — extend to add folder inheritance branch
- `acl_service.create_acl_entry()` / `remove_acl_entry()` / `get_document_acls()` — pattern for folder ACL CRUD
- `PERMISSION_HIERARCHY` dict and `has_sufficient_permission()` — reuse directly
- `_get_folder_path()` recursive CTE in `folder_service.py` — reference for ancestor CTE pattern
- `require_permission()` dependency factory in `dependencies.py` — existing access control integration point
- Folder admin page in frontend already has a detail/info panel — add Permissions tab there

### Established Patterns
- No ACL entries → open access (backward compat rule in `check_permission`)
- Group resolution via `user_groups` join table
- Soft-delete with `is_deleted == False` filter everywhere
- `created_by` string field on all models
- `selectinload` for relationship loading in async context
- `BaseModel` from `app.models.base` provides `id`, `created_at`, `updated_at`, `is_deleted`, `created_by`

### Integration Points
- `acl_service.check_permission()` — core integration: add folder inheritance after document-level check fails
- `folder_service.get_folder_documents()` — filter documents by resolved permission during browsing
- Document detail API response — add `access_source` field ("direct", "folder_inherited", "open") when folder ACL is active
- Folders router — add `/folders/{folder_id}/acl` CRUD endpoints
- Frontend: `FolderTree` admin component — add Permissions tab with ACL list + picker

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the decisions above — open to standard approaches for the ACL CRUD router shape and test fixture design.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
