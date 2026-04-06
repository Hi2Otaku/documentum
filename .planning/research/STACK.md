# Technology Stack

**Project:** Documentum Workflow Clone v1.2
**Researched:** 2026-04-06

## Existing Stack (No Changes Needed)

The v1.0 stack is fully adequate for v1.2. No framework changes, no database migrations to a different engine, no new infrastructure services beyond what is listed below.

| Technology | Version | Purpose | Status in v1.2 |
|------------|---------|---------|----------------|
| FastAPI | 0.135.x | HTTP API | Unchanged |
| SQLAlchemy | 2.0.48 | ORM (async) | Unchanged |
| PostgreSQL | 16+ | Primary database | Unchanged |
| Redis | 7.x | Celery broker + pub/sub | Expanded role: event bus |
| Celery | 5.6.x | Task queue + Beat | +6 new Beat tasks |
| MinIO | latest | Object storage | +renditions bucket |
| React | 19.x | Frontend SPA | +notification components |
| Vite | 6.x | Build tool | Unchanged |

## New Dependencies for v1.2

### Backend - Python Packages

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| Jinja2 | 3.1.x | Email notification templates | Render HTML email bodies from templates. Already a FastAPI transitive dep (via Starlette), but use explicitly for notification templates. |
| Pillow | 11.x | Image processing for thumbnails | Generate thumbnail renditions from images and PDF first pages. Mature, well-maintained. |
| pdf2image | 1.17.x | PDF to image conversion | Convert PDF pages to images for thumbnail generation. Wraps poppler-utils. |
| cryptography | 44.x | Digital signatures (PKCS7/CMS) | Already a transitive dep via python-jose[cryptography]. Make explicit for direct CMS signing operations. |
| PyPDF | 5.x | PDF manipulation | Merge PDFs for virtual document assembly. Lightweight, pure Python. |

### System Dependencies (Docker)

| Package | Purpose | Where |
|---------|---------|-------|
| libreoffice-headless | Office doc to PDF conversion | Celery worker Docker image |
| poppler-utils | PDF rendering (used by pdf2image) | Celery worker Docker image |

### Frontend - No New Libraries

All v1.2 frontend features use existing libraries:
- Notifications UI: shadcn/ui components (already installed)
- Signature status display: existing badge/icon patterns
- Virtual document tree: can use existing React Flow or a simple tree component from shadcn/ui

## Updated Docker Compose Services

```yaml
# New or modified services for v1.2:

celery-worker:
  # MODIFIED: needs LibreOffice headless for renditions
  build:
    context: .
    dockerfile: Dockerfile.worker  # New Dockerfile with LibreOffice
  # ... existing config unchanged

# Optional: dedicated rendition worker (if LibreOffice makes the image too large)
celery-rendition-worker:
  build:
    context: .
    dockerfile: Dockerfile.rendition
  command: celery -A app.celery_app worker --loglevel=info -Q renditions
  # Same env as celery-worker
```

## Updated Celery Beat Schedule

```python
beat_schedule = {
    # Existing
    "poll-auto-activities": {"task": "...", "schedule": 10.0},
    "aggregate-dashboard-metrics": {"task": "...", "schedule": 300.0},

    # v1.2 additions
    "check-timer-deadlines": {"task": "app.tasks.timer_tasks.check_timer_deadlines", "schedule": 30.0},
    "poll-sub-workflows": {"task": "app.tasks.sub_workflow_tasks.poll_sub_workflows", "schedule": 10.0},
    "process-event-queue": {"task": "app.tasks.event_tasks.process_event_queue", "schedule": 5.0},
    "process-dispositions": {"task": "app.tasks.retention_tasks.process_dispositions", "schedule": 86400.0},
}
```

## Updated Settings (config.py)

```python
# Notification settings
notification_email_enabled: bool = True
notification_batch_size: int = 50

# Rendition settings
rendition_auto_generate: bool = True
rendition_thumbnail_size: str = "256x256"
rendition_max_file_size_mb: int = 100
libreoffice_path: str = "/usr/bin/soffice"

# Signature settings
signature_algorithm: str = "sha256"
signature_key_size: int = 2048

# Retention settings
retention_disposition_batch_size: int = 100
```

## Installation (v1.2 additions)

```bash
# Python packages (add to pyproject.toml)
pip install Jinja2 Pillow pdf2image cryptography PyPDF

# System packages (in Dockerfile.worker)
apt-get install -y libreoffice-headless poppler-utils
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Event bus | Redis pub/sub | RabbitMQ | Already have Redis. Adding RabbitMQ is unnecessary infrastructure complexity. |
| Event bus | Redis pub/sub | Redis Streams | Pub/sub is simpler for our scale. Streams add complexity for durability we may not need yet. Can migrate later. |
| PDF conversion | LibreOffice headless | Pandoc | Pandoc handles markup well but not Office formats (docx/xlsx/pptx). |
| PDF conversion | LibreOffice headless | Cloud API (CloudConvert) | Requires external dependency and API key. Self-hosted is sufficient. |
| Thumbnail gen | Pillow + pdf2image | ImageMagick | Pillow is pure Python, easier to install in Docker. ImageMagick has security history. |
| PDF merge | PyPDF | pdftk | PyPDF is pure Python, no system dependency. pdftk requires Java. |
| Signatures | cryptography (PKCS7) | python-pkcs11 (HSM) | HSM overkill for internal use. Can add HSM support later. |
| Email templates | Jinja2 | MJML | Jinja2 already available. MJML adds build step for email-specific responsive templates. |
| Notification delivery | Celery tasks | Dedicated notification service | No need for a separate service at our scale. Celery tasks suffice. |

## Sources

- Pillow: https://pillow.readthedocs.io/ -- HIGH confidence
- pdf2image: https://github.com/Belval/pdf2image -- HIGH confidence
- PyPDF: https://pypdf.readthedocs.io/ -- HIGH confidence
- cryptography PKCS7/CMS: https://cryptography.io/en/latest/hazmat/primitives/asymmetric/serialization/#pkcs7 -- HIGH confidence
- LibreOffice headless conversion: standard DevOps pattern -- HIGH confidence
- Redis pub/sub: https://redis.io/docs/latest/develop/interact/pubsub/ -- HIGH confidence
