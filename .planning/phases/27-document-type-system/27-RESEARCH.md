# Phase 27: Document Type System - Research

**Researched:** 2026-04-13
**Domain:** Document type definitions with JSON Schema validation, dynamic metadata forms
**Confidence:** HIGH

## Summary

Phase 27 introduces a document type system allowing admins to define named types with JSON Schema metadata definitions, assign types to documents, validate metadata on save, and support one-level type inheritance. This is a greenfield feature with no existing document type code in the codebase.

The implementation is straightforward: a new `DocumentType` model extending `BaseModel`, a new `document_type_id` nullable FK on `Document`, validation via the `jsonschema` Python library (v4.26.0, not yet installed), and frontend components using existing shadcn/ui primitives. The codebase patterns are well-established across 26 prior phases -- model/service/router/schema layers, `@tanstack/react-query` for data fetching, `@tanstack/react-table` for tables, and Radix-based shadcn/ui components.

**Primary recommendation:** Follow the existing model/service/router/schema pattern exactly. The only new dependency is `jsonschema`. Validate `custom_properties` against merged parent+child schemas at the service layer on every document write (upload, update). Frontend renders dynamic form fields from the JSON Schema at runtime.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Separate `document_types` DB table with `parent_type_id` FK (max 1 level inheritance)
- Schema merged at read time (child fields + parent fields)
- Admin users only can create/edit types -- role-based gate on API
- Validate on document save at API level -- single enforcement point
- Reject save on validation failure with descriptive field-level error messages
- No retroactive validation -- schema changes only affect new saves
- Type is optional -- documents with no type skip validation entirely
- Dedicated `/admin/types` page in existing admin/settings area
- JSON editor (textarea with syntax highlighting) for schema field definitions
- Supported field types: string, number, boolean, date, enum (select)
- Type list displayed as table: name, field count, document count, parent type column
- Type selection dropdown on both upload form and document edit form
- Type-specific fields render as dynamic section below standard fields
- Type can be changed after upload with warning if metadata mismatch
- Untyped documents show em-dash in type column

### Claude's Discretion
- Exact JSON Schema subset to support beyond the 5 primitive types listed
- Whether to show a schema preview/sample document in the type admin page
- Ordering of type-specific fields in the rendered form

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TYPE-01 | User can define a named document type with a JSON Schema metadata definition | `DocumentType` model with `name`, `description`, `metadata_schema` JSON column; CRUD endpoints gated by `get_current_active_admin` dependency |
| TYPE-02 | User can assign a type to a document at creation or edit time | Nullable `document_type_id` FK on `Document`; `TypeSelector` dropdown in upload and edit forms; `DocumentUpload`/`DocumentUpdate` schemas extended |
| TYPE-03 | System validates document metadata against assigned type's JSON Schema on save, rejecting missing required fields with descriptive errors | `jsonschema.validate()` call in `document_service` on upload/update; `ValidationError` caught and converted to 422 with field-level detail |
| TYPE-04 | User can define a document type that inherits schema fields from a parent type | Self-referential `parent_type_id` FK on `DocumentType`; schema merging logic combines parent + child `properties` and `required` arrays at validation time |
| TYPE-05 | Frontend renders type-specific metadata form fields based on assigned type | `TypeMetadataForm` component reads JSON Schema `properties`, renders Input/Select/Checkbox per field type, shows inherited fields first with "(inherited)" label |
</phase_requirements>

## Standard Stack

### Core (New)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| jsonschema | 4.26.0 | Validate arbitrary user-defined JSON Schemas at runtime | Pydantic validates fixed schemas at compile time; jsonschema validates dynamic schemas defined by admins. The standard Python library for JSON Schema validation (4M+ weekly PyPI downloads). |

### Existing (No Changes)
| Library | Version | Purpose |
|---------|---------|---------|
| FastAPI | 0.135.x | HTTP API framework |
| SQLAlchemy | 2.0.x | Async ORM with `Mapped` type annotations |
| Alembic | 1.18.x | Database migrations |
| Pydantic | 2.12.x | Request/response validation |
| React | 19.x | Frontend UI |
| @tanstack/react-query | 5.96.x | Server state / data fetching |
| @tanstack/react-table | 8.21.x | Table component logic |
| shadcn/ui (Radix) | v4 | UI components (Dialog, Select, Input, Textarea, Table, Badge, etc.) |
| sonner | 2.0.x | Toast notifications |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| jsonschema | fastjsonschema | 10x faster but no format validators, less community support, doesn't handle `$ref` |
| jsonschema | Pydantic dynamic models | Pydantic is designed for fixed schemas; creating dynamic models from user JSON is hacky and fragile |
| JSON textarea | Monaco Editor | Heavy dependency (~2MB) for a simple JSON editing need; monospace textarea is sufficient for MVP |

**Installation:**
```bash
pip install jsonschema==4.26.0
```

Also update `pyproject.toml` dependencies list to include `"jsonschema>=4.26,<5"`.

## Architecture Patterns

### Backend: New Files
```
src/app/
  models/
    document_type.py          # DocumentType SQLAlchemy model
  schemas/
    document_type.py          # Pydantic request/response schemas
  services/
    document_type_service.py  # CRUD + schema merging + validation logic
  routers/
    document_types.py         # /document-types CRUD endpoints (admin-only)
```

### Backend: Modified Files
```
src/app/
  models/
    document.py               # Add document_type_id FK + relationship
    __init__.py               # Export DocumentType
  schemas/
    document.py               # Add document_type_id to Upload/Update/Response
  services/
    document_service.py       # Inject type validation into upload + update
  routers/
    documents.py              # Accept document_type_id in upload form data
  main.py                     # Register document_types router
```

### Frontend: New Files
```
frontend/src/
  pages/
    DocumentTypesPage.tsx              # /admin/types page
  components/
    admin/
      DocumentTypeTable.tsx            # Type list table
      CreateTypeDialog.tsx             # Create type modal
      EditTypeDialog.tsx               # Edit type modal (includes delete)
      SchemaEditor.tsx                 # JSON textarea with error display
    documents/
      TypeSelector.tsx                 # Type dropdown for document forms
      TypeMetadataForm.tsx             # Dynamic form from JSON Schema
      TypeBadge.tsx                    # Type name badge for table cells
  api/
    documentTypes.ts                   # API client for /document-types
```

### Frontend: Modified Files
```
frontend/src/
  App.tsx                              # Add /admin/types route
  components/
    layout/SidebarNav.tsx              # Add Types nav item (admin section)
    documents/DocumentTable.tsx        # Add Type column
    documents/DocumentDetailPanel.tsx  # Add Doc Type metadata row
    documents/DocumentDropZone.tsx     # Accept optional documentTypeId
  api/
    documents.ts                       # Add document_type_id to types and upload fn
```

### Pattern 1: DocumentType Model
**What:** SQLAlchemy model extending BaseModel with self-referential FK
**When to use:** Any entity needing hierarchical type definitions
```python
# src/app/models/document_type.py
import uuid
from sqlalchemy import ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class DocumentType(BaseModel):
    __tablename__ = "document_types"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    parent_type_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("document_types.id"), nullable=True
    )

    parent_type: Mapped["DocumentType | None"] = relationship(
        remote_side="DocumentType.id",
        lazy="selectin",
    )
```

### Pattern 2: Schema Merging (Parent + Child)
**What:** Merge parent and child JSON Schemas for validation
**When to use:** When validating a document whose type has a parent
```python
def merge_schemas(parent_schema: dict, child_schema: dict) -> dict:
    """Merge parent + child JSON Schemas. Child properties override parent."""
    merged = {
        "type": "object",
        "properties": {
            **parent_schema.get("properties", {}),
            **child_schema.get("properties", {}),
        },
        "required": list(set(
            parent_schema.get("required", []) +
            child_schema.get("required", [])
        )),
    }
    return merged
```

### Pattern 3: Validation at Service Layer
**What:** Validate custom_properties against type schema before persisting
**When to use:** In `upload_document` and `update_document_metadata`
```python
import jsonschema

async def validate_document_metadata(
    db: AsyncSession,
    document_type_id: uuid.UUID | None,
    custom_properties: dict,
) -> None:
    """Validate custom_properties against the document type schema. Raises HTTPException on failure."""
    if document_type_id is None:
        return  # Untyped documents skip validation

    doc_type = await get_document_type(db, document_type_id)
    schema = doc_type.metadata_schema

    if doc_type.parent_type_id and doc_type.parent_type:
        schema = merge_schemas(doc_type.parent_type.metadata_schema, schema)

    try:
        jsonschema.validate(instance=custom_properties, schema=schema)
    except jsonschema.ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Metadata validation failed",
                "field": ".".join(str(p) for p in e.absolute_path) or e.json_path,
                "error": e.message,
            },
        )
```

### Pattern 4: Dynamic Form Field Rendering (Frontend)
**What:** React component that reads JSON Schema and renders appropriate form controls
**When to use:** TypeMetadataForm on document upload/edit
```typescript
// Mapping JSON Schema types to form controls
function renderField(key: string, prop: SchemaProperty, value: unknown, onChange: (v: unknown) => void) {
  if (prop.enum) {
    return <Select value={value} onValueChange={onChange}>...</Select>;
  }
  switch (prop.type) {
    case "string":
      if (prop.format === "date") return <Input type="date" .../>;
      return <Input type="text" .../>;
    case "number":
      return <Input type="number" .../>;
    case "boolean":
      return <Checkbox checked={!!value} onCheckedChange={onChange} />;
    default:
      return <Input type="text" .../>;
  }
}
```

### Anti-Patterns to Avoid
- **Adding required fields without defaults to existing type schemas:** This breaks existing documents on next edit. The service layer should warn (or block) when a schema update adds a new required field without a default value.
- **Frontend-only validation:** All validation MUST happen at the API layer. Frontend validation is purely for UX -- it is not a security boundary.
- **Deep inheritance chains:** The decision caps inheritance at 1 level (parent -> child). Do NOT allow grandchild types. Enforce in the create/update endpoint by checking the candidate parent has no parent itself.
- **Validating on read:** Never validate existing documents against their type schema when fetching. Only validate on write (upload, update).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Schema validation | Custom property-by-property validator | `jsonschema.validate()` | Handles required, type coercion, format validators, nested objects, `$ref`, pattern, min/max -- dozens of edge cases |
| JSON syntax checking | Regex or custom parser | `json.loads()` in Python, `JSON.parse()` in JS | Standard library, handles all edge cases |
| UUID generation | Custom ID schemes | `uuid.uuid4()` via BaseModel | Consistent with all 26 existing models |
| Toast notifications | Custom notification system | `sonner` (already installed) | Already used throughout the frontend |
| Form state management | Custom state tracking | React `useState` + controlled inputs | The form is simple enough; no need for react-hook-form for 5-10 dynamic fields |

**Key insight:** The `jsonschema` library is the critical "don't hand-roll" item. JSON Schema validation has dozens of edge cases (required vs optional, type coercion, enum matching, format validators, nested objects, pattern matching). Rolling a custom validator would miss at least half of these.

## Common Pitfalls

### Pitfall 1: Schema Evolution Breaks Existing Documents
**What goes wrong:** Admin adds a new required field to a type schema. All existing documents of that type fail validation on their next edit, even though the user only changed the title.
**Why it happens:** The validation runs on the full `custom_properties` dict, not just the changed fields.
**How to avoid:** Validate on write only (never on read). When updating a document, validate the entire `custom_properties` dict that will be saved. If the user did not supply `custom_properties` in the update request, do NOT validate -- only validate when the user explicitly provides metadata. Consider blocking required-without-default field additions at the type schema update endpoint.
**Warning signs:** Users report they cannot edit documents after an admin changes a type schema.

### Pitfall 2: Circular or Deep Inheritance
**What goes wrong:** A type is set as its own parent, or a chain of parent->child->grandchild is created, causing infinite loops or unexpected schema merging.
**Why it happens:** Missing validation on the `parent_type_id` field during create/update.
**How to avoid:** On create/update, verify: (1) `parent_type_id` is not the type's own ID, (2) the candidate parent has `parent_type_id IS NULL` (no grandparents allowed), (3) no existing child types point to this type as parent if we are setting a parent on it.
**Warning signs:** Stack overflow on schema merge, or unexpected validation errors from grandparent schema fields.

### Pitfall 3: Upload Endpoint Uses Form Data, Not JSON
**What goes wrong:** Developer sends `document_type_id` as a JSON body field, but the upload endpoint uses `Form()` parameters because it also accepts a file upload via multipart.
**Why it happens:** The existing `POST /documents/` uses `Form(...)` for `title`, `author`, and `custom_properties` (as a JSON string in form data). Adding `document_type_id` must follow the same pattern.
**How to avoid:** Add `document_type_id: str | None = Form(None)` to the upload endpoint signature. Parse it as UUID in the handler. This matches the existing pattern where `custom_properties` is sent as a JSON string in form data.
**Warning signs:** 422 errors on upload when sending document_type_id, or the field silently being ignored.

### Pitfall 4: Frontend Has No Document Edit Form Yet
**What goes wrong:** Planner assumes there is an existing document metadata edit form to add the TypeSelector to, but the frontend currently has NO edit form -- only the detail panel (read-only) and the upload drop zone.
**Why it happens:** The `PUT /documents/{id}` endpoint exists on the backend but has no frontend consumer.
**How to avoid:** Phase 27 must create a minimal document metadata edit capability in the frontend (either inline editing in the detail panel, or a dedicated edit dialog) so the TypeSelector and TypeMetadataForm have somewhere to render for existing documents. This is necessary to satisfy TYPE-02 ("assign a type at edit time").
**Warning signs:** TYPE-02 requirement cannot be demonstrated because there is no way to edit a document's type after upload.

### Pitfall 5: SQLite Test DB Does Not Support JSON Operators
**What goes wrong:** Tests pass locally but queries using PostgreSQL-specific JSON operators fail in the test suite because tests use SQLite in-memory.
**Why it happens:** The test conftest uses `sqlite+aiosqlite:///:memory:`. SQLite has limited JSON support compared to PostgreSQL.
**How to avoid:** The `jsonschema` validation happens in Python code (not in SQL queries), so this is largely safe. However, if any new queries use PostgreSQL JSONB operators, they will need SQLite-compatible alternatives in tests. Keep validation in Python, not in DB triggers.
**Warning signs:** Tests fail with `OperationalError` on JSON-related queries.

## Code Examples

### Backend: DocumentType Pydantic Schemas
```python
# src/app/schemas/document_type.py
import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class DocumentTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    metadata_schema: dict[str, Any] = Field(default_factory=dict)
    parent_type_id: uuid.UUID | None = None

class DocumentTypeUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    metadata_schema: dict[str, Any] | None = None
    parent_type_id: uuid.UUID | None = None  # Set to None to remove parent

class DocumentTypeResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    metadata_schema: dict[str, Any]
    parent_type_id: uuid.UUID | None
    parent_type_name: str | None = None  # Computed from relationship
    field_count: int = 0  # Computed from schema properties
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### Backend: Router Pattern (Admin-Only CRUD)
```python
# src/app/routers/document_types.py
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_active_admin

router = APIRouter(prefix="/document-types", tags=["document-types"])

@router.post("/", status_code=201)
async def create_document_type(
    data: DocumentTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),  # Admin gate
):
    ...

@router.get("/")
async def list_document_types(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  # Any authenticated user can read
):
    ...
```

### Backend: Extending Document Upload for Type
```python
# In routers/documents.py, modify upload_document:
@router.post("/", ...)
async def upload_document(
    file: UploadFile,
    title: str = Form(...),
    author: str | None = Form(None),
    custom_properties: str | None = Form(None),
    document_type_id: str | None = Form(None),  # NEW
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    props = json.loads(custom_properties) if custom_properties else None
    type_id = uuid.UUID(document_type_id) if document_type_id else None

    # Validate metadata against type schema BEFORE creating document
    if type_id and props:
        await document_type_service.validate_metadata(db, type_id, props or {})

    document = await document_service.upload_document(
        db, file=file, title=title, author=author,
        custom_properties=props, document_type_id=type_id,
        user_id=str(current_user.id),
    )
```

### Frontend: API Client Pattern
```typescript
// src/api/documentTypes.ts -- follows existing apiFetch/apiMutate pattern from documents.ts
export interface DocumentTypeResponse {
  id: string;
  name: string;
  description: string | null;
  metadata_schema: Record<string, unknown>;
  parent_type_id: string | null;
  parent_type_name: string | null;
  field_count: number;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export async function fetchDocumentTypes(): Promise<DocumentTypeResponse[]> {
  const res = await apiFetch<{ data: DocumentTypeResponse[] }>("/api/v1/document-types/");
  return res.data;
}

export async function createDocumentType(data: DocumentTypeCreate): Promise<DocumentTypeResponse> {
  const res = await apiMutate<{ data: DocumentTypeResponse }>("/api/v1/document-types/", "POST", data);
  return res.data;
}
```

### Alembic Migration Pattern
```python
# alembic/versions/phase27_001_document_types.py
def upgrade():
    op.create_table(
        "document_types",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_schema", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("parent_type_id", sa.Uuid(), sa.ForeignKey("document_types.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("documents", sa.Column("document_type_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_documents_document_type_id",
        "documents", "document_types",
        ["document_type_id"], ["id"],
    )

def downgrade():
    op.drop_constraint("fk_documents_document_type_id", "documents")
    op.drop_column("documents", "document_type_id")
    op.drop_table("document_types")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| jsonschema v3 | jsonschema v4 (4.26.0) | 2022 | v4 introduced referencing library for `$ref` resolution; API is largely the same for basic validation |
| `jsonschema.Draft7Validator` | `jsonschema.Draft202012Validator` | 2022 | Default validator in v4 uses Draft 2020-12; for this project Draft 7 is sufficient and more widely documented |

**Note:** Use `jsonschema.Draft7Validator` explicitly rather than the default Draft 2020-12 validator. Draft 7 is simpler, better documented, and covers all the field types we need (string, number, boolean, enum, format). There is no benefit to using a newer draft for this use case.

## Open Questions

1. **Document metadata edit UI for existing documents**
   - What we know: The backend `PUT /documents/{id}` endpoint exists and supports updating `custom_properties`, but the frontend has NO edit form for document metadata.
   - What's unclear: Should we add inline editing in DocumentDetailPanel, or a separate EditDocumentDialog?
   - Recommendation: Add an "Edit Metadata" button in DocumentDetailPanel that opens a dialog with TypeSelector + TypeMetadataForm + standard fields. This is the simplest path to satisfy TYPE-02 for existing documents.

2. **jsonschema validation error format for multiple errors**
   - What we know: `jsonschema.validate()` raises on the first error only. To collect ALL errors, use `Draft7Validator(schema).iter_errors(instance)`.
   - What's unclear: Should we return all errors at once, or just the first?
   - Recommendation: Use `iter_errors()` to collect all field-level errors and return them as an array in the 422 response. Better UX -- user can fix all errors at once.

3. **Document count per type for the admin table**
   - What we know: The UI spec shows "Documents" column in the type table with a count.
   - What's unclear: Should this be a live count query or a denormalized counter?
   - Recommendation: Live `COUNT(*)` query via a subquery join when listing types. With expected type counts (<100 types, <10K documents), this is fast enough. No need for denormalization.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_document_types.py -x` |
| Full suite command | `pytest tests/ -x --timeout=60` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TYPE-01 | Admin creates document type with name + JSON Schema | integration | `pytest tests/test_document_types.py::test_create_type -x` | Wave 0 |
| TYPE-01 | Non-admin cannot create type (403) | integration | `pytest tests/test_document_types.py::test_create_type_non_admin -x` | Wave 0 |
| TYPE-02 | Assign type to document at upload time | integration | `pytest tests/test_document_types.py::test_upload_with_type -x` | Wave 0 |
| TYPE-02 | Change type on existing document via update | integration | `pytest tests/test_document_types.py::test_update_document_type -x` | Wave 0 |
| TYPE-03 | Metadata validation rejects missing required field | integration | `pytest tests/test_document_types.py::test_validation_rejects_missing_required -x` | Wave 0 |
| TYPE-03 | Metadata validation passes with valid properties | integration | `pytest tests/test_document_types.py::test_validation_passes_valid_metadata -x` | Wave 0 |
| TYPE-03 | Untyped document skips validation | integration | `pytest tests/test_document_types.py::test_untyped_skips_validation -x` | Wave 0 |
| TYPE-04 | Child type validates against merged parent+child schema | integration | `pytest tests/test_document_types.py::test_child_type_inherits_parent -x` | Wave 0 |
| TYPE-04 | Cannot create grandchild type (depth > 1 blocked) | integration | `pytest tests/test_document_types.py::test_no_grandchild_types -x` | Wave 0 |
| TYPE-05 | Frontend renders type fields | manual-only | Manual: open upload form, select type, verify fields render | N/A |

### Sampling Rate
- **Per task commit:** `pytest tests/test_document_types.py -x`
- **Per wave merge:** `pytest tests/ -x --timeout=60`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_document_types.py` -- covers TYPE-01 through TYPE-04 (all backend requirements)
- [ ] No new conftest fixtures needed -- existing `admin_user`, `admin_token`, `regular_user`, `regular_token`, `async_client` fixtures are sufficient

## Project Constraints (from CLAUDE.md)

- **Tech stack:** FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Alembic
- **Frontend:** React 19 + TypeScript + Vite + shadcn/ui + TanStack Query/Table + Zustand
- **Testing:** pytest + pytest-asyncio + httpx AsyncClient with aiosqlite in-memory DB
- **Auth:** JWT via `python-jose` / `PyJWT`, admin gating via `get_current_active_admin` dependency
- **API pattern:** `EnvelopeResponse[T]` wrapper with optional `PaginationMeta`
- **GSD workflow:** All work through GSD commands; no direct repo edits outside GSD workflow

## Sources

### Primary (HIGH confidence)
- Codebase analysis: all model, service, router, schema, and frontend files examined directly -- patterns are consistent across 26 phases
- PyPI registry: `jsonschema` 4.26.0 confirmed as latest stable (verified via `pip index versions`)
- npm registry: all frontend dependencies verified installed via `package.json`

### Secondary (MEDIUM confidence)
- jsonschema library documentation (training data, verified against PyPI version) -- `validate()`, `Draft7Validator`, `iter_errors()` API

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - single new dependency (jsonschema), all else existing
- Architecture: HIGH - follows exact patterns from 26 prior phases, all integration points examined
- Pitfalls: HIGH - based on direct codebase analysis (found missing edit form, identified Form data pattern, verified SQLite test DB)

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable domain, no fast-moving dependencies)
