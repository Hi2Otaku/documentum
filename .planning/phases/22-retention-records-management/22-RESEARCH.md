# Phase 22: Retention & Records Management - Research

**Date:** 2026-04-06
**Discovery Level:** 0 (pure internal work, existing patterns only)

## Codebase Analysis

### Document Model (`src/app/models/document.py`)
- `Document` extends `BaseModel` (id, created_at, updated_at, created_by, is_deleted)
- Has title, author, filename, content_type, custom_properties, locked_by/locked_at, version fields, lifecycle_state
- Related: `DocumentVersion` with content hash, MinIO object key, renditions

### Document Deletion Flow (`src/app/routers/documents.py`, line 112-134)
- `DELETE /documents/{document_id}` - admin only via `get_current_active_admin`
- Soft-delete only: sets `document.is_deleted = True`
- Creates audit record with action="delete"
- Returns EnvelopeResponse with message
- **This is the interception point for retention blocking (RET-03)**

### Established Patterns
- **Models:** SQLAlchemy 2.0 declarative with `BaseModel` base class, Uuid PKs, enums in `enums.py`
- **Schemas:** Pydantic v2 with `ConfigDict(from_attributes=True)`, `EnvelopeResponse[T]` envelope
- **Routers:** FastAPI `APIRouter` with prefix, tags, Depends for auth/db
- **Services:** Async functions taking `AsyncSession`, raise `HTTPException` for errors
- **Migrations:** Alembic with `phase{N}_001` revision IDs, enum types created explicitly
- **Registration:** Models in `models/__init__.py`, routers in `main.py` via `include_router`

### Migration Chain
Multiple heads exist (phase16_001, phase17_001, phase18_001, phase19_001, phase20_001 all branch from phase11_001).
Phase 22 migration should use `down_revision = 'phase20_001'` or another leaf. Given the branching pattern, using `phase11_001` is the safest common ancestor.

## Architecture Decisions

### Retention Policy Model
- `RetentionPolicy` table: name, description, retention_period_days (int), disposition_action (enum: archive/delete)
- `DocumentRetention` join table: document_id FK, retention_policy_id FK, applied_at, expires_at (computed), applied_by
- `LegalHold` table: document_id FK, reason, placed_by, placed_at, released_at (null = active)

### Deletion Blocking Strategy
- Add a service function `check_retention_block(db, document_id)` that:
  1. Checks for active legal holds (released_at IS NULL)
  2. Checks for active retention (expires_at > now)
  3. Returns blocking reason or None
- Call this from the delete endpoint before soft-delete
- Raise HTTP 409 Conflict with clear message if blocked

### No New External Dependencies
All features use existing SQLAlchemy, FastAPI, Pydantic stack. Level 0 discovery.
