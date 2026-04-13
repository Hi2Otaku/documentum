# Phase 27: Document Type System - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 27 delivers the Document Type System: a mechanism for defining named document types with JSON Schema metadata definitions, assigning types to documents, validating metadata on save, supporting one-level type inheritance, and rendering type-specific form fields in the frontend.

This phase adds:
- `document_types` table with JSON Schema field definitions and optional parent type
- `document_type_id` FK on the `Document` model
- API-level validation of `custom_properties` against the assigned type's schema on every save
- `/admin/types` page for creating and managing document types
- Dynamic metadata form section in document upload/edit forms, driven by the assigned type

Out of scope: folder/filing, search, ACL changes, migration of existing documents to types.

</domain>

<decisions>
## Implementation Decisions

### Type Definition Storage & Inheritance
- Separate `document_types` DB table — clean FK, queryable, reuses existing `BaseModel` mixin
- `parent_type_id` FK on `document_types` — schema merged at read time (child fields + parent fields)
- Max 1 level of inheritance (parent → child only) — matches Documentum practical limit
- Admin users only can create/edit types — role-based gate on the API endpoint

### Schema Validation Behavior
- Validate on document save at API level — single enforcement point, no frontend-only validation
- Reject save on validation failure with descriptive field-level error messages
- No retroactive validation — schema changes only affect new saves, existing documents unaffected
- Type is optional — documents with no type skip validation entirely (no forced "Generic" type)

### Type Admin UI
- Dedicated `/admin/types` page in the existing admin/settings area
- JSON editor (textarea with syntax highlighting) for schema field definitions — developer-friendly
- Supported field types: string, number, boolean, date, enum (select) — standard JSON Schema primitives
- Type list displayed as a table: name, field count, document count, parent type column

### Document Form Integration
- Type selection dropdown added to both upload form and document edit form, before metadata fields
- Type-specific fields render as a dynamic section appended below standard fields (not replacing them)
- Type can be changed after upload, with a warning if existing metadata won't match the new schema
- Untyped documents show "—" in the type column — untyped is a valid state, not an error

### Claude's Discretion
- Exact JSON Schema subset to support (beyond the 5 primitive types listed)
- Whether to show a schema preview/sample document in the type admin page
- Ordering of type-specific fields in the rendered form

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseModel` mixin (id UUID, created_at, updated_at, created_by, is_deleted) — use for `DocumentType`
- `Document` model in `src/app/models/document.py` — add `document_type_id` nullable FK
- `DocumentResponse` Pydantic schema — extend with `document_type_id` and `document_type_name`
- `DocumentUpload` / `DocumentUpdate` Pydantic schemas — add `document_type_id` field
- Existing admin/settings routing patterns in the frontend for the `/admin/types` page

### Established Patterns
- SQLAlchemy 2.0 async ORM with `Mapped` type annotations — follow for `DocumentType` model
- FastAPI router pattern: `src/app/routers/` — create `src/app/routers/document_types.py`
- Pydantic v2 schemas in `src/app/schemas/` — create `src/app/schemas/document_type.py`
- `custom_properties` stored as JSON — validated against type schema at API layer using `jsonschema`

### Integration Points
- `src/app/routers/documents.py` — inject type validation into upload and update handlers
- `src/app/main.py` (or router registry) — mount the new `document_types` router
- Frontend `DocumentsPage.tsx` — add type column to document table
- Frontend document upload/edit form — add type dropdown + dynamic field section

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond what was captured in decisions — open to standard approaches for the JSON Schema editor and field rendering.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
