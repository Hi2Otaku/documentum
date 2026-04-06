# Phase 21: Virtual Documents - Research

**Conducted:** 2026-04-06
**Method:** Inline codebase exploration (Level 0 -- all patterns established)

## Discovery Level: 0 (Skip)

All work follows established codebase patterns:
- SQLAlchemy model pattern (BaseModel, enums, relationships) -- used in 10+ models
- Service layer pattern (document_service, rendition_service) -- established
- Router pattern (APIRouter + Depends + EnvelopeResponse) -- used in all 16 routers
- Alembic migration pattern (phase-prefixed revisions) -- used in 11 migrations
- Frontend API client pattern (apiFetch/apiMutate + authHeaders) -- established in documents.ts
- Frontend component pattern (shadcn/ui + TanStack Query) -- established in documents/
- Celery task pattern (for PDF merge async task) -- established in rendition tasks

No new external dependencies needed except PyPDF2/pypdf for PDF merging (standard Python PDF library).

## Codebase Patterns Discovered

### Backend Model Pattern
- All models extend `BaseModel` (id, created_at, updated_at, created_by, is_deleted)
- UUIDs for PKs, ForeignKey references via `Uuid()` + `ForeignKey()`
- Enums defined in `enums.py`, registered in `__init__.py`
- Relationships via `Mapped[list[...]]` with `relationship()` + `back_populates`

### Service Layer Pattern
- Pure async functions accepting `(db: AsyncSession, ...)` 
- HTTPException raised for 404/400/409 errors
- Audit records created via `create_audit_record()`
- MinIO operations via `upload_object`/`download_object` from `app.core.minio_client`

### Router Pattern
- `APIRouter(prefix="/resource", tags=["resource"])`
- `EnvelopeResponse[T]` wrapping, `Depends(get_current_user)` auth
- Router registered in `main.py` with `application.include_router(router, prefix=settings.api_v1_prefix)`

### Frontend Pattern
- API client in `frontend/src/api/{resource}.ts` with `apiFetch`/`apiMutate` helpers
- Components in `frontend/src/components/{resource}/`
- Pages in `frontend/src/pages/` with `useQuery` for data fetching
- Routes in `App.tsx` under `<ProtectedRoute>` + `<AppShell>`

### Celery Task Pattern
- Tasks in `src/app/tasks/{name}.py`
- Registered in `celery_app.py` include list
- Async DB operations via `asyncio.run()` inside sync Celery tasks
- MinIO download/upload within task body

## Virtual Document Design

### Data Model
- `VirtualDocument` model: FK to `documents.id` (parent document), with `is_virtual` flag on Document or separate table
- `VirtualDocumentChild` model: FK to virtual_document, FK to child document, `order_index` integer, unique constraint on (virtual_doc_id, child_document_id)
- Approach: Separate `virtual_documents` table linking parent_document_id -> child relationships, rather than adding columns to Document model. Cleaner separation.

### Circular Reference Detection
- On add-child: walk ancestors of the virtual document to ensure the child (or any of its descendants if it is also virtual) does not contain the parent. Simple recursive CTE query or iterative check.
- Depth limit: Since VDOC-05 (nested virtual docs) is deferred, we only support depth=1 (virtual doc contains regular docs, not other virtual docs). This simplifies cycle detection to: "child cannot be the parent itself."
- Actually, even at depth=1, we should still prevent: A contains B, B contains A. So check both directions.

### PDF Merge
- Use `pypdf` (successor to PyPDF2) to merge PDFs
- For each child document, fetch its PDF rendition (from Phase 20 rendition system)
- If a child has no PDF rendition ready, skip or fail with clear message
- Celery task for async merge, store result in MinIO, return download URL

### API Endpoints
- `POST /virtual-documents` -- create a virtual document (creates a Document + VirtualDocument record)
- `GET /virtual-documents/{id}` -- get virtual document with children list
- `POST /virtual-documents/{id}/children` -- add a child document
- `PUT /virtual-documents/{id}/children` -- reorder children (batch update)
- `DELETE /virtual-documents/{id}/children/{child_id}` -- remove a child
- `POST /virtual-documents/{id}/merge-pdf` -- trigger PDF merge, return merged file

## Dependencies

- `pypdf` -- for PDF merging (pure Python, no external binary needed)
- All other dependencies already in the project

## Key Decision

Using a separate `virtual_documents` + `virtual_document_children` table approach rather than adding an `is_virtual` column to the Document table. This keeps the Document model clean and makes the virtual document concept a distinct entity with its own relationships.
