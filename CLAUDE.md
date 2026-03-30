<!-- GSD:project-start source:PROJECT.md -->
## Project

**Documentum Workflow Clone**

A near-complete clone of OpenText Documentum's Workflow Management system built in Python with a full web UI. It provides a general-purpose workflow engine that can model and execute arbitrary business processes — including document management with versioning, visual workflow design, user inboxes, dashboards, and all routing/delegation mechanisms described in Documentum's architecture.

**Core Value:** Any workflow use case described in the Documentum specification (sequential, parallel, conditional routing, reject flows, auto activities, delegation, work queues, BAM dashboards, lifecycle integration, audit trail, ACL management) can be modeled and executed end-to-end through the system.

### Constraints

- **Tech stack**: Python backend — framework to be determined by research (Django/FastAPI)
- **Frontend**: Full web UI with visual workflow designer (drag-and-drop), inbox, dashboards
- **Document storage**: Must support file upload, versioning, and package attachment to workflows
- **Background processing**: Needs a task queue/worker system for Process Engine and Workflow Agent
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Backend Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | 0.135.x | HTTP API framework | Native async/await for WebSocket dashboards and concurrent workflow execution. Built-in OpenAPI docs. Pydantic integration for data validation. Django's ORM is still sync-only under the hood (threadpool wrappers), which is a liability for a workflow engine that needs real-time WebSocket feeds and concurrent background task coordination. |
| Uvicorn | 0.34.x | ASGI server | Standard production server for FastAPI. Use with `--workers` for multi-process or behind Gunicorn with UvicornWorker. |
| Python | 3.12+ | Runtime | 3.12 is the stable sweet spot (performance improvements, better error messages). 3.13 is fine too. Avoid 3.14 beta. |
### Database & ORM
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL | 16+ | Primary database | JSONB for process variables, LISTEN/NOTIFY for real-time dashboard updates, row-level security for ACLs, mature ACID compliance for workflow state integrity. |
| SQLAlchemy | 2.0.48 | ORM | Full async support via asyncpg driver. Declarative models with type hints. Superior relationship modeling for the complex Documentum object model (Process -> Activity -> Flow -> Package -> WorkItem). |
| Alembic | 1.18.x | Database migrations | The standard migration tool for SQLAlchemy. Auto-generates migrations from model changes. |
| asyncpg | 0.30.x | Async PostgreSQL driver | Fastest Python PostgreSQL driver. Native async, required for SQLAlchemy async engine. |
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
### Background Task Processing
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Celery | 5.6.x | Task queue / worker system | The Process Engine and Workflow Agent are long-running background processes that execute workflow steps, auto-activities, and timer-based triggers. Celery provides: Canvas workflows (chains, groups, chords) for modeling parallel/sequential execution, beat scheduler for periodic Workflow Agent polling, mature retry/error handling, result backends for tracking task state. |
| Redis | 7.x+ | Message broker + cache + pub/sub | Celery broker, WebSocket pub/sub for real-time dashboards, session cache, rate limiting. One dependency serving multiple roles. |
| redis-py | 5.x+ | Python Redis client | Async support via redis.asyncio for FastAPI integration. |
### Real-Time Communication
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI WebSockets | (built-in) | Real-time dashboard updates, inbox notifications | FastAPI's native WebSocket support on ASGI. No additional library needed. |
| PostgreSQL LISTEN/NOTIFY | (built-in) | Database-level event broadcasting | When a workflow state changes (task completed, new work item), PostgreSQL triggers notify connected listeners. FastAPI WebSocket handlers subscribe and push to clients. Eliminates polling. |
| Server-Sent Events (SSE) | (built-in) | One-way dashboard streams | For BAM dashboards that only display data (no user input), SSE is simpler than WebSockets. Use `StreamingResponse` in FastAPI. |
### Authentication & Security
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| python-jose[cryptography] | 3.3.x | JWT token creation/verification | Standard JWT library. Handles token signing, expiration, claims. |
| passlib[bcrypt] | 1.7.x | Password hashing | Industry standard bcrypt hashing. |
| FastAPI Security | (built-in) | OAuth2 password flow, dependency injection | Built-in OAuth2PasswordBearer scheme with dependency injection for route protection. |
### Frontend Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | 19.x | UI framework | Dominant ecosystem, best library support for workflow UIs. React 19 with Server Components (though we use it as SPA). |
| TypeScript | 5.x | Type safety | Non-negotiable for a complex UI with workflow state, drag-and-drop, and real-time data. |
| Vite | 6.x | Build tool | 40x faster than CRA. Native ES modules in dev, Rollup for production. The default choice for React SPAs in 2026. |
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
# Python backend (use pip or uv)
# Dev dependencies
# Frontend
# Dev dependencies
## Docker Compose Services
## Key Architecture Decisions
### Why FastAPI + SQLAlchemy (not Django)
### Why Celery (not just asyncio)
- **Persistent task state** -- Tasks survive server restarts
- **Retry with backoff** -- Failed auto-activities retry automatically
- **Periodic scheduling** -- Workflow Agent polls every N seconds (Celery Beat)
- **Canvas workflows** -- Parallel review activities map to Celery groups/chords
- **Worker scaling** -- Add more Celery workers as workflow volume grows
### Why MinIO (not PostgreSQL BLOB)
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
