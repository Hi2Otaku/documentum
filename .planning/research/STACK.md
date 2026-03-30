# Technology Stack

**Project:** Documentum Workflow Clone
**Researched:** 2026-03-30
**Overall Confidence:** HIGH

## Recommended Stack

### Backend Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | 0.135.x | HTTP API framework | Native async/await for WebSocket dashboards and concurrent workflow execution. Built-in OpenAPI docs. Pydantic integration for data validation. Django's ORM is still sync-only under the hood (threadpool wrappers), which is a liability for a workflow engine that needs real-time WebSocket feeds and concurrent background task coordination. |
| Uvicorn | 0.34.x | ASGI server | Standard production server for FastAPI. Use with `--workers` for multi-process or behind Gunicorn with UvicornWorker. |
| Python | 3.12+ | Runtime | 3.12 is the stable sweet spot (performance improvements, better error messages). 3.13 is fine too. Avoid 3.14 beta. |

**Why not Django:** Django's batteries (admin, auth, ORM) are valuable for CRUD apps, but this project needs: (1) native async for WebSockets/real-time dashboards, (2) fine-grained control over the workflow engine's execution model, (3) SQLAlchemy's superior async support and relationship modeling for complex workflow state machines. Django's ORM async story is still incomplete in 2026 -- async ORM calls run in threadpools, adding overhead under load.

### Database & ORM

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL | 16+ | Primary database | JSONB for process variables, LISTEN/NOTIFY for real-time dashboard updates, row-level security for ACLs, mature ACID compliance for workflow state integrity. |
| SQLAlchemy | 2.0.48 | ORM | Full async support via asyncpg driver. Declarative models with type hints. Superior relationship modeling for the complex Documentum object model (Process -> Activity -> Flow -> Package -> WorkItem). |
| Alembic | 1.18.x | Database migrations | The standard migration tool for SQLAlchemy. Auto-generates migrations from model changes. |
| asyncpg | 0.30.x | Async PostgreSQL driver | Fastest Python PostgreSQL driver. Native async, required for SQLAlchemy async engine. |

**Why not Django ORM:** SQLAlchemy 2.0's async engine works natively with asyncpg -- no threadpool overhead. The Documentum data model has deep relationships (5+ core object types with polymorphic behavior) that benefit from SQLAlchemy's Unit of Work pattern and explicit relationship loading strategies.

### Data Validation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Pydantic | 2.12.x | Request/response validation, settings | FastAPI's native validation layer. V2 is 5-50x faster than V1. Handles workflow config schemas, API contracts, and settings management. |
| pydantic-settings | 2.13.x | Configuration management | Type-safe config from env vars and .env files. |

### File/Document Storage

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| MinIO | latest | S3-compatible object storage | Runs locally (no cloud dependency), S3 API compatible (migrate to AWS S3 later if needed), built-in versioning, bucket policies for ACL. Stores document files while PostgreSQL stores metadata and version history. |
| minio (Python SDK) | 7.2.x | MinIO client | Official Python SDK. Handles upload, download, versioning, presigned URLs for secure document access. |

**Architecture:** Files stored in MinIO (object storage), metadata/versions tracked in PostgreSQL. This separates concerns: the database handles querying and relationships, MinIO handles binary storage efficiently. Document versioning is modeled in PostgreSQL (version number, label, timestamps, creator) with each version pointing to a MinIO object key.

**Why not filesystem storage:** No built-in versioning, no presigned URLs, harder to scale, no bucket policies. MinIO gives S3 semantics locally with zero cloud cost.

### Background Task Processing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Celery | 5.6.x | Task queue / worker system | The Process Engine and Workflow Agent are long-running background processes that execute workflow steps, auto-activities, and timer-based triggers. Celery provides: Canvas workflows (chains, groups, chords) for modeling parallel/sequential execution, beat scheduler for periodic Workflow Agent polling, mature retry/error handling, result backends for tracking task state. |
| Redis | 7.x+ | Message broker + cache + pub/sub | Celery broker, WebSocket pub/sub for real-time dashboards, session cache, rate limiting. One dependency serving multiple roles. |
| redis-py | 5.x+ | Python Redis client | Async support via redis.asyncio for FastAPI integration. |

**Why Celery over Dramatiq:** Celery's Canvas (chains, groups, chords) directly maps to Documentum's parallel/sequential routing patterns. A workflow with parallel legal and financial review followed by director approval is literally a `chord([legal_review, financial_review], director_approval)`. Dramatiq is simpler but lacks these workflow primitives. The complexity cost of Celery is justified here because workflow orchestration IS the product.

**Why not ARQ/Taskiq:** Less mature, smaller ecosystems, fewer production battle scars. This project needs proven reliability for a workflow engine.

### Real-Time Communication

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI WebSockets | (built-in) | Real-time dashboard updates, inbox notifications | FastAPI's native WebSocket support on ASGI. No additional library needed. |
| PostgreSQL LISTEN/NOTIFY | (built-in) | Database-level event broadcasting | When a workflow state changes (task completed, new work item), PostgreSQL triggers notify connected listeners. FastAPI WebSocket handlers subscribe and push to clients. Eliminates polling. |
| Server-Sent Events (SSE) | (built-in) | One-way dashboard streams | For BAM dashboards that only display data (no user input), SSE is simpler than WebSockets. Use `StreamingResponse` in FastAPI. |

**Pattern:** Database change -> PostgreSQL NOTIFY -> FastAPI listener -> WebSocket/SSE -> Browser dashboard. For Celery task completion events, use Redis pub/sub -> FastAPI listener -> WebSocket.

### Authentication & Security

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| python-jose[cryptography] | 3.3.x | JWT token creation/verification | Standard JWT library. Handles token signing, expiration, claims. |
| passlib[bcrypt] | 1.7.x | Password hashing | Industry standard bcrypt hashing. |
| FastAPI Security | (built-in) | OAuth2 password flow, dependency injection | Built-in OAuth2PasswordBearer scheme with dependency injection for route protection. |

**ACL Strategy:** Build a custom ACL system in PostgreSQL modeled after Documentum's permission sets (None, Browse, Read, Relate, Version, Write, Delete). Store ACLs as database records linking users/groups to objects with permission levels. Enforce in FastAPI middleware/dependencies.

### Frontend Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | 19.x | UI framework | Dominant ecosystem, best library support for workflow UIs. React 19 with Server Components (though we use it as SPA). |
| TypeScript | 5.x | Type safety | Non-negotiable for a complex UI with workflow state, drag-and-drop, and real-time data. |
| Vite | 6.x | Build tool | 40x faster than CRA. Native ES modules in dev, Rollup for production. The default choice for React SPAs in 2026. |

**Why not Next.js:** This is an internal tool, not a public website. No SSR/SEO needed. Vite SPA is simpler, faster to develop, and easier to deploy alongside the FastAPI backend. Next.js adds complexity (server components, routing conventions) without benefit for this use case.

### Frontend Libraries

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| @xyflow/react (React Flow) | 12.10.x | Visual workflow designer (drag-and-drop) | The de facto standard for node-based UIs in React. Built-in drag-and-drop, custom nodes/edges, zoom/pan, mini-map. Maps directly to the Process Builder / workflow designer requirement. |
| shadcn/ui | latest (CLI v4) | UI component library | Copy-paste components built on Radix UI + Tailwind. Full code ownership, accessible by default, highly customizable. Better than MUI for this project because we need custom workflow-specific components. |
| Tailwind CSS | 4.x | Utility-first CSS | shadcn/ui dependency. Rapid UI development without CSS naming debates. |
| @tanstack/react-query | 5.95.x | Server state management | Caching, background refetching, optimistic updates for workflow data. Handles all API data fetching. |
| @tanstack/react-table | 8.21.x | Data tables | Headless table logic for work item lists, audit logs, user management. Sorting, filtering, pagination built-in. |
| Zustand | 5.x | Client state management | Lightweight (~3KB) store for UI state (selected nodes, panel visibility, modal state). TanStack Query handles server state; Zustand handles UI state only. |
| React Router | 7.x | Client-side routing | Standard SPA routing. Dashboard, inbox, workflow designer, admin pages. |
| Recharts | 2.x | Dashboard charts | Built on D3, React-native API. For BAM dashboard metrics (throughput, cycle time, bottleneck visualization). |

### Testing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | 8.x | Python test framework | Standard. Fixtures, parametrize, plugins. |
| pytest-asyncio | 0.24.x | Async test support | Required for testing async FastAPI endpoints and SQLAlchemy async queries. |
| httpx | 0.28.x | Async HTTP client for testing | FastAPI's recommended test client (replaces requests for async). `AsyncClient` for testing WebSocket and async endpoints. |
| pytest-cov | 5.x | Coverage reporting | Target 80%+ coverage on workflow engine core. |
| Vitest | 3.x | Frontend test runner | Vite-native, fast, Jest-compatible API. |
| Playwright | 1.x | E2E browser testing | Test the visual workflow designer drag-and-drop, dashboard rendering. |

### DevOps & Infrastructure

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Docker | latest | Containerization | PostgreSQL, Redis, MinIO, FastAPI, Celery workers all as containers. |
| Docker Compose | latest | Local orchestration | Single `docker-compose up` for the full stack. |
| Ruff | 0.9.x | Python linter + formatter | Replaces flake8 + black + isort. 10-100x faster. The 2026 standard. |
| pre-commit | 3.x | Git hooks | Ruff, type checking, test runner on commit. |
| mypy | 1.x | Python type checking | Strict mode for workflow engine core. Pydantic plugin for model validation. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Backend | FastAPI | Django | Async ORM still incomplete; workflow engine needs native async for WebSockets and concurrent execution |
| ORM | SQLAlchemy 2.0 | Django ORM | No native async; weaker relationship modeling for complex object graphs |
| ORM | SQLAlchemy 2.0 | Tortoise ORM | Smaller ecosystem, fewer production deployments, less mature migration tooling |
| Task Queue | Celery | Dramatiq | Lacks Canvas workflow primitives (chains/groups/chords) that map to parallel routing |
| Task Queue | Celery | ARQ | Too lightweight for workflow orchestration; no periodic task scheduler |
| File Storage | MinIO | Local filesystem | No versioning, no presigned URLs, no bucket policies |
| File Storage | MinIO | AWS S3 | Requires cloud account; MinIO is S3-compatible so migration is trivial later |
| Frontend | React + Vite | Next.js | SSR unnecessary for internal tool; adds deployment complexity |
| Frontend | React + Vite | Vue/Svelte | React Flow (xyflow) is the best node-based UI library, and it is React-first |
| UI Components | shadcn/ui | MUI (Material UI) | MUI is opinionated on design; shadcn gives full code ownership for custom workflow components |
| State Mgmt | Zustand + TanStack Query | Redux Toolkit | Overkill for UI state when TanStack Query handles server state; Zustand is 5x smaller |
| Charts | Recharts | D3 directly | D3 has steep learning curve; Recharts wraps D3 with React components |
| Workflow UI | React Flow (@xyflow/react) | JointJS | React Flow is open source (MIT core), more active community, better React integration |

## Installation

```bash
# Python backend (use pip or uv)
pip install fastapi[standard] uvicorn[standard] \
    sqlalchemy[asyncio] asyncpg alembic \
    pydantic pydantic-settings \
    celery[redis] redis \
    minio \
    python-jose[cryptography] passlib[bcrypt] \
    python-multipart  # for file uploads

# Dev dependencies
pip install -D pytest pytest-asyncio pytest-cov httpx \
    ruff mypy pre-commit

# Frontend
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install @xyflow/react @tanstack/react-query @tanstack/react-table \
    zustand react-router recharts
npx shadcn@latest init  # sets up shadcn/ui + Tailwind

# Dev dependencies
npm install -D vitest @testing-library/react playwright
```

## Docker Compose Services

```yaml
services:
  db:
    image: postgres:16
    # Document metadata, workflow state, ACLs, audit trail
  redis:
    image: redis:7
    # Celery broker, pub/sub for real-time, cache
  minio:
    image: minio/minio
    # Document file storage (S3-compatible)
  api:
    build: ./backend
    # FastAPI application
  celery-worker:
    build: ./backend
    command: celery -A app.worker worker
    # Process Engine + Workflow Agent
  celery-beat:
    build: ./backend
    command: celery -A app.worker beat
    # Scheduled tasks (agent polling, SLA checks)
  frontend:
    build: ./frontend
    # React SPA (or served by nginx in production)
```

## Key Architecture Decisions

### Why FastAPI + SQLAlchemy (not Django)

The workflow engine has three async-critical paths:

1. **WebSocket dashboards** -- BAM metrics pushed in real-time via PostgreSQL NOTIFY -> WebSocket
2. **Concurrent workflow execution** -- Multiple workflow instances advancing simultaneously
3. **Long-polling inbox** -- Users waiting for new work items

Django can do all of these, but with threadpool overhead on every ORM call. FastAPI + SQLAlchemy async gives true async I/O end-to-end. For a workflow engine where state transitions happen rapidly under load, this matters.

### Why Celery (not just asyncio)

The Process Engine and Workflow Agent need:
- **Persistent task state** -- Tasks survive server restarts
- **Retry with backoff** -- Failed auto-activities retry automatically
- **Periodic scheduling** -- Workflow Agent polls every N seconds (Celery Beat)
- **Canvas workflows** -- Parallel review activities map to Celery groups/chords
- **Worker scaling** -- Add more Celery workers as workflow volume grows

Pure asyncio tasks would be lost on restart and harder to monitor/debug.

### Why MinIO (not PostgreSQL BLOB)

Storing documents as PostgreSQL BLOBs works for small files but:
- Bloats the database (backup/restore becomes slow)
- No presigned URLs (every download goes through the API)
- No native bucket policies
- MinIO gives S3 semantics with zero config, and the Python SDK is clean

## Sources

- [FastAPI Official Docs](https://fastapi.tiangolo.com/) -- HIGH confidence
- [FastAPI PyPI - v0.135.x](https://pypi.org/project/fastapi/) -- HIGH confidence
- [SQLAlchemy 2.0.48 Release](https://www.sqlalchemy.org/blog/2026/03/02/sqlalchemy-2.0.48-released/) -- HIGH confidence
- [Alembic 1.18.4 Docs](https://alembic.sqlalchemy.org/) -- HIGH confidence
- [Celery 5.6.x Docs](https://docs.celeryq.dev/en/stable/) -- HIGH confidence
- [React Flow / @xyflow/react](https://reactflow.dev) -- HIGH confidence
- [shadcn/ui](https://ui.shadcn.com/) -- HIGH confidence
- [TanStack Query v5](https://tanstack.com/query/latest) -- HIGH confidence
- [Pydantic v2.12.x](https://docs.pydantic.dev/latest/) -- HIGH confidence
- [MinIO Python SDK](https://minio-py.min.io/) -- HIGH confidence
- [Zustand](https://zustand.docs.pmnd.rs/) -- HIGH confidence
- [Django async ORM limitations in 2026](https://engineering.kraken.tech/news/2026/01/12/using-django-async.html) -- MEDIUM confidence
- [Vite as default React build tool](https://devot.team/blog/react-vite) -- HIGH confidence
