---
phase: 31-document-relationships
verified: 2026-04-14T11:00:00Z
status: gaps_found
score: 5/7 must-haves verified
gaps:
  - truth: "ACL enforcement: WRITE required for create/delete, READ for list"
    status: failed
    reason: "Router uses only get_current_user dependency. No require_permission calls exist in routers/relationships.py. Any authenticated user can create, list, and delete relationships regardless of document permissions."
    artifacts:
      - path: "src/app/routers/relationships.py"
        issue: "Missing Depends(require_permission(PermissionLevel.WRITE)) on POST/DELETE and Depends(require_permission(PermissionLevel.READ)) on GET"
    missing:
      - "Import require_permission and PermissionLevel from app.core.dependencies and app.models.enums"
      - "Add require_permission(PermissionLevel.READ) dependency to GET endpoint"
      - "Add require_permission(PermissionLevel.WRITE) dependency to POST and DELETE endpoints"
  - truth: "Integration tests cover create, duplicate rejection, self-ref rejection, bidirectional list, title inclusion, delete, and ACL"
    status: failed
    reason: "tests/test_document_relationships.py does not exist. Zero test coverage for the relationships backend."
    artifacts:
      - path: "tests/test_document_relationships.py"
        issue: "File does not exist (MISSING)"
    missing:
      - "Create tests/test_document_relationships.py with integration tests for all CRUD operations"
      - "Test self-relationship rejection (400)"
      - "Test duplicate relationship rejection (409)"
      - "Test bidirectional listing"
      - "Test delete (soft-delete)"
      - "Test ACL enforcement (once ACL is added to router)"
human_verification:
  - test: "Create a relationship between two documents via the UI"
    expected: "AddRelationshipDialog opens, user can search for a target document, select relationship type, submit, and see the new relationship in the panel"
    why_human: "Requires running application with database, visual UI interaction"
  - test: "Click a related document title in the RelationshipPanel"
    expected: "DocumentDetailPanel switches to show the related document's details"
    why_human: "Navigation behavior requires running UI with state management"
  - test: "Delete a relationship via the trash icon"
    expected: "Relationship disappears from the panel after hover-reveal trash icon is clicked"
    why_human: "Requires running application with real API calls"
---

# Phase 31: Document Relationships Verification Report

**Phase Goal:** Users can create and navigate typed relationships between documents, establishing traceability links
**Verified:** 2026-04-14T11:00:00Z
**Status:** gaps_found
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Creating a relationship between two documents with a valid type succeeds and returns the relationship | VERIFIED | `relationship_service.create_relationship` validates source != target, checks duplicates, creates record, refreshes with eagerly loaded documents. Router POST returns 201 with EnvelopeResponse. |
| 2 | Duplicate (source, target, type) combination is rejected | VERIFIED | `relationship_service.py` line 61-69: queries for existing non-deleted relationship with same triple, raises 409 CONFLICT. |
| 3 | Self-relationships (source == target) are rejected | VERIFIED | `relationship_service.py` line 40-44: explicit check `source_document_id == target_document_id` raises 400. Frontend also filters out source doc from search results. |
| 4 | GET returns both outgoing and incoming relationships with direction field | VERIFIED (with deviation) | `list_relationships` uses `or_()` on source/target. Direction is NOT in API response; frontend computes it by comparing `source_document_id` to the current `documentId`. Functionally equivalent. |
| 5 | Response includes related document title for navigation | VERIFIED | API returns `source_document_title` and `target_document_title` via eagerly loaded relationships. Frontend picks the correct one based on direction. |
| 6 | DELETE removes a relationship by its UUID | VERIFIED | `delete_relationship` does soft-delete (`is_deleted = True`). Router returns EnvelopeResponse with meta message. |
| 7 | ACL enforcement: WRITE required for create/delete, READ for list | FAILED | Router only uses `Depends(get_current_user)`. No `require_permission` calls. Any authenticated user can CRUD relationships on any document. |

**Score:** 5/7 truths verified (truths 4 and 5 verified with acceptable deviations; truth 7 failed)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/app/models/document_relationship.py` | DocumentRelationship model | VERIFIED | 51 lines, class DocumentRelationship with UniqueConstraint, source/target FKs, selectinload relationships |
| `src/app/models/enums.py` | RelationshipType enum | NOT HERE | RelationshipType is defined in `document_relationship.py`, not in `enums.py`. Functional but inconsistent with codebase pattern. |
| `src/app/schemas/document_relationship.py` | Pydantic schemas | VERIFIED | RelationshipCreate and RelationshipResponse present. Schema uses source/target_document_title instead of direction/related_document_id. |
| `src/app/services/relationship_service.py` | CRUD business logic | VERIFIED | 135 lines. create_relationship, list_relationships, delete_relationship all substantive with validation. |
| `src/app/routers/relationships.py` | REST API endpoints | VERIFIED (with gap) | GET/POST/DELETE endpoints present. Missing ACL enforcement (see gap). Note: file named `relationships.py` not `document_relationships.py`. |
| `alembic/versions/phase31_001_document_relationships.py` | Database migration | VERIFIED | Creates table with enum, unique constraint, indexes. Downgrade drops all. |
| `tests/test_document_relationships.py` | Integration tests | MISSING | File does not exist. |
| `frontend/src/api/relationships.ts` | API client | VERIFIED | fetchRelationships, createRelationship, deleteRelationship, relationshipKeys factory. 130 lines. |
| `frontend/src/components/documents/RelationshipPanel.tsx` | Relationships panel | VERIFIED | 230 lines. Direction grouping (outgoing/incoming), type badges with colors, delete mutation, empty state, skeleton loading, onNavigate prop. |
| `frontend/src/components/documents/AddRelationshipDialog.tsx` | Add relationship dialog | VERIFIED | 176 lines. Document search via fetchDocuments, type dropdown, description textarea, error display, submit validation. |
| `frontend/src/components/documents/DocumentDetailPanel.tsx` | Updated detail panel | VERIFIED | RelationshipPanel imported and rendered as Section 8 after Separator. onDocumentSelect prop wired to onNavigate. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `routers/relationships.py` | `services/relationship_service.py` | service function calls | WIRED | `relationship_service.list_relationships`, `.create_relationship`, `.delete_relationship` all called |
| `main.py` | `routers/relationships.py` | include_router | WIRED | Line 106: `application.include_router(relationships.router, prefix=settings.api_v1_prefix)` |
| `models/__init__.py` | `models/document_relationship.py` | import | WIRED | `DocumentRelationship` and `RelationshipType` imported and in `__all__` |
| `RelationshipPanel.tsx` | `api/relationships.ts` | useQuery + useMutation | WIRED | `fetchRelationships`, `deleteRelationship`, `relationshipKeys` all imported and used |
| `AddRelationshipDialog.tsx` | `api/relationships.ts` | useMutation | WIRED | `createRelationship`, `relationshipKeys`, `RELATIONSHIP_TYPES`, `RELATIONSHIP_TYPE_LABELS` imported and used |
| `DocumentDetailPanel.tsx` | `RelationshipPanel.tsx` | component import | WIRED | `RelationshipPanel` imported and rendered with documentId and onNavigate props |
| `DocumentsPage.tsx` | `DocumentDetailPanel.tsx` | onDocumentSelect prop | WIRED | `onDocumentSelect={setSelectedDocumentId}` passes selection handler |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| RelationshipPanel.tsx | `relationships` | `useQuery -> fetchRelationships -> GET /api/v1/documents/{id}/relationships` | Yes -- service queries DB via SQLAlchemy `select(DocumentRelationship)` with `or_()` and `selectinload` | FLOWING |
| AddRelationshipDialog.tsx | `searchResults` | `useQuery -> fetchDocuments` | Yes -- existing documents API with DB query | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED (requires running server with database for API endpoint testing)

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| REL-01 | 31-01 | User can create a typed relationship between two documents (supersedes, references, is-part-of), with direction | SATISFIED | Backend CRUD service + POST endpoint + AddRelationshipDialog. 4 types available (supersedes, references, is_part_of, related_to). Plan had 5 types but requirements only mention 3. |
| REL-02 | 31-01, 31-02 | User can view all relationships for a document in a relationships panel within the document detail view | SATISFIED | RelationshipPanel rendered in DocumentDetailPanel Section 8, shows outgoing/incoming groups with type badges |
| REL-03 | 31-02 | User can navigate from a document to any related document via the relationship link | SATISFIED | Clickable document titles in RelationshipPanel call onNavigate -> onDocumentSelect -> setSelectedDocumentId in DocumentsPage |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/app/routers/relationships.py` | all endpoints | Missing ACL enforcement -- no `require_permission` dependency | Blocker | Any authenticated user can create/delete relationships on any document regardless of permissions |
| `src/app/models/document_relationship.py` | 12 | `RelationshipType` defined here instead of `enums.py` | Info | Inconsistent with codebase pattern where all enums live in enums.py |
| `src/app/routers/relationships.py` | 88 | DELETE returns 200 with EnvelopeResponse instead of 204 No Content | Warning | Deviation from REST convention and plan specification |

### Human Verification Required

### 1. End-to-End Relationship Creation
**Test:** Open a document detail panel, click "Add" in the Relationships section, search for another document, select a type, and submit.
**Expected:** New relationship appears in the panel with correct type badge and direction indicator.
**Why human:** Requires running application with database, visual UI interaction.

### 2. Cross-Document Navigation
**Test:** Click a related document's title in the RelationshipPanel.
**Expected:** DocumentDetailPanel switches to show the clicked document's details.
**Why human:** Navigation behavior requires running UI with live state management.

### 3. Relationship Deletion
**Test:** Hover over a relationship row and click the trash icon.
**Expected:** Relationship disappears from the panel immediately.
**Why human:** Hover interaction and real-time UI update require running application.

### Gaps Summary

Two gaps prevent full goal achievement:

1. **Missing ACL Enforcement (Blocker):** The router at `src/app/routers/relationships.py` does not use `require_permission` dependency from `app.core.dependencies`. All three endpoints (GET, POST, DELETE) only require authentication via `get_current_user` but do not check document-level permissions. This means any authenticated user can create relationships on documents they have no access to and delete relationships they should not be able to modify. The plan explicitly required WRITE for create/delete and READ for list.

2. **Missing Integration Tests (Blocker):** `tests/test_document_relationships.py` was planned with 7 test cases (create, duplicate rejection, self-ref rejection, bidirectional list, title inclusion, delete, ACL) but the file was never created. There is zero automated test coverage for the relationships backend.

Both gaps share a root cause: the implementation was done rapidly (4 minutes per SUMMARY) and skipped the testing and security hardening steps.

**Note:** The relationship type set differs from the original plan (4 types: supersedes, references, is_part_of, related_to vs. planned 5: supersedes, references, amends, attachment_of, related_to). However, REQUIREMENTS.md REL-01 only specifies "supersedes, references, is-part-of" so the current set satisfies the requirement.

---

_Verified: 2026-04-14T11:00:00Z_
_Verifier: Claude (gsd-verifier)_
