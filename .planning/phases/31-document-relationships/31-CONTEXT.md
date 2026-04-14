# Phase 31: Document Relationships - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — recommended defaults selected)

<domain>
## Phase Boundary

This phase delivers typed, directional relationships between documents with full CRUD and navigation. Users can create relationships like "supersedes", "references", "amends", or "is attachment of" between any two documents. A dedicated relationships panel in the document detail view shows all connections, and clicking a link navigates to the related document.

</domain>

<decisions>
## Implementation Decisions

### Relationship Model
- **D-01:** Create a `DocumentRelationship` model with: source_document_id, target_document_id, relationship_type (enum), description (optional), created_by. Uses BaseModel for standard audit fields.
- **D-02:** Relationship types as a string enum: `supersedes`, `references`, `amends`, `attachment_of`, `related_to`. Start with these 5 types — extensible later.
- **D-03:** Relationships are directional — "A supersedes B" is different from "B supersedes A". The UI shows both directions: outgoing relationships from the current document and incoming relationships to it.
- **D-04:** Unique constraint on (source_document_id, target_document_id, relationship_type) to prevent duplicate relationships of the same type between the same pair.

### API Design
- **D-05:** REST endpoints under `/api/v1/documents/{document_id}/relationships` — GET (list), POST (create), DELETE (remove).
- **D-06:** GET returns both outgoing and incoming relationships in a single response, with a `direction` field ("outgoing" | "incoming") on each entry.
- **D-07:** POST accepts `target_document_id` and `relationship_type`. The source is always the document in the URL path.
- **D-08:** ACL enforcement: user needs READ on the source document to view relationships, WRITE to create/delete.

### Frontend
- **D-09:** New `DocumentRelationshipsPanel` component inside the document detail view, below existing content.
- **D-10:** Panel shows relationships grouped by direction (Outgoing / Incoming) with relationship type badge, target document title as a clickable link, and a remove button.
- **D-11:** "Add Relationship" button opens a dialog with document search/select, relationship type dropdown, and optional description.
- **D-12:** Clicking a related document navigates to its detail view (same page, different document selected).

### Claude's Discretion
- Empty state design for when a document has no relationships
- Whether to show relationship count in the document list/table
- Dialog layout and validation details

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Patterns
- `src/app/models/document.py` — Document model structure
- `src/app/models/base.py` — BaseModel with standard audit fields
- `src/app/routers/documents.py` — Document router pattern for nested resources
- `src/app/services/document_service.py` — Document CRUD with ACL enforcement

### Frontend
- `frontend/src/components/documents/DocumentDetailPanel.tsx` — Where relationships panel integrates
- `frontend/src/api/folders.ts` — Pattern for nested resource API clients

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- BaseModel provides id, created_at, updated_at, created_by, is_deleted
- EnvelopeResponse + PaginationMeta for API responses
- DocumentDetailPanel as integration point for new panel section
- Existing ACL check_permission for access control

### Established Patterns
- SQLAlchemy models with Mapped[] type hints
- Alembic migrations for schema changes
- React Query with query key factories
- shadcn/ui components (Badge, Button, Dialog, Select)

### Integration Points
- Document detail panel — add relationships section
- Document model — add relationship backref

</code_context>

<specifics>
## Specific Ideas

No specific requirements — autonomous mode used recommended defaults.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 31-document-relationships*
*Context gathered: 2026-04-14*
