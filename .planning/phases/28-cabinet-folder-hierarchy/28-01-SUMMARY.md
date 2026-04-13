---
phase: 28-cabinet-folder-hierarchy
plan: "01"
subsystem: backend-data-layer
tags: [folder, cabinet, hierarchy, sqlalchemy, alembic, service, cte, wave-0-stubs]
dependency_graph:
  requires:
    - "27-01: DocumentType model (document_type.py, phase27_001 migration)"
    - "23-01: Digital signatures (phase23_001 migration chain)"
  provides:
    - "Folder model with self-referential parent_id FK"
    - "document_folders association table"
    - "phase28_001 Alembic migration"
    - "FolderService with 12 public async functions"
    - "18 Wave 0 test stubs for Plan 02 to implement"
  affects:
    - "src/app/models/__init__.py (Folder + document_folders added to registry)"
    - "tests/test_folders.py (18 stubs ready for Plan 02)"
tech_stack:
  added: []
  patterns:
    - "Self-referential SQLAlchemy relationship (parent/children) — same pattern as DocumentType"
    - "SQLAlchemy Table() for association table with extra columns (filed_at, filed_by)"
    - "Recursive CTEs via .cte(name=..., recursive=True).union_all(recursive_term)"
    - "Module-level async functions with db: AsyncSession as first param"
key_files:
  created:
    - src/app/models/folder.py
    - alembic/versions/phase28_001_folders.py
    - src/app/services/folder_service.py
    - tests/test_folders.py
  modified:
    - src/app/models/__init__.py
decisions:
  - "Self-referential FK on folders.parent_id with named constraint fk_folders_parent_id"
  - "document_folders uses Table() (not a mapped class) to allow extra columns (filed_at, filed_by)"
  - "Folder tree built in Python from flat query to avoid N+1 recursion in async context"
  - "Recursive CTEs used for path (ancestors), descendant check, copy subtree, and delete subtree"
  - "copy_folder uses id_map dict to remap old IDs to new IDs in depth order"
metrics:
  duration: "~3.5 min"
  completed: "2026-04-13"
  tasks_completed: 2
  files_created: 4
  files_modified: 1
---

# Phase 28 Plan 01: Folder Foundation Summary

**One-liner:** SQLAlchemy Folder model with self-referential FK, document_folders junction table, phase28_001 migration, and FolderService with recursive CTE path/tree/move/copy/delete — plus 18 Wave 0 test stubs.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Folder model, migration, registry, 18 test stubs | 8728a16 | src/app/models/folder.py, alembic/versions/phase28_001_folders.py, src/app/models/__init__.py, tests/test_folders.py |
| 2 | FolderService with CTE-based operations | 5e1f45c | src/app/services/folder_service.py |

## What Was Built

### Folder Model (`src/app/models/folder.py`)

- `document_folders` association Table with `document_id`, `folder_id`, `filed_at`, `filed_by` columns
- `Folder(BaseModel)` with `name`, `description`, `parent_id` (self-FK), `is_cabinet`
- Self-referential `parent`/`children` relationships (same pattern as DocumentType)
- `documents` many-to-many relationship via `document_folders` (viewonly)

### Migration (`alembic/versions/phase28_001_folders.py`)

- `revision = "phase28_001"`, `down_revision = "phase27_001"`
- Creates `folders` table with FK constraint `fk_folders_parent_id` and index `ix_folders_parent_id`
- Creates `document_folders` table with composite PK `(document_id, folder_id)`
- `downgrade()` drops `document_folders`, index, then `folders`

### FolderService (`src/app/services/folder_service.py`)

15 async functions (12 public + 3 private):

**Public:**
- `create_cabinet` — new cabinet (is_cabinet=True, parent_id=None)
- `create_folder` — subfolder under existing parent
- `get_folder` — detail dict with path breadcrumb and document count
- `get_folder_tree` — full nested hierarchy as list of dicts
- `rename_folder` — rename in place
- `move_folder` — reparent with self/circular guards
- `copy_folder` — deep-copy subtree using id_map + document_folders duplication
- `delete_folder` — recursive CTE soft-delete + document_folders cleanup
- `file_document` — insert document_folders row (with 404/409 guards)
- `unfile_document` — delete document_folders row (with 404 guard)
- `get_folder_documents` — paginated document list for a folder
- `get_document_folder_ids` — list of folder IDs containing a document

**Private:**
- `_fetch_folder_or_404` — selectinload(parent) + 404 guard
- `_get_folder_path` — recursive CTE walking ancestors, depth DESC
- `_is_descendant` — recursive CTE checking if candidate is a descendant

### Test Stubs (`tests/test_folders.py`)

18 async test stubs all marked `pytest.skip("Wave 0 stub")`, organized by requirement:
- FOLD-01 (3 tests): create_cabinet, create_subfolder, create_subfolder_regular_user
- FOLD-02 (2 tests): get_folder_tree, tree_excludes_deleted
- FOLD-03 (5 tests): file_document, multi_file_document, unfile_document, document_response_includes_folder_ids, list_documents_by_folder
- FOLD-04 (8 tests): move_folder, move_circular_rejected, move_self_rejected, rename_folder, copy_folder, folder_detail_has_path, delete_cascades_subtree, delete_unfiles_documents

## Verification

All checks passed:
- `from app.models.folder import Folder, document_folders` — OK
- `from app.models import Folder, document_folders` — OK
- `from app.services.folder_service import create_cabinet, ...all 12...` — OK
- `pytest tests/test_folders.py --collect-only` — 18 items collected
- `pytest tests/test_folders.py` — 18 skipped (Wave 0 stub), 0 failed

## Deviations from Plan

**1. [Rule 3 - Blocking] Worktree was 20 commits behind main**

- **Found during:** Initial setup
- **Issue:** The worktree branch lacked phase 27 files (`document_type.py`, `phase27_001_document_types.py`) that the plan's `down_revision = "phase27_001"` depends on
- **Fix:** Merged `main` into the worktree branch with `git merge main --no-edit --no-verify` (fast-forward)
- **Impact:** Worktree now has all phase 27 and planning files

## Known Stubs

All 18 test functions in `tests/test_folders.py` are stubs (`pytest.skip("Wave 0 stub")`). These are intentional — Plan 02 will implement the router endpoints and wire these tests to call real API endpoints.

## Self-Check: PASSED

Files exist:
- src/app/models/folder.py — FOUND
- alembic/versions/phase28_001_folders.py — FOUND
- src/app/services/folder_service.py — FOUND
- tests/test_folders.py — FOUND
- src/app/models/__init__.py — modified, Folder/document_folders present

Commits:
- 8728a16 feat(28-01): Folder model, migration, model registry, and 18 Wave 0 test stubs — FOUND
- 5e1f45c feat(28-01): FolderService with CTE-based tree, path, move, copy, delete — FOUND
