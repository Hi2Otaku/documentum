# Phase 31: Document Relationships - Research

**Researched:** 2026-04-14
**Domain:** Document relationship management (backend model, API, frontend panel)
**Confidence:** HIGH

## Summary

Phase 31 delivers typed, directional relationships between documents. The implementation is straightforward: a new `DocumentRelationship` SQLAlchemy model with a joining table between two documents, a REST API nested under `/api/v1/documents/{document_id}/relationships`, and a new `DocumentRelationshipsPanel` React component integrated into the existing `DocumentDetailPanel`.

The codebase already has strong precedent for every pattern needed. The `VirtualDocumentChild` model demonstrates document-to-document linking with foreign keys and unique constraints. The `folders.py` API client and router show the nested-resource REST pattern. The `DocumentDetailPanel` already organizes sections with separators and cards, making integration of a new relationships section natural.

**Primary recommendation:** Follow existing patterns exactly -- BaseModel for the SQLAlchemy model, enum for relationship types, `require_permission` dependency for ACL checks, React Query with query key factory for frontend data fetching.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Create a `DocumentRelationship` model with: source_document_id, target_document_id, relationship_type (enum), description (optional), created_by. Uses BaseModel for standard audit fields.
- **D-02:** Relationship types as a string enum: `supersedes`, `references`, `amends`, `attachment_of`, `related_to`. Start with these 5 types -- extensible later.
- **D-03:** Relationships are directional -- "A supersedes B" is different from "B supersedes A". The UI shows both directions: outgoing relationships from the current document and incoming relationships to it.
- **D-04:** Unique constraint on (source_document_id, target_document_id, relationship_type) to prevent duplicate relationships of the same type between the same pair.
- **D-05:** REST endpoints under `/api/v1/documents/{document_id}/relationships` -- GET (list), POST (create), DELETE (remove).
- **D-06:** GET returns both outgoing and incoming relationships in a single response, with a `direction` field ("outgoing" | "incoming") on each entry.
- **D-07:** POST accepts `target_document_id` and `relationship_type`. The source is always the document in the URL path.
- **D-08:** ACL enforcement: user needs READ on the source document to view relationships, WRITE to create/delete.
- **D-09:** New `DocumentRelationshipsPanel` component inside the document detail view, below existing content.
- **D-10:** Panel shows relationships grouped by direction (Outgoing / Incoming) with relationship type badge, target document title as a clickable link, and a remove button.
- **D-11:** "Add Relationship" button opens a dialog with document search/select, relationship type dropdown, and optional description.
- **D-12:** Clicking a related document navigates to its detail view (same page, different document selected).

### Claude's Discretion
- Empty state design for when a document has no relationships
- Whether to show relationship count in the document list/table
- Dialog layout and validation details

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REL-01 | User can create a typed relationship between two documents (supersedes, references, is-part-of), with direction | D-01 through D-08 cover model, enum, API, and ACL enforcement |
| REL-02 | User can view all relationships for a document in a relationships panel within the document detail view | D-06, D-09, D-10 cover the panel design with bidirectional display |
| REL-03 | User can navigate from a document to any related document via the relationship link | D-12 covers click-to-navigate behavior within document detail |
</phase_requirements>

## Standard Stack

No new libraries required. This phase uses only existing project dependencies.

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.x | ORM model for DocumentRelationship | Already used for all models |
| Alembic | 1.18.x | Database migration for new table | Standard migration tool |
| FastAPI | 0.135.x | REST API endpoints | Existing API framework |
| Pydantic | 2.12.x | Request/response schemas | Existing validation layer |
| React | 19.x | Frontend UI components | Existing frontend framework |
| @tanstack/react-query | 5.x | Data fetching for relationships | Existing server state management |
| shadcn/ui | v4 | UI components (Badge, Button, Dialog, Select) | Existing component library |

**Installation:** None needed -- all dependencies already in place.

## Architecture Patterns

### Recommended Project Structure
```
src/app/
  models/
    document_relationship.py   # New: DocumentRelationship model + RelationshipType enum
  schemas/
    document_relationship.py   # New: Pydantic schemas for request/response
  services/
    document_relationship_service.py  # New: CRUD business logic
  routers/
    document_relationships.py  # New: REST endpoints (nested under documents)

frontend/src/
  api/
    documentRelationships.ts   # New: API client + query key factory
  components/documents/
    DocumentRelationshipsPanel.tsx  # New: Panel component
    AddRelationshipDialog.tsx      # New: Dialog for creating relationships

alembic/versions/
  phase31_001_document_relationships.py  # New: Migration

tests/
  test_document_relationships.py  # New: API tests
```

### Pattern 1: Self-Referential Many-to-Many (Document-to-Document)
**What:** The DocumentRelationship model links two documents via source_document_id and target_document_id, both referencing `documents.id`.
**When to use:** When modeling typed, directional edges between entities of the same type.
**Example:**
```python
# Follows VirtualDocumentChild pattern (document.py / virtual_document.py)
class DocumentRelationship(BaseModel):
    __tablename__ = "document_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id", "target_document_id", "relationship_type",
            name="uq_document_relationship",
        ),
    )

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False
    )
    target_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(
        Enum(RelationshipType, name="relationshiptype"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
```

### Pattern 2: Bidirectional Query in Single Endpoint
**What:** GET endpoint returns both outgoing (source = current doc) and incoming (target = current doc) relationships, with a `direction` field appended.
**When to use:** When users need to see all connections from a single view.
**Example:**
```python
# Service layer queries both directions
async def list_relationships(db: AsyncSession, document_id: uuid.UUID):
    outgoing = await db.execute(
        select(DocumentRelationship)
        .options(selectinload(DocumentRelationship.target_document))
        .where(DocumentRelationship.source_document_id == document_id,
               DocumentRelationship.is_deleted == False)
    )
    incoming = await db.execute(
        select(DocumentRelationship)
        .options(selectinload(DocumentRelationship.source_document))
        .where(DocumentRelationship.target_document_id == document_id,
               DocumentRelationship.is_deleted == False)
    )
    # Return combined list with direction metadata
```

### Pattern 3: Nested Router Registration
**What:** The relationships router is mounted under the documents prefix using `include_router` in main.py.
**When to use:** Sub-resources that belong to a parent entity.
**Example:**
```python
# In routers/document_relationships.py
router = APIRouter(
    prefix="/documents/{document_id}/relationships",
    tags=["document-relationships"],
)

# In main.py -- add alongside other routers
application.include_router(document_relationships.router, prefix=settings.api_v1_prefix)
```

### Anti-Patterns to Avoid
- **Lazy loading in async context:** Always use `selectinload()` for relationships accessed in response serialization. This project has a documented decision from Phase 27 about MissingGreenlet errors with aiosqlite.
- **Forgetting to register model in `__init__.py`:** SQLAlchemy Base.metadata.create_all in tests depends on all models being imported via `app.models.__init__`.
- **Duplicating ACL logic:** Use the existing `require_permission` dependency factory, not custom permission checks.
- **Self-relationships:** Must validate that source_document_id != target_document_id at the service layer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ACL enforcement | Custom permission check | `require_permission(PermissionLevel.READ/WRITE)` | Already handles superuser bypass, document existence check, proper HTTP error codes |
| Enum validation | String validation in router | Pydantic model with `RelationshipType` enum field | Automatic 422 on invalid values, documented in OpenAPI |
| Response wrapping | Manual dict construction | `EnvelopeResponse[list[RelationshipResponse]]` | Consistent API contract |
| Document search in dialog | Custom search endpoint | Existing `/api/v1/documents/?title=...` endpoint | Already supports title filter with pagination |

## Common Pitfalls

### Pitfall 1: MissingGreenlet with Relationship Eager Loading
**What goes wrong:** Accessing `relationship.target_document.title` in async context raises `MissingGreenlet` error.
**Why it happens:** aiosqlite (used in tests) and asyncpg both require explicit eager loading for relationship access outside the original query context.
**How to avoid:** Always use `selectinload()` on `source_document` and `target_document` relationships in queries.
**Warning signs:** Tests pass locally but fail with `sqlalchemy.exc.MissingGreenlet` in the response serialization step.

### Pitfall 2: Circular Self-Referential FK Ambiguity
**What goes wrong:** SQLAlchemy cannot determine which FK to use for a relationship when both FKs point to the same table.
**Why it happens:** Two ForeignKey columns (source_document_id, target_document_id) reference the same `documents.id`.
**How to avoid:** Use `foreign_keys=[source_document_id]` on the `source_document` relationship and `foreign_keys=[target_document_id]` on the `target_document` relationship.
**Warning signs:** `AmbiguousForeignKeysError` at model import time.

### Pitfall 3: Enum Name Collision in PostgreSQL
**What goes wrong:** Alembic migration fails with "type already exists" for the enum.
**Why it happens:** PostgreSQL enums are schema-level objects. If the name collides with an existing enum, migration fails.
**How to avoid:** Use a unique enum name like `relationshiptype` (following project convention: `lifecyclestate`, `permissionlevel`, etc.). In the migration, use `sa.Enum(..., name="relationshiptype", create_type=True)` or use raw DDL (as established in Phase 29's migration fix).
**Warning signs:** Migration errors containing "already exists" or duplicate type name.

### Pitfall 4: Forgetting to Check Both Document Existence
**What goes wrong:** Creating a relationship to a non-existent or soft-deleted target document succeeds at the API level but creates orphaned data.
**Why it happens:** The `require_permission` dependency only checks the source document (the one in the URL path).
**How to avoid:** In the service layer, explicitly verify the target document exists and is not soft-deleted before creating the relationship.
**Warning signs:** Relationships pointing to deleted documents appear in the UI with no title.

### Pitfall 5: DELETE Endpoint Needs Relationship ID, Not Document Pair
**What goes wrong:** API design confusion about how to identify a relationship to delete.
**Why it happens:** The natural key is (source, target, type) but that is unwieldy in a URL.
**How to avoid:** Use the relationship's UUID (`id` from BaseModel) in the DELETE path: `DELETE /documents/{document_id}/relationships/{relationship_id}`.
**Warning signs:** Complicated query string parameters for deletion.

## Code Examples

### Backend Model
```python
# src/app/models/document_relationship.py
import uuid
from sqlalchemy import Enum, ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
from app.models.enums import RelationshipType

class DocumentRelationship(BaseModel):
    __tablename__ = "document_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id", "target_document_id", "relationship_type",
            name="uq_document_relationship",
        ),
    )

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False
    )
    target_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("documents.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(
        Enum(RelationshipType, name="relationshiptype"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_document: Mapped["Document"] = relationship(
        foreign_keys=[source_document_id], lazy="selectin"
    )
    target_document: Mapped["Document"] = relationship(
        foreign_keys=[target_document_id], lazy="selectin"
    )
```

### Enum Addition
```python
# Add to src/app/models/enums.py
class RelationshipType(str, enum.Enum):
    SUPERSEDES = "supersedes"
    REFERENCES = "references"
    AMENDS = "amends"
    ATTACHMENT_OF = "attachment_of"
    RELATED_TO = "related_to"
```

### Pydantic Schemas
```python
# src/app/schemas/document_relationship.py
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class RelationshipCreate(BaseModel):
    target_document_id: uuid.UUID
    relationship_type: str  # validated against enum in service
    description: str | None = None

class RelationshipResponse(BaseModel):
    id: uuid.UUID
    source_document_id: uuid.UUID
    target_document_id: uuid.UUID
    relationship_type: str
    description: str | None
    direction: str  # "outgoing" | "incoming"
    related_document_id: uuid.UUID  # the "other" document
    related_document_title: str
    created_at: datetime
    created_by: str | None
    model_config = ConfigDict(from_attributes=True)
```

### Frontend API Client Pattern
```typescript
// frontend/src/api/documentRelationships.ts
// Follows folders.ts pattern exactly

export const relationshipKeys = {
  all: ["document-relationships"] as const,
  list: (documentId: string) => [...relationshipKeys.all, documentId] as const,
};

export interface RelationshipResponse {
  id: string;
  source_document_id: string;
  target_document_id: string;
  relationship_type: string;
  description: string | null;
  direction: "outgoing" | "incoming";
  related_document_id: string;
  related_document_title: string;
  created_at: string;
  created_by: string | null;
}

export async function fetchRelationships(documentId: string): Promise<RelationshipResponse[]> {
  const res = await apiFetch<{ data: RelationshipResponse[] }>(
    `/api/v1/documents/${documentId}/relationships`
  );
  return res.data;
}

export async function createRelationship(
  documentId: string,
  data: { target_document_id: string; relationship_type: string; description?: string }
): Promise<RelationshipResponse> {
  const res = await apiMutate<{ data: RelationshipResponse }>(
    `/api/v1/documents/${documentId}/relationships`,
    "POST",
    data,
  );
  return res.data;
}

export async function deleteRelationship(
  documentId: string,
  relationshipId: string,
): Promise<void> {
  // DELETE with authHeaders, following folders.ts deleteFolder pattern
}
```

### Migration Pattern
```python
# alembic/versions/phase31_001_document_relationships.py
# Follows phase28_001_folders.py pattern with raw DDL for enum (per Phase 29 decision)

def upgrade() -> None:
    op.execute("CREATE TYPE relationshiptype AS ENUM ('supersedes', 'references', 'amends', 'attachment_of', 'related_to')")
    op.create_table(
        "document_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("target_document_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.Enum("supersedes", "references", "amends", "attachment_of", "related_to", name="relationshiptype", create_type=False), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["target_document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_document_id", "target_document_id", "relationship_type", name="uq_document_relationship"),
    )
    op.create_index("ix_doc_rel_source", "document_relationships", ["source_document_id"])
    op.create_index("ix_doc_rel_target", "document_relationships", ["target_document_id"])

def downgrade() -> None:
    op.drop_table("document_relationships")
    op.execute("DROP TYPE relationshiptype")
```

## Project Constraints (from CLAUDE.md)

- **Tech stack:** FastAPI backend, React + Vite + TypeScript frontend
- **ORM:** SQLAlchemy 2.0 with async (asyncpg for production, aiosqlite for tests)
- **Migrations:** Alembic with raw DDL for PostgreSQL-specific enum types
- **UI components:** shadcn/ui (Radix + Tailwind)
- **State management:** React Query for server state, Zustand for UI state
- **Testing:** pytest with pytest-asyncio, httpx AsyncClient, in-memory SQLite
- **Patterns:** BaseModel for audit fields, EnvelopeResponse for API wrapping, selectinload for async relationships
- **GSD Workflow:** All changes through GSD commands

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_document_relationships.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REL-01 | Create typed directional relationship between two documents | integration | `pytest tests/test_document_relationships.py::test_create_relationship -x` | Wave 0 |
| REL-01 | Prevent duplicate (source, target, type) | integration | `pytest tests/test_document_relationships.py::test_duplicate_relationship_rejected -x` | Wave 0 |
| REL-01 | Prevent self-relationship | integration | `pytest tests/test_document_relationships.py::test_self_relationship_rejected -x` | Wave 0 |
| REL-02 | List both outgoing and incoming relationships | integration | `pytest tests/test_document_relationships.py::test_list_relationships_bidirectional -x` | Wave 0 |
| REL-03 | Response includes related document title for navigation | integration | `pytest tests/test_document_relationships.py::test_relationship_includes_document_title -x` | Wave 0 |
| REL-01 | Delete relationship by ID | integration | `pytest tests/test_document_relationships.py::test_delete_relationship -x` | Wave 0 |
| REL-01 | ACL: WRITE required for create/delete | integration | `pytest tests/test_document_relationships.py::test_acl_write_required -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_document_relationships.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_document_relationships.py` -- covers REL-01, REL-02, REL-03
- No framework install or conftest changes needed -- existing infrastructure is sufficient

## Open Questions

1. **Should soft-deleted relationships be visible?**
   - What we know: BaseModel provides `is_deleted` flag; all queries should filter `is_deleted == False`
   - What's unclear: Whether to expose a "show deleted" option
   - Recommendation: Filter out deleted relationships. No "show deleted" toggle -- keep it simple for v1.

2. **ACL check on target document during creation?**
   - What we know: D-08 says WRITE on source. But should user also need READ on target?
   - What's unclear: Whether a user should be able to link to a document they cannot see
   - Recommendation: Require READ on target document as well -- prevents information disclosure (confirming a document exists by its ID).

## Sources

### Primary (HIGH confidence)
- Project codebase: `src/app/models/virtual_document.py` -- self-referential FK pattern with unique constraints
- Project codebase: `src/app/models/document.py` -- Document model structure, relationship definitions
- Project codebase: `src/app/routers/documents.py` -- Nested resource router pattern, ACL dependency usage
- Project codebase: `frontend/src/api/folders.ts` -- API client pattern with query key factory
- Project codebase: `frontend/src/components/documents/DocumentDetailPanel.tsx` -- Integration point structure
- Project codebase: `src/app/core/dependencies.py` -- `require_permission` factory pattern
- Project codebase: `alembic/versions/phase28_001_folders.py` -- Migration pattern with raw DDL
- Project decisions: Phase 27 selectinload requirement, Phase 29 raw DDL for enum migration

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns exist in codebase
- Architecture: HIGH -- direct replication of VirtualDocument + Folder patterns
- Pitfalls: HIGH -- each pitfall identified from actual project history (MissingGreenlet, enum collisions)

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable -- no external dependency changes expected)
