# Documentum Workflow Clone

A near-complete clone of [OpenText Documentum's Workflow Management](https://www.opentext.com/products/documentum) system built in Python with FastAPI. It provides a general-purpose workflow engine that can model and execute arbitrary business processes — including document management with versioning, workflow template design, user inboxes, lifecycle management, and all routing/delegation mechanisms described in Documentum's architecture.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **API** | FastAPI + Uvicorn (async, OpenAPI docs) |
| **Database** | PostgreSQL 16 + SQLAlchemy 2.0 (async via asyncpg) |
| **Migrations** | Alembic |
| **File Storage** | MinIO (S3-compatible object storage) |
| **Task Queue** | Celery + Redis (background workers, beat scheduler) |
| **Auth** | JWT (PyJWT + bcrypt password hashing) |
| **Validation** | Pydantic v2 |
| **Testing** | pytest + pytest-asyncio + httpx (211 tests) |
| **Runtime** | Python 3.12+, Docker Compose |

## Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd documentum_clone

# Start all services (FastAPI, PostgreSQL, Redis, MinIO, Celery)
docker compose up

# API available at http://localhost:8000
# OpenAPI docs at http://localhost:8000/docs
# MinIO console at http://localhost:9001
```

Default credentials:
- **API admin**: `admin` / `admin`
- **MinIO console**: `minioadmin` / `minioadmin`
- **PostgreSQL**: `docuser` / `docpass`

## Local Development

```bash
# Install dependencies (using uv or pip)
uv sync
# or: pip install -e ".[dev]"

# Run tests (uses SQLite in-memory, no Docker needed)
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Lint and format
ruff check src/ tests/
ruff format src/ tests/
```

## Project Structure

```
src/app/
├── main.py                 # FastAPI application entry point
├── core/                   # Config, database, dependencies
├── models/                 # SQLAlchemy models
│   ├── user.py             # User, Group, Role, UserGroup
│   ├── document.py         # Document, DocumentVersion, metadata
│   ├── workflow.py         # Process, Activity, Flow, Package, WorkItem, ExecutionToken
│   ├── acl.py              # ACL, ACLEntry (object-level permissions)
│   ├── audit.py            # AuditLog (append-only mutation log)
│   └── enums.py            # All enums (states, types, triggers)
├── schemas/                # Pydantic request/response schemas
├── services/               # Business logic
│   ├── auth_service.py     # JWT authentication
│   ├── user_service.py     # User/group/role management
│   ├── document_service.py # Upload, versioning, check-in/out
│   ├── template_service.py # Workflow template CRUD, validation, versioning
│   ├── engine_service.py   # Process engine (start, advance, route)
│   ├── inbox_service.py    # Work item inbox, complete, reject, comment
│   ├── alias_service.py    # Alias set resolution for performers
│   ├── lifecycle_service.py# Document state machine (Draft→Approved→Archived)
│   ├── acl_service.py      # Object-level access control
│   ├── expression_evaluator.py # Routing condition evaluation
│   └── audit_service.py    # Audit trail logging
├── routers/                # HTTP route handlers
│   ├── auth.py             # Login, token refresh
│   ├── users.py            # User CRUD
│   ├── groups.py           # Group CRUD, membership
│   ├── roles.py            # Role CRUD
│   ├── documents.py        # Upload, download, versioning, check-in/out
│   ├── templates.py        # Template CRUD, validate, install
│   ├── workflows.py        # Start instance, advance, manage
│   ├── inbox.py            # Inbox list, complete, reject, comment
│   ├── aliases.py          # Alias set CRUD
│   ├── lifecycle.py        # Lifecycle state transitions
│   └── health.py           # Health check
└── middleware/             # Request middleware
tests/
├── conftest.py             # Shared fixtures (async DB, test client, auth)
├── test_auth.py            # Authentication tests
├── test_documents.py       # Document management tests
├── test_templates.py       # Template design/validation tests
├── test_workflows.py       # Workflow execution tests
├── test_inbox.py           # Inbox/work item tests
├── test_routing.py         # Parallel/conditional routing tests
├── test_reject_flows.py    # Reject flow tests
├── test_sequential.py      # Sequential performer tests
├── test_aliases.py         # Alias set tests
├── test_lifecycle.py       # Document lifecycle tests
├── test_acl.py             # ACL permission tests
└── ...                     # 211 tests total
```

## What's Built (Phases 1–7)

### Phase 1: Foundation & User Management
- Docker Compose stack with all services (FastAPI, PostgreSQL, Redis, MinIO, Celery)
- Database schema for 5 core Documentum object types (Process, Activity, Flow, Package, WorkItem)
- User/group/role management with JWT authentication
- Append-only audit trail on every create/update/delete

### Phase 2: Document Management
- File upload to MinIO with metadata stored in PostgreSQL
- Major/minor versioning with check-in/check-out locking
- Admin force-unlock, version history, download any version
- Extensible metadata with custom properties

### Phase 3: Workflow Template Design (API)
- Template CRUD with activities (Manual, Auto, Start, End), flows, and process variables
- AND-join / OR-join trigger conditions on activities
- Conditional routing expressions evaluated against process variables
- Structural validation (disconnected nodes, missing performers, unreachable activities)
- Immutable versioning — installing a template freezes it; edits create new versions

### Phase 4: Process Engine Core
- Start workflow instances from installed templates with document attachment
- State machine: Dormant → Running → Halted → Failed → Finished
- Sequential routing (A → B → C)
- Parallel routing (AND-split activates multiple activities; AND-join waits for all)
- Process variable read/write during execution

### Phase 5: Work Items & Inbox
- Work items generated for manual activities, routed to assigned performers
- Inbox with filtering, sorting, priority, and due date
- Complete (forward) or reject work items with comments
- Performer assignment: supervisor, specific user, or group-based

### Phase 6: Advanced Routing & Alias Sets
- Performer-chosen routing (user selects which outgoing path)
- Expression-based conditional routing (engine evaluates at runtime)
- Reject flows — loop back to previous activities
- Sequential performers and runtime selection
- Alias sets — map abstract roles to users without editing templates

### Phase 7: Document Lifecycle & ACL
- Document state machine: Draft → Review → Approved → Archived
- Workflow-triggered lifecycle transitions (e.g., approval activity promotes document)
- ACL permissions auto-update on state changes (e.g., read-only after Approved)
- Permission enforcement on all API operations (403 on unauthorized access)
- Full audit trail for lifecycle transitions and ACL mutations

## What's Remaining (Phases 8–11)

| Phase | Name | Description |
|-------|------|-------------|
| **8** | Visual Workflow Designer | React Flow drag-and-drop canvas for designing templates in the browser |
| **9** | Auto Activities & Workflow Agent | Server-side Python method execution, Celery beat agent, REST API integration |
| **10** | Delegation, Work Queues & Management | User delegation, shared task pools, admin workflow control (halt/resume/abort) |
| **11** | Dashboards, Query Interface & Validation | BAM dashboards, admin query interface, contract approval end-to-end example |

## How to Continue Building

This project uses the [GSD (Get Shit Done)](https://github.com/coleam00/gsd) workflow system with Claude Code for structured phase-by-phase development. Each phase goes through: **discuss → plan → execute → verify**.

### Resuming development

```bash
# Open Claude Code in the project directory
cd documentum_clone
claude

# Check current progress
/gsd:progress

# Start the next phase (Phase 8: Visual Workflow Designer)
/gsd:discuss-phase 8    # Gather context, clarify approach
/gsd:plan-phase 8       # Generate detailed execution plans
/gsd:execute-phase 8    # Execute plans with atomic commits

# Or run all remaining phases autonomously
/gsd:autonomous
```

### Phase 8 specifically (next up)

Phase 8 is the first **frontend** phase — it introduces React, TypeScript, Vite, and React Flow. The recommended workflow:

```bash
/gsd:ui-phase 8         # Generate UI design contract (recommended for frontend phases)
/gsd:discuss-phase 8    # Discuss approach and gather context
/gsd:plan-phase 8       # Create detailed plans
/gsd:execute-phase 8    # Build it
/gsd:verify-work 8      # User acceptance testing
```

### Manual development (without GSD)

If you prefer to develop without the GSD workflow:

1. **Frontend setup**: Initialize a React + Vite + TypeScript app in a `frontend/` directory with React Flow, shadcn/ui, Tailwind CSS, TanStack Query, and Zustand
2. **Visual designer**: Build the drag-and-drop workflow canvas using React Flow with custom nodes for activity types
3. **API integration**: Connect the designer to the existing template API endpoints
4. **Remaining backend**: Implement auto activities (Phase 9), delegation/queues (Phase 10), and dashboards (Phase 11)

## API Overview

All endpoints are documented at `http://localhost:8000/docs` (Swagger UI) when the server is running.

| Area | Endpoints | Description |
|------|-----------|-------------|
| Auth | `POST /auth/login`, `POST /auth/register` | JWT authentication |
| Users | `GET/POST/PUT/DELETE /users/` | User management |
| Groups | `GET/POST /groups/`, membership management | Group management |
| Documents | `POST /documents/upload`, versioning, check-in/out | Document CRUD |
| Templates | `GET/POST /templates/`, validate, install | Workflow template design |
| Workflows | `POST /workflows/start`, advance, manage | Workflow execution |
| Inbox | `GET /inbox/`, complete, reject, comment | Work item management |
| Aliases | `GET/POST /aliases/` | Alias set management |
| Lifecycle | `POST /lifecycle/transition` | Document state transitions |
| Health | `GET /health` | Service health check |

## License

Internal/personal use.
