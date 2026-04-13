---
phase: 27-document-type-system
plan: 01
subsystem: document-management
tags: [jsonschema, sqlalchemy, pydantic, alembic, document-types, metadata-validation]

requires:
  - phase: 02-documents
    provides: Document model, document upload service, document schemas

provides:
  - DocumentType SQLAlchemy model with self-referential parent_type_id FK
  - DocumentTypeCreate/Update/Response Pydantic schemas
  - document_type_service with CRUD, merge_schemas, get_effective_schema, validate_metadata
  - Alembic migration phase27_001 (document_types table + document_type_id FK on documents)
  - Test stubs for TYPE-01 through TYPE-04 (12 async tests, syntactically valid)
  - jsonschema>=4.26 installed and declared in pyproject.toml

affects:
  - 27-02 (router/endpoints consume service and schemas)
  - 27-03 (schema merging used in inheritance display)
  - 27-04 (validation called at upload and update)

tech-stack:
  added:
    - jsonschema>=4.26,<5 (Draft7Validator for metadata validation)
  patterns:
    - Self-referential SQLAlchemy relationship with explicit foreign_keys to avoid ambiguity
    - Service-layer merge_schemas combining parent+child JSON Schema properties/required arrays
    - Draft7Validator.iter_errors collects ALL errors before raising single 422 HTTPException
    - Untyped documents (document_type_id=None) skip validation entirely

key-files:
  created:
    - src/app/models/document_type.py
    - src/app/schemas/document_type.py
    - src/app/services/document_type_service.py
    - alembic/versions/phase27_001_document_types.py
    - tests/test_document_types.py
  modified:
    - pyproject.toml (jsonschema dependency added)
    - src/app/models/__init__.py (DocumentType import + __all__ entry)
    - src/app/models/document.py (document_type_id FK + relationship)
    - src/app/schemas/document.py (document_type_id + document_type_name on response/update)

key-decisions:
  - "jsonschema Draft7Validator chosen for broad JSON Schema draft compatibility"
  - "Max 1 level inheritance enforced at service layer (not DB constraint)"
  - "Untyped documents skip validation to preserve backward compatibility"
  - "merge_schemas: child properties override parent; required arrays are unioned"

patterns-established:
  - "Pattern 1: Service validates metadata before DB write using get_effective_schema + Draft7Validator"
  - "Pattern 2: Self-referential SQLAlchemy model uses explicit foreign_keys list to avoid AmbiguousForeignKeysError"

requirements-completed: [TYPE-01, TYPE-03, TYPE-04]

duration: 12min
completed: 2026-04-13
---

# Phase 27 Plan 01: Document Type System Foundation Summary

**DocumentType model, Pydantic schemas, service layer with JSON Schema validation and schema merging, Alembic migration, and 12-test stub file — all importable and syntactically valid.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-13T03:43:00Z
- **Completed:** 2026-04-13T03:55:21Z
- **Tasks:** 2 of 2
- **Files modified:** 9

## Accomplishments

- DocumentType model with self-referential parent_type_id FK (1-level hierarchy enforced at service)
- document_type_service with merge_schemas + get_effective_schema + validate_metadata using Draft7Validator
- Document model extended with document_type_id nullable FK; DocumentResponse/Update schemas updated
- Alembic migration phase27_001 creates document_types table and adds FK column to documents
- 12 async test stubs covering CRUD, inheritance, grandchild prevention, and metadata validation — all parse OK

## Task Commits

1. **Task 1: DocumentType model, schemas, migration, test stubs** - `6d8b8c1` (feat)
2. **Task 2: document_type_service with CRUD, schema merging, validation** - `77d846c` (feat)

## Files Created/Modified

- `src/app/models/document_type.py` — DocumentType SQLAlchemy model with self-referential FK
- `src/app/models/__init__.py` — Added DocumentType import and __all__ entry
- `src/app/models/document.py` — Added document_type_id FK and document_type relationship
- `src/app/schemas/document_type.py` — DocumentTypeCreate, DocumentTypeUpdate, DocumentTypeResponse
- `src/app/schemas/document.py` — Added document_type_id and document_type_name to DocumentResponse/DocumentUpdate
- `src/app/services/document_type_service.py` — Full service: CRUD, merge_schemas, get_effective_schema, validate_metadata
- `alembic/versions/phase27_001_document_types.py` — Migration: document_types table + FK on documents
- `tests/test_document_types.py` — 12 async test stubs (all parse clean, router not yet wired)
- `pyproject.toml` — jsonschema>=4.26,<5 dependency added

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

- `tests/test_document_types.py` — All 12 tests will fail until Plan 02 wires the router at `/api/v1/document-types/`. This is intentional per plan design (TDD RED state at plan boundary).

## Self-Check: PASSED

Files verified:
- FOUND: src/app/models/document_type.py
- FOUND: src/app/schemas/document_type.py
- FOUND: src/app/services/document_type_service.py
- FOUND: alembic/versions/phase27_001_document_types.py
- FOUND: tests/test_document_types.py

Commits verified:
- FOUND: 6d8b8c1
- FOUND: 77d846c
