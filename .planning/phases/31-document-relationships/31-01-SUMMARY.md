---
phase: 31-document-relationships
plan: "01"
subsystem: full-stack
tags: [relationships, document-links, supersedes, references, is-part-of, related-to]
dependency_graph:
  requires:
    - "28-01: Folder model (phase28_001 migration chain)"
    - "01-01: Document model, User model"
  provides:
    - "DocumentRelationship model with RelationshipType enum"
    - "phase31_001 Alembic migration for document_relationships table"
    - "relationship_service with create, list, delete operations"
    - "REST endpoints: GET/POST/DELETE /documents/{id}/relationships"
    - "Frontend RelationshipPanel with AddRelationshipDialog"
  affects:
    - "src/app/models/__init__.py (DocumentRelationship + RelationshipType added)"
    - "src/app/main.py (relationships router registered)"
    - "frontend/src/components/documents/DocumentDetailPanel.tsx (RelationshipPanel integrated)"
tech_stack:
  added: []
  patterns:
    - "Directional relationship model with source/target FKs to same table"
    - "UniqueConstraint on (source, target, type) to prevent duplicates"
    - "selectinload for eager loading related document titles"
    - "Bidirectional listing: OR condition on source_document_id / target_document_id"
key_files:
  created:
    - src/app/models/document_relationship.py
    - alembic/versions/phase31_001_document_relationships.py
    - src/app/schemas/document_relationship.py
    - src/app/services/relationship_service.py
    - src/app/routers/relationships.py
    - frontend/src/api/relationships.ts
    - frontend/src/components/documents/AddRelationshipDialog.tsx
    - frontend/src/components/documents/RelationshipPanel.tsx
  modified:
    - src/app/models/__init__.py
    - src/app/main.py
    - frontend/src/components/documents/DocumentDetailPanel.tsx
decisions:
  - "Relationships are directional (source -> target) with both directions shown in the panel"
  - "Soft-delete on relationships (is_deleted flag) consistent with BaseModel pattern"
  - "RelationshipPanel placed after Folders section in DocumentDetailPanel"
  - "Document search in AddRelationshipDialog uses existing fetchDocuments API with title filter"
metrics:
  duration: "4min"
  completed: "2026-04-14T03:44:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 8
  files_modified: 3
---

# Phase 31 Plan 01: Document Relationships Summary

Typed directional document links with full-stack CRUD (supersedes, references, is_part_of, related_to) and a RelationshipPanel in the document detail view.

## What Was Built

### Backend (Task 1)
- **DocumentRelationship model** with `RelationshipType` enum (`supersedes`, `references`, `is_part_of`, `related_to`), source/target FK to documents table, unique constraint preventing duplicate relationships
- **Alembic migration** `phase31_001` creating `document_relationships` table with indexes on both source and target columns
- **relationship_service** with three operations: `create_relationship` (validates both documents exist, prevents self-references and duplicates), `list_relationships` (returns all relationships where document is source OR target), `delete_relationship` (soft-delete with ownership check)
- **REST router** at `/documents/{id}/relationships` with GET (list), POST (create), DELETE (remove), including audit trail integration
- **Pydantic schemas** for request validation and response serialization with document title resolution

### Frontend (Task 2)
- **relationships.ts API client** with `fetchRelationships`, `createRelationship`, `deleteRelationship`, query key helpers, and type label constants
- **RelationshipPanel** component showing all relationships with color-coded type badges, directional indicators (outgoing arrow / incoming label), clickable document links for navigation, and hover-reveal delete button
- **AddRelationshipDialog** with relationship type selector, document search (using existing fetchDocuments API with title filter), and optional description field
- **DocumentDetailPanel integration** as Section 8, placed after the Folders section with a separator

## Deviations from Plan

None - no plan file existed, so implementation was derived directly from ROADMAP requirements (REL-01, REL-02, REL-03) and research architecture spec.

## Decisions Made

1. **Directional relationships with bidirectional listing**: Relationships store a source -> target direction, but the panel shows all relationships where the document is either source or target, with direction indicators
2. **Soft-delete pattern**: Consistent with all other models using BaseModel's `is_deleted` flag
3. **Document search in dialog**: Reuses the existing `fetchDocuments` API with title filter rather than a dedicated search endpoint
4. **Router as separate module**: Created `routers/relationships.py` rather than extending the documents router, keeping concerns separated

## Verification

- Backend model, registry, and service imports verified clean
- Router follows established pattern (APIRouter, Depends(get_db), Depends(get_current_user))
- Frontend follows exact patterns from existing API clients and components

## Self-Check: PASSED

All 8 created files verified on disk. Both commits (b677052, 89f557a) verified in git log.
