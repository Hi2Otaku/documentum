# Phase 28: Cabinet/Folder Hierarchy — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 28-cabinet-folder-hierarchy
**Mode:** auto (gsd:autonomous — all decisions auto-selected)

---

## Cabinet vs Folder Model

| Option | Description | Selected |
|--------|-------------|----------|
| Single table | `folders` table, cabinets = `parent_id IS NULL` | ✓ |
| Two tables | Separate `cabinets` and `folders` tables | |
| Polymorphic | `dm_sysobject`-style base table | |

**Auto-selected:** Single table — follows `document_types.parent_type_id` precedent; STATE.md already ruled out polymorphic base table.

---

## Document Filing Model

| Option | Description | Selected |
|--------|-------------|----------|
| Many-to-many junction | `document_folders` table with composite PK | ✓ |
| Single folder_id on document | Document belongs to one folder | |
| Virtual (tag-based) | No filing table, folders as tags | |

**Auto-selected:** Many-to-many — ROADMAP requires multi-filing ("file a document into multiple folders"); FOLD-03 explicit.

---

## Path Resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Recursive CTE | Computed on demand via `WITH RECURSIVE` | ✓ |
| ltree extension | PostgreSQL ltree for materialized paths | |
| Application-layer | Iterate parent_ids in Python | |

**Auto-selected:** Recursive CTE — STATE.md explicitly decided against ltree; adjacency list + CTE is the established pattern.

---

## Frontend Scope in Phase 28

| Option | Description | Selected |
|--------|-------------|----------|
| CRUD + tree navigator | Admin page + FolderTree component + filing UI | ✓ |
| Full browse experience | Folder tree sidebar + document grid in /browse | |
| Backend only | API only, no frontend | |

**Auto-selected:** CRUD + tree navigator — Phase 32 owns the full browse experience; Phase 28 needs functional CRUD for dependent phases (29, 30, 32) to build on. FolderTree component is reusable in Phase 32.

---

## Claude's Discretion

- Folder delete cascade behavior (soft-delete subtree, unfile documents, don't delete documents)
- Copy endpoint design (POST /folders/{id}/copy with destination parent_id)
- `is_cabinet` boolean flag for API response clarity
- Breadcrumb resolution included in GET /folders/{id} response
- No auto-filing on document upload — filing is a separate user action

## Deferred Ideas

- Folder-level ACL (Phase 29 — already in roadmap)
- Smart folders / saved searches (Phase 33 — already in roadmap)
- Lazy-load tree children on expand for large hierarchies (Phase 32 optimization)
