# Documentum Workflow Clone

A full-featured clone of [OpenText Documentum](https://www.opentext.com/products/documentum) — the enterprise content management (ECM) and workflow platform — built with Python, FastAPI, and React.

Four milestones shipped covering the complete Documentum feature set: workflow engine, frontend, advanced engine features, and document-centric ECM.

## Screenshots

| Browse | Search | Workflow Designer |
|--------|--------|-------------------|
| Three-panel document browser with folder tree, content grid, and detail panel | Full-text search with highlighted snippets and filter sidebar | Visual drag-and-drop workflow designer with React Flow |

## Features

### Document Management
- **Upload & Versioning** — Major/minor versioning with check-in/check-out locking
- **Document Types** — Custom types with JSON Schema metadata validation and type inheritance
- **Lifecycle States** — Draft, Review, Approved, Archived with workflow-driven transitions
- **Relationships** — Typed directional links between documents (supersedes, references, related_to)
- **Full-Text Search** — PostgreSQL FTS with content extraction from PDF/Word, prefix and substring matching, highlighted snippets
- **Saved Searches & Smart Folders** — Persistent queries that appear as virtual folder nodes

### Folder & Permission Management
- **Cabinet/Folder Hierarchy** — Navigable tree with create, move, copy, rename, delete
- **Document Filing** — File documents into multiple folders (multi-filing)
- **Folder ACL Inheritance** — Permissions assigned to folders propagate to all contained documents
- **Per-Document ACL** — Direct user/group permission grants with hierarchy (Read < Write < Delete < Admin)

### Workflow Engine
- **Visual Designer** — Drag-and-drop canvas (React Flow) for designing workflow templates
- **Activity Types** — Start, End, Manual, Auto, Sub-Workflow, Event-driven
- **Routing** — Sequential, parallel (AND-split/join), conditional (expression-based), performer-chosen
- **Performer Assignment** — Supervisor, specific user, group, sequential performers, runtime selection
- **Reject Flows** — Loop back to previous activities for rework
- **Alias Sets** — Map abstract roles to users without editing templates
- **Lifecycle Integration** — Activities trigger document state transitions on completion
- **Sub-Workflows** — Nest workflows within workflows with variable mapping
- **Event Activities** — Activities that trigger on domain events

### Infrastructure
- **User Inbox** — Work items with acquire/complete/reject, comments, due dates
- **Delegation** — Users can delegate work to others when unavailable
- **Work Queues** — Shared task pools for group-based work distribution
- **BAM Dashboard** — Business activity monitoring with workflow metrics
- **Audit Trail** — Append-only log of every mutation with before/after state
- **Notifications** — In-app notification system for workflow events
- **Renditions** — Async PDF/thumbnail generation via Celery workers
- **Retention Policies** — Configurable document retention rules
- **Digital Signatures** — Document signing with hash verification

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI + Uvicorn (Python 3.12+, async) |
| **Frontend** | React 19 + TypeScript + Vite |
| **UI Components** | shadcn/ui + Tailwind CSS |
| **Workflow Designer** | React Flow (@xyflow/react) |
| **State Management** | TanStack Query (server) + Zustand (client) |
| **Database** | PostgreSQL 16 + SQLAlchemy 2.0 (async via asyncpg) |
| **Migrations** | Alembic |
| **File Storage** | MinIO (S3-compatible object storage) |
| **Task Queue** | Celery + Redis |
| **Search** | PostgreSQL Full-Text Search (tsvector/tsquery + GIN index) |
| **Auth** | JWT (PyJWT + bcrypt) |
| **Testing** | pytest (357 tests) + Vitest |

## Quick Start

```bash
# Start all services
docker compose up -d

# Run database migrations
docker compose exec api alembic upgrade head

# Seed demo data (users, folders, documents, workflow, permissions)
bash seed_demo.sh

# Start frontend dev server
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173** in your browser.

### Default Accounts

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin` | Superuser (full access) |
| `john.legal` | `demo1234` | Legal reviewer (Legal Dept access) |
| `sarah.finance` | `demo1234` | Finance reviewer (Finance Dept access) |
| `mike.director` | `demo1234` | Director (Legal + Finance access) |

### URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |

## Demo Walkthrough

### 1. Browse Documents
Go to `/browse` (default landing page). Click cabinets in the repository view to drill into folders, then click documents to see detail panels with metadata, lifecycle state, and relationships.

### 2. Search
Go to `/search`. Type any keyword — results appear with highlighted snippets. Filter by folder, document type, or lifecycle state. Save a search and mark it as a Smart Folder to see it in the browse tree.

### 3. Workflow
Login as `john.legal`. Check the **Inbox** for a "Legal Review" work item. Acquire and complete it. The attached document transitions from Draft to Review. Then `sarah.finance` gets the Financial Review, and `mike.director` gets the Director Approval — the document becomes Approved.

### 4. ACL Inheritance
Login as `john.legal` — only Legal Department and HR (open access) folders are visible. Finance Department is hidden because john.legal has no permission. The "Inherited from Legal Department" badge appears on documents accessed through folder ACL.

### 5. Design a Workflow
Go to **Workflows** > create a new template > **Design**. Drag activities from the palette, connect them with flows, assign performers via username dropdown, and set lifecycle actions to automate document state transitions.

## Project Structure

```
src/app/
  core/           Config, database, auth dependencies, MinIO client
  models/         SQLAlchemy models (document, workflow, ACL, audit, folder, etc.)
  schemas/        Pydantic request/response schemas
  services/       Business logic (engine, search, lifecycle, ACL, etc.)
  routers/        FastAPI route handlers (25 routers)
  tasks/          Celery tasks (extraction, renditions, auto activities)

frontend/src/
  pages/          BrowsePage, SearchPage, InboxPage, DesignerPage, etc.
  components/     UI components organized by domain
  api/            API client functions with query key factories
  stores/         Zustand stores (auth, designer)
  hooks/          Custom hooks (save template, keyboard shortcuts)

tests/            357 pytest tests (SQLite in-memory, no Docker needed)
alembic/          Database migrations
```

## API Overview

All endpoints documented at `/docs` (Swagger UI).

| Area | Key Endpoints |
|------|---------------|
| Auth | `POST /auth/login` |
| Users/Groups | `/users/`, `/groups/`, `/roles/` |
| Documents | `/documents/` — upload, versioning, check-in/out, metadata |
| Folders | `/folders/` — tree, CRUD, filing, ACL management |
| Search | `/search/` — full-text search with filters |
| Templates | `/templates/` — design, validate, install workflows |
| Workflows | `/workflows/` — start, halt, resume instances |
| Inbox | `/inbox/` — work items, acquire, complete, reject |
| Relationships | `/documents/{id}/relationships` — typed document links |
| Saved Searches | `/saved-searches/` — persistent queries, smart folders |
| Lifecycle | `/documents/{id}/lifecycle` — state transitions |
| Dashboard | `/dashboard/` — workflow metrics |

## Development

```bash
# Run tests (uses SQLite in-memory, no Docker needed)
cd src && python -m pytest tests/ -q

# Type check frontend
cd frontend && npx tsc --noEmit

# Lint
ruff check src/ tests/
```

## Milestones

| Version | Name | Phases | Shipped |
|---------|------|--------|---------|
| **v1.0** | Core Engine | 1-11 | 2026-03-30 |
| **v1.1** | Full Frontend | 12-15 | 2026-04-06 |
| **v1.2** | Advanced Engine | 16-26 | 2026-04-13 |
| **v1.3** | Document-Centric ECM | 27-33 | 2026-04-14 |

Total: **33 phases**, **96 plans**, **357 tests**, built with [Claude Code](https://claude.ai/claude-code).

## License

MIT
