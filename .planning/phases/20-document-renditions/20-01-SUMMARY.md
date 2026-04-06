---
phase: "20"
plan: "01"
name: "Rendition Model, Celery Tasks, and API"
subsystem: document-renditions
tags: [renditions, celery, pdf, thumbnail, minio]
dependency_graph:
  requires: [document-management, celery-workers, minio-storage]
  provides: [rendition-model, rendition-api, rendition-celery-tasks]
  affects: [document-upload, document-checkin]
tech_stack:
  added: [Pillow, LibreOffice-headless]
  patterns: [celery-async-task, minio-rendition-storage, auto-trigger-on-upload]
key_files:
  created:
    - src/app/models/rendition.py
    - src/app/tasks/rendition.py
    - src/app/services/rendition_service.py
    - src/app/schemas/rendition.py
    - src/app/routers/renditions.py
    - alembic/versions/phase20_001_renditions.py
  modified:
    - src/app/models/enums.py
    - src/app/models/__init__.py
    - src/app/models/document.py
    - src/app/celery_app.py
    - src/app/main.py
    - src/app/services/document_service.py
decisions:
  - "Rendition failures do not block document upload/checkin -- logged as warnings"
  - "LibreOffice headless for Office-to-PDF conversion, direct copy for already-PDF"
  - "Pillow for image thumbnails only; non-image types fail with descriptive message"
  - "Renditions stored under renditions/{doc_id}/{version_id}/ path in MinIO"
metrics:
  duration: "4m"
  completed: "2026-04-06"
  tasks: 4
  files_created: 6
  files_modified: 6
---

# Phase 20 Plan 01: Rendition Model, Celery Tasks, and API Summary

Rendition database model with PDF/thumbnail Celery workers, REST API for list/download/retry, and auto-trigger on document upload/checkin via LibreOffice headless and Pillow.

## What Was Built

### Rendition Model (Task 1)
- `Rendition` SQLAlchemy model with document_version FK, type (pdf/thumbnail), status lifecycle (pending -> processing -> ready/failed), MinIO object key, error tracking
- `RenditionType` and `RenditionStatus` enums added to enums.py
- `renditions` relationship added to `DocumentVersion` model
- Alembic migration `phase20_001` creates the renditions table with index

### Celery Rendition Tasks (Task 2)
- `generate_pdf_rendition` task: downloads source from MinIO, converts via LibreOffice headless (Office formats) or copies directly (already PDF), uploads result
- `generate_thumbnail` task: downloads image source, resizes to 256x256 via Pillow, uploads PNG
- Both tasks update Rendition status through PROCESSING -> READY/FAILED lifecycle
- Tasks registered in celery_app.py include list

### Rendition Service and API (Task 3)
- `rendition_service.py` with create, list, get, retry, download functions
- API endpoints:
  - `GET /documents/{id}/versions/{vid}/renditions` -- list renditions for a version
  - `GET /renditions/{id}` -- get single rendition status
  - `GET /renditions/{id}/download` -- download ready rendition content
  - `POST /renditions/{id}/retry` -- retry failed rendition
- Router registered in main.py

### Auto-trigger on Upload/Checkin (Task 4)
- `_trigger_renditions` helper in document_service dispatches both PDF and THUMBNAIL rendition requests
- Wired into `upload_document` and `checkin_document` flows
- Failures are caught and logged as warnings without blocking document operations

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 10e49e7 | Rendition model, enums, and Alembic migration |
| 2 | b5e5c7e | Celery tasks for PDF and thumbnail generation |
| 3 | 075fe76 | Rendition service, schemas, and API endpoints |
| 4 | d06ff82 | Auto-trigger renditions on upload and checkin |

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None. All rendition flows are fully wired: model -> service -> API -> Celery tasks -> MinIO storage. LibreOffice and Pillow are runtime dependencies that fail gracefully with descriptive error messages if not installed.

## Decisions Made

1. **Rendition failures non-blocking**: Document upload/checkin succeeds even if rendition queuing fails. Logged as warnings.
2. **LibreOffice for Office-to-PDF**: Supports DOCX, XLSX, PPTX, ODT, RTF, TXT, HTML, CSV. Already-PDF files are copied directly.
3. **Pillow for thumbnails only**: Only image/* MIME types get thumbnails. Non-image types fail with a clear message rather than producing a generic placeholder.
4. **MinIO path convention**: `renditions/{document_id}/{version_id}/rendition.pdf` and `thumbnail.png`.

## Self-Check: PASSED

- All 6 created files: FOUND
- All 4 commits: FOUND
