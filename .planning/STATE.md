---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Document-Centric ECM
status: executing
stopped_at: Completed 29-01-PLAN.md (folder ACL inheritance backend)
last_updated: "2026-04-13T13:55:07.636Z"
last_activity: 2026-04-13
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 10
  completed_plans: 8
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-13)

**Core value:** Any workflow or document management use case described in the Documentum specification can be modeled and executed end-to-end.
**Current focus:** Phase 29 — folder-acl-inheritance

## Current Position

Phase: 29 (folder-acl-inheritance) — EXECUTING
Plan: 2 of 3
Status: Ready to execute
Last activity: 2026-04-13

Progress: [..........] 0% (v1.3: 0/7 phases)

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v1.3)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend (from v1.2):**

| Phase 24 P03 | 1m | 2 tasks | 5 files |
| Phase 24-01 P01 | 2min | 2 tasks | 4 files |
| Phase 25 P01 | 2m | 2 tasks | 3 files |
| Phase 26 P01 | 1m | 2 tasks | 1 files |
| Phase 27-document-type-system P01 | 12 | 2 tasks | 9 files |
| Phase 27-document-type-system P02 | 5min | 2 tasks | 5 files |
| Phase 27-document-type-system P03 | 3.5min | 2 tasks | 8 files |
| Phase 28-cabinet-folder-hierarchy P03 | 60 | 3 tasks | 12 files |
| Phase 29-folder-acl-inheritance P01 | 4min | 3 tasks | 7 files |

## Accumulated Context

### Decisions

v1.3 architecture decisions (resolved during research):

- No dm_sysobject polymorphic base table -- Python mixin instead (too many FKs to migrate)
- No ltree PostgreSQL extension -- adjacency list + recursive CTEs for folder hierarchy
- PostgreSQL tsvector for full-text search -- no Elasticsearch
- New Python packages: jsonschema, PyPDF2, python-docx
- [Phase 27-document-type-system]: jsonschema Draft7Validator for metadata validation; max 1 level inheritance enforced at service layer; untyped documents skip validation for backward compatibility
- [Phase 27-document-type-system]: Use explicit selectinload() in async queries for relationships accessed in response serialization (prevents MissingGreenlet in aiosqlite)
- [Phase 27-document-type-system]: Place validate_metadata in router before service call to keep upload_document service pure and reusable
- [Phase 27-document-type-system]: Client-side JSON schema validation in dialog validates parse correctness and property count before API call
- [Phase 27-document-type-system]: Parent type dropdown restricted to root types (parent_type_id === null) to prevent 3-level hierarchy in UI
- [Phase 28-cabinet-folder-hierarchy]: FolderPickerDialog is reusable for both Move and file-document flows, avoiding UI duplication
- [Phase 28-cabinet-folder-hierarchy]: deleteFolder and unfileDocument use raw fetch (not apiMutate) consistent with deleteDocumentType pattern
- [Phase 28-cabinet-folder-hierarchy]: folder_ids on DocumentResponse is optional for backward compatibility
- [Phase 29-folder-acl-inheritance]: _get_ancestor_folder_ids() extracted as shared CTE helper for reuse by check_permission and future get_access_source
- [Phase 29-folder-acl-inheritance]: Direct document ACL overrides folder ACL entirely — folder ACL only runs when no direct DocumentACL entries exist
- [Phase 29-folder-acl-inheritance]: N+1 per-document check_permission for get_folder_documents acceptable with page_size cap; list_documents uses subquery descendant CTE

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-04-13T13:55:07.632Z
Stopped at: Completed 29-01-PLAN.md (folder ACL inheritance backend)
Resume file: None
