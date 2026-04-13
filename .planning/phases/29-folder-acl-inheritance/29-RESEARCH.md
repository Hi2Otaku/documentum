# Phase 29: Folder ACL Inheritance - Research

**Researched:** 2026-04-13
**Domain:** ACL inheritance, recursive CTE permission resolution, folder-scoped access control
**Confidence:** HIGH

## Summary

Phase 29 adds folder-level ACL that propagates to documents filed within folders. The existing codebase already has a complete document ACL system (`DocumentACL` model, `acl_service.check_permission()`, CRUD endpoints in `lifecycle.py` router) and a folder hierarchy with recursive CTE utilities (`folder_service._get_folder_path()`, `_is_descendant()`). This phase mirrors the document ACL pattern for folders, extends `check_permission()` with a folder inheritance branch, filters document listings by resolved permissions, and adds frontend UI for managing folder ACLs.

The core technical challenge is extending `check_permission()` and `list_documents()` to walk ancestor folder ACLs via recursive CTE when a document has no direct ACL entries. The existing CTE patterns in `folder_service.py` provide exact templates. The `get_folder_documents()` endpoint also needs ACL filtering. All decisions are locked in CONTEXT.md; no alternative exploration is needed.

**Primary recommendation:** Mirror `DocumentACL` for `FolderACL` model, extend `acl_service.check_permission()` with a folder inheritance branch using a recursive CTE, and add folder ACL CRUD endpoints following the exact pattern from `lifecycle.py` router's document ACL endpoints.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- OR logic for multi-folder: if user has access via ANY folder's ACL chain, grant access (most permissive)
- Recursive CTE walks all ancestor folders -- no depth limit
- Folder with no ACL entries = open access (backward compat: no entries = open, consistent with existing check_permission pattern)
- Document with direct ACL entries = folder ACL is skipped entirely; document-level ACL is authoritative (override, not merge)
- New folder_acl table (mirrors document_acl -- clean separation, consistent pattern)
- Superuser bypass: superusers see everything regardless of folder ACL
- Folder ACL management requires ADMIN permission on the folder OR superuser status
- get_folder_tree always returns the full tree regardless of folder ACL -- only document content is filtered (browsability preserved)
- Permissions tab/section inline within the existing folder admin panel (FolderTree page)
- Principal picker supports both users and groups (same pattern as document ACL UI)
- Document detail shows "Access inherited from folder: [name]" badge when access comes from folder ACL
- Documents the user can't access are silently omitted from folder browsing results (standard ECM behavior, no placeholder count)

### Claude's Discretion
- Exact SQL shape of the folder ACL inheritance join in check_permission (subquery vs EXISTS vs CTE)
- Whether to add a folder_acl_service.py or extend acl_service.py
- Alembic migration naming and column ordering
- Test fixture design for multi-folder and multi-ancestor scenarios

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOLD-05 | Permissions assigned to a folder are inherited by all documents within it (folder-level ACL propagation) | FolderACL model mirrors DocumentACL; check_permission extended with recursive CTE ancestor walk; list_documents and get_folder_documents filter by resolved ACL; folder ACL CRUD endpoints; frontend permissions tab + access source badge |
</phase_requirements>

## Architecture Patterns

### Recommended Project Structure (new/modified files)

```
src/app/
  models/
    acl.py              # ADD FolderACL class (mirrors DocumentACL)
  services/
    acl_service.py      # EXTEND check_permission() with folder inheritance
                        # ADD folder ACL CRUD functions
    folder_service.py   # MODIFY get_folder_documents() to accept user_id/is_superuser for filtering
    document_service.py # MODIFY list_documents() to include folder ACL branch
  schemas/
    acl.py              # ADD FolderACLEntryCreate, FolderACLEntryResponse
  routers/
    folders.py          # ADD /folders/{id}/acl CRUD endpoints
  
alembic/versions/
    xxxx_add_folder_acl.py  # New migration

frontend/src/
  api/
    folders.ts          # ADD fetchFolderAcls, addFolderAcl, removeFolderAcl
  components/
    folders/
      FolderPermissionsTab.tsx   # NEW
      AddPermissionDialog.tsx    # NEW
    documents/
      AccessSourceBadge.tsx      # NEW
  pages/
    FoldersPage.tsx     # MODIFY: add Tabs with Details + Permissions
```

### Pattern 1: FolderACL Model (mirror DocumentACL)

**What:** New SQLAlchemy model `FolderACL` in `acl.py` with identical structure to `DocumentACL` but referencing `folders.id` instead of `documents.id`.

**When to use:** This is the only model pattern for this phase.

**Example:**
```python
# Source: existing DocumentACL pattern in src/app/models/acl.py
class FolderACL(BaseModel):
    __tablename__ = "folder_acl"
    __table_args__ = (
        UniqueConstraint(
            "folder_id", "principal_id", "principal_type", "permission_level",
            name="uq_folder_acl_entry",
        ),
    )

    folder_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("folders.id"), nullable=False, index=True
    )
    principal_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    permission_level: Mapped[str] = mapped_column(
        Enum(PermissionLevel, name="permissionlevel"), nullable=False
    )

    folder = relationship("Folder")
```

### Pattern 2: Recursive CTE for Ancestor Folder ACL Resolution

**What:** Walk from a document's folder(s) up through all ancestor folders to find matching ACL entries. Uses the same CTE pattern as `_get_folder_path()` in `folder_service.py`.

**When to use:** Inside `check_permission()` when document has no direct ACL entries and user is not superuser.

**Recommendation:** Use a single recursive CTE that walks ancestors of all folders a document is filed in, then check FolderACL entries against that set. This avoids N+1 queries for multi-filed documents.

**Example (pseudocode for the CTE):**
```python
# 1. Get all folder_ids the document is filed in
# 2. Recursive CTE: anchor = those folder_ids, recursive = parent_id walk
# 3. Check FolderACL entries where folder_id IN (CTE result set)
#    AND (principal_id = user_id AND principal_type = 'user')
#    OR (principal_id IN user_group_ids AND principal_type = 'group')
# 4. If ANY matching entry has sufficient permission level, return True

# Key: "no FolderACL entries on any ancestor" = open access (backward compat)
# This means: if the CTE finds ancestors but NONE have ANY FolderACL entries,
# the folder chain is "open"
```

### Pattern 3: Document Listing ACL Filter Extension

**What:** Extend the `list_documents()` ACL filter in `document_service.py` to include folder ACL as an additional OR branch.

**Current logic (simplified):**
```
visible = doc_has_direct_acl_for_user 
        OR doc_has_no_acl_entries 
        OR doc_has_active_work_item_for_user
```

**New logic:**
```
visible = doc_has_direct_acl_for_user
        OR (doc_has_no_direct_acl AND folder_chain_grants_access)
        OR (doc_has_no_direct_acl AND folder_chain_has_no_acl_entries)
        OR doc_has_active_work_item_for_user
```

**Critical detail:** The "no ACL entries = open access" rule must be evaluated per-document for direct ACLs AND per-folder-chain for folder ACLs. A document with no direct ACL AND whose folders have no folder ACLs = open access. A document with no direct ACL but whose folder has ACL entries = folder ACL governs.

### Pattern 4: Access Source Field on Document Response

**What:** Add `access_source` field to document detail response to indicate how access was granted.

**Values:** `"direct"` | `"folder_inherited"` | `"open"`

**When:** Only computed for authenticated single-document fetches (GET /documents/{id}). Not needed for list endpoints (those just filter silently).

**Implementation:** After `check_permission()` succeeds, call a lightweight helper to determine access source:
1. If document has direct ACL entries for user -> "direct"
2. If document has no direct ACL entries but folder ACL grants access -> "folder_inherited" (also return the folder name)
3. If no ACL entries at all -> "open"

### Anti-Patterns to Avoid
- **Merging document + folder ACLs:** Decision is override, not merge. If document has direct ACL entries, folder ACL is completely ignored.
- **Filtering the folder tree by ACL:** Decision says full tree is always visible. Only document content within folders is filtered.
- **Showing "access denied" placeholders:** Decision says silently omit inaccessible documents from listings.
- **Depth-limited CTE:** Decision says no depth limit on ancestor walk.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Recursive ancestor walk | Manual parent-chasing loop in Python | SQLAlchemy recursive CTE (existing pattern in `_get_folder_path`) | Single SQL query vs. N+1; CTE pattern already proven in codebase |
| Permission hierarchy comparison | Manual if/elif chains | Existing `PERMISSION_HIERARCHY` dict + `has_sufficient_permission()` | Already handles READ < WRITE < DELETE < ADMIN ordering |
| Group membership resolution | Custom group lookup | Existing `user_groups` join table pattern from `check_permission()` | Already handles group-based ACL in document ACL |

## Common Pitfalls

### Pitfall 1: "No ACL = open" ambiguity in folder chains
**What goes wrong:** Misinterpreting the backward compatibility rule when folders and documents interact. A document filed in a folder with ACL entries should be restricted by folder ACL. But a document filed in a folder with NO ACL entries should remain open.
**Why it happens:** The "no ACL = open" rule applies at TWO levels: document-level and folder-level. Both must be checked independently.
**How to avoid:** In `check_permission()`, after determining document has no direct ACL: (1) find all ancestor folders, (2) check if ANY of those folders have ANY FolderACL entries, (3) if none have entries -> open access, (4) if some have entries -> check if user has permission via those entries.
**Warning signs:** Tests pass for documents not filed in any folder but fail for documents in folders with ACLs.

### Pitfall 2: Multi-filing OR logic
**What goes wrong:** A document filed in folders A and B. Folder A restricts access. Folder B grants access. User should be able to see the document (OR logic), but implementation checks only one folder.
**Why it happens:** Not aggregating across all document_folders rows.
**How to avoid:** The CTE anchor must include ALL folder_ids from the document_folders table for the given document, and the ACL check must use ANY/EXISTS semantics across the full ancestor set.
**Warning signs:** Document visible when filed in accessible folder alone, but invisible when also filed in restricted folder.

### Pitfall 3: SQLite vs PostgreSQL CTE differences in tests
**What goes wrong:** Tests use `sqlite+aiosqlite:///:memory:` (per conftest.py). SQLite supports recursive CTEs but has subtle differences from PostgreSQL (e.g., no `LATERAL`, limited type casting).
**Why it happens:** Test DB differs from production DB.
**How to avoid:** Use standard SQL in CTEs. Avoid PostgreSQL-specific syntax in the CTE itself. The existing `_get_folder_path()` CTE works in both SQLite and PostgreSQL, so follow its exact pattern.
**Warning signs:** Tests pass but production queries fail, or vice versa.

### Pitfall 4: N+1 on access_source resolution
**What goes wrong:** Computing `access_source` for every document in a list endpoint causes N additional queries.
**Why it happens:** Calling `check_permission()` or access source helper per document.
**How to avoid:** Only compute `access_source` on single-document detail endpoint (GET /documents/{id}), not on list endpoints. List endpoints just filter silently.
**Warning signs:** Slow document list page loads.

### Pitfall 5: Enum reuse in new table
**What goes wrong:** Creating a new `permissionlevel` enum type in the migration when one already exists.
**Why it happens:** Alembic auto-generates `sa.Enum(PermissionLevel, name='permissionlevel', create_type=False)` vs `create_type=True`.
**How to avoid:** In the Alembic migration, use `create_type=False` for the `permission_level` column in `folder_acl` since the `permissionlevel` PostgreSQL enum already exists from `document_acl`. In SQLite tests this is not an issue.
**Warning signs:** Migration fails with "type already exists" error on PostgreSQL.

### Pitfall 6: Superuser bypass must be checked early
**What goes wrong:** Superuser still goes through the full CTE ancestor walk, causing unnecessary query overhead.
**Why it happens:** Superuser check buried deep in the permission chain.
**How to avoid:** Check `is_superuser` at the very top of `check_permission()` and return True immediately. Already partially done in `list_documents()` but not in `check_permission()` itself (currently `check_permission` doesn't receive `is_superuser`).
**Warning signs:** Superuser document detail requests slower than expected.

## Code Examples

### FolderACL CRUD Service Functions (extend acl_service.py)

```python
# Source: mirrored from existing create_acl_entry / remove_acl_entry / get_document_acls
# Recommendation: Add these to acl_service.py rather than a new file,
# since they share PERMISSION_HIERARCHY, has_sufficient_permission, and audit patterns.

async def create_folder_acl_entry(
    db: AsyncSession,
    folder_id: uuid.UUID,
    principal_id: uuid.UUID,
    principal_type: str,
    permission_level: PermissionLevel,
    user_id: str | None = None,
) -> FolderACL:
    """Create a folder ACL entry (mirrors create_acl_entry pattern)."""
    # Check for existing duplicate
    # Create entry
    # Audit record with entity_type="folder_acl"
    ...

async def get_folder_acls(
    db: AsyncSession, folder_id: uuid.UUID,
) -> list[FolderACL]:
    """Return all non-deleted ACL entries for a folder."""
    ...

async def check_folder_permission(
    db: AsyncSession,
    folder_id: uuid.UUID,
    user_id: uuid.UUID,
    required_level: PermissionLevel,
) -> bool:
    """Check if user has sufficient permission on a folder (for ACL management)."""
    # Used to gate /folders/{id}/acl endpoints
    # Similar to check_permission but checks FolderACL directly
    ...
```

### Extended check_permission with Folder Inheritance

```python
async def check_permission(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    required_level: PermissionLevel,
) -> bool:
    # ... existing document-level ACL checks ...
    
    # If document has direct ACL entries but user not authorized -> return False
    # (document-level ACL is authoritative when present)
    if total_entries > 0:
        # ... existing user/group/workflow checks ...
        return False  # (if none matched)
    
    # No direct ACL entries -> check folder ACL inheritance
    # Step 1: Get all folders this document is filed in
    from app.models.folder import document_folders, Folder
    folder_result = await db.execute(
        select(document_folders.c.folder_id).where(
            document_folders.c.document_id == document_id
        )
    )
    folder_ids = [row[0] for row in folder_result.all()]
    
    if not folder_ids:
        return True  # Not filed in any folder, no ACL -> open access
    
    # Step 2: Recursive CTE to get all ancestor folder IDs
    folder_table = Folder.__table__
    anchor = (
        select(folder_table.c.id)
        .where(
            folder_table.c.id.in_(folder_ids),
            folder_table.c.is_deleted == False,
        )
        .cte(name="folder_ancestors", recursive=True)
    )
    anc_alias = anchor.alias("anc")
    recursive = select(folder_table.c.id).join(
        anc_alias, folder_table.c.id == folder_table.c.parent_id  # walk up
    )
    # ... build full ancestor set ...
    
    # Step 3: Check if ANY FolderACL entries exist on any ancestor
    # If none -> open access (backward compat)
    # If some -> check user/group access
    ...
```

### Folder ACL Router Endpoints

```python
# Source: mirrors lifecycle.py document ACL endpoints pattern
# Add to folders.py router

@router.get("/{folder_id}/acl", response_model=EnvelopeResponse[list[FolderACLEntryResponse]])
async def list_folder_acl(folder_id: uuid.UUID, db, current_user):
    """List folder ACL entries. Requires ADMIN on folder or superuser."""
    ...

@router.post("/{folder_id}/acl", response_model=EnvelopeResponse[FolderACLEntryResponse], status_code=201)
async def add_folder_acl(folder_id: uuid.UUID, request: FolderACLEntryCreate, db, current_user):
    """Add folder ACL entry. Requires ADMIN on folder or superuser."""
    ...

@router.delete("/{folder_id}/acl/{acl_id}", response_model=EnvelopeResponse)
async def remove_folder_acl(folder_id: uuid.UUID, acl_id: uuid.UUID, db, current_user):
    """Remove folder ACL entry. Requires ADMIN on folder or superuser."""
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Document-only ACL | Document ACL + Folder ACL inheritance | This phase | Documents in folders inherit folder permissions; no per-document ACL needed for folder-scoped access |
| No folder permissions | Folder-level RBAC with CTE ancestor walk | This phase | Permissions cascade through folder hierarchy automatically |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `tests/conftest.py` (session-scoped fixtures, aiosqlite in-memory DB) |
| Quick run command | `python -m pytest tests/test_folder_acl.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOLD-05a | User with folder READ can see documents in that folder | integration | `pytest tests/test_folder_acl.py::test_folder_read_grants_document_access -x` | No - Wave 0 |
| FOLD-05b | User without folder permission cannot see folder-only-ACL documents | integration | `pytest tests/test_folder_acl.py::test_no_folder_permission_hides_documents -x` | No - Wave 0 |
| FOLD-05c | Direct document ACL overrides folder ACL entirely | integration | `pytest tests/test_folder_acl.py::test_direct_acl_overrides_folder_acl -x` | No - Wave 0 |
| FOLD-05d | Folder with no ACL entries = open access (backward compat) | integration | `pytest tests/test_folder_acl.py::test_no_folder_acl_means_open_access -x` | No - Wave 0 |
| FOLD-05e | Multi-folder OR logic (access via any folder grants access) | integration | `pytest tests/test_folder_acl.py::test_multi_folder_or_logic -x` | No - Wave 0 |
| FOLD-05f | Superuser bypass for folder ACL | integration | `pytest tests/test_folder_acl.py::test_superuser_bypasses_folder_acl -x` | No - Wave 0 |
| FOLD-05g | Folder ACL CRUD endpoints (add, list, remove) | integration | `pytest tests/test_folder_acl.py::test_folder_acl_crud -x` | No - Wave 0 |
| FOLD-05h | Nested folder inheritance (grandchild inherits from grandparent) | integration | `pytest tests/test_folder_acl.py::test_nested_folder_inheritance -x` | No - Wave 0 |
| FOLD-05i | Group-based folder ACL | integration | `pytest tests/test_folder_acl.py::test_group_folder_acl -x` | No - Wave 0 |
| FOLD-05j | access_source field on document detail response | integration | `pytest tests/test_folder_acl.py::test_access_source_field -x` | No - Wave 0 |
| FOLD-05k | Folder documents endpoint filters by ACL | integration | `pytest tests/test_folder_acl.py::test_folder_documents_filtered_by_acl -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_folder_acl.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_folder_acl.py` -- covers all FOLD-05 sub-requirements
- [ ] No framework install needed (pytest + pytest-asyncio already configured)
- [ ] No conftest changes needed (existing fixtures provide admin_user, regular_user, db_session, async_client)

## Open Questions

1. **Superuser parameter for check_permission()**
   - What we know: `check_permission()` currently doesn't accept `is_superuser`; superuser bypass is only in `list_documents()` and `require_permission()` dependency.
   - What's unclear: Whether to add `is_superuser` parameter to `check_permission()` for early bypass, or keep the bypass at the caller level.
   - Recommendation: Add superuser bypass inside `check_permission()` to centralize the logic. This requires passing the `User` object or `is_superuser` bool. The caller (`require_permission()` dependency) already has `current_user` available.

2. **Document count accuracy in folder tree after ACL filtering**
   - What we know: `get_folder_tree()` includes `document_count` per folder. After ACL filtering, the count shown may not match what the user can actually see.
   - What's unclear: Whether to show total count (including inaccessible) or filtered count.
   - Recommendation: Keep showing total count in tree (consistent with "full tree always visible" decision). The mismatch is acceptable -- users see fewer documents than the count suggests, which is standard ECM behavior.

## Sources

### Primary (HIGH confidence)
- `src/app/models/acl.py` -- DocumentACL model (exact template for FolderACL)
- `src/app/services/acl_service.py` -- check_permission(), create_acl_entry() patterns
- `src/app/services/folder_service.py` -- recursive CTE patterns (_get_folder_path, _is_descendant)
- `src/app/routers/lifecycle.py` lines 69-140 -- document ACL CRUD endpoint pattern
- `src/app/services/document_service.py` lines 143-238 -- list_documents() ACL filtering logic
- `src/app/schemas/acl.py` -- ACLEntryCreate/Response schema pattern
- `tests/test_acl.py` -- existing ACL test patterns and fixture helpers
- `tests/conftest.py` -- test infrastructure (aiosqlite, admin_user, async_client fixtures)
- `.planning/phases/29-folder-acl-inheritance/29-UI-SPEC.md` -- approved UI design contract

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 recursive CTE documentation -- CTE pattern verified via existing working code in `folder_service.py`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use; no new dependencies needed
- Architecture: HIGH -- mirrors existing DocumentACL pattern exactly; CTE patterns proven in codebase
- Pitfalls: HIGH -- identified from actual code inspection of edge cases in check_permission() and list_documents()

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable -- no external dependencies changing)
