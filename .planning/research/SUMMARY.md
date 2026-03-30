# Project Research Summary

**Project:** Documentum Workflow Clone
**Domain:** Workflow Engine / BPM / Enterprise Content Management
**Researched:** 2026-03-30
**Confidence:** HIGH

## Executive Summary

This project builds a clone of OpenText Documentum's workflow and document management capabilities: a structured BPM engine where process templates define activities, flows, and routing rules, and a runtime engine advances workflow instances through those steps while managing document packages, work item inboxes, ACLs, and an audit trail. Expert implementations treat the workflow engine as a state machine runtime backed by a relational database, with a dedicated background process (the Process Engine) as the sole owner of state transitions, and a separate agent for executing automated server-side activities. This separation is non-negotiable — any architecture that lets the API layer mutate workflow state directly will produce race conditions, audit gaps, and inconsistency.

The recommended approach uses FastAPI + SQLAlchemy (async, native PostgreSQL) for the API layer, Celery + Redis for the background Process Engine and Workflow Agent, MinIO for document file storage, and React + React Flow for the visual workflow designer. The choice of FastAPI over Django is deliberate: the workflow engine has three async-critical paths (WebSocket dashboards, concurrent workflow execution, real-time inbox updates) that Django's threadpool-wrapped async ORM handles poorly under load. Celery's Canvas primitives (chains, groups, chords) directly model Documentum's parallel and sequential routing patterns in a way that simpler task queues cannot.

The primary risks cluster around three areas: (1) engine correctness — AND-join deadlocks and race conditions in parallel completion are the most common failure modes in custom workflow engines and must be designed out from the first migration using token-based execution and transactional atomic join evaluation; (2) template versioning — running instances must pin to the template version they started with, or editing a template will corrupt in-flight workflows; and (3) audit integrity — the audit trail must be a cross-cutting concern built from day one, not bolted on later, capturing every state transition atomically with the change it records.

---

## Key Findings

### Recommended Stack

The backend is FastAPI (0.135.x) with SQLAlchemy 2.0 async (asyncpg driver) against PostgreSQL 16. Pydantic v2 handles validation. Celery 5.6 with Redis 7 as broker runs the Process Engine (advances workflow state machines) and Workflow Agent (executes auto activities on a beat schedule). MinIO provides S3-compatible local document storage with versioning and presigned URLs. See STACK.md for full version matrix and alternatives considered.

The frontend is React 19 + TypeScript + Vite (SPA, not Next.js — no SSR needed for an internal tool). React Flow (@xyflow/react 12.x) is the only serious option for the visual workflow designer. TanStack Query handles server state; Zustand handles UI state; shadcn/ui + Tailwind provides the component layer.

**Core technologies:**
- **FastAPI + Uvicorn:** HTTP API and WebSocket server — native async end-to-end, no threadpool overhead
- **SQLAlchemy 2.0 (asyncpg):** ORM — full async, models the deep Documentum object graph cleanly
- **PostgreSQL 16:** Primary database — JSONB for process variables, LISTEN/NOTIFY for real-time events, row-level security for ACLs
- **Celery 5.6 + Redis 7:** Task queue — Canvas workflow primitives map to parallel/sequential routing; beat scheduler runs the Workflow Agent
- **MinIO:** Document file storage — S3-compatible locally, bucket policies, versioning, presigned URLs
- **React Flow (@xyflow/react):** Visual designer — the de facto standard for node-based UIs in React, MIT licensed
- **TanStack Query v5:** Server state — caching, background refetch, optimistic updates for workflow data
- **shadcn/ui + Tailwind 4:** UI layer — full code ownership, accessible, customizable for workflow-specific components

### Expected Features

See FEATURES.md for the full dependency graph and priority ordering.

**Must have (table stakes):**
- Sequential, parallel (AND-split/join), and conditional routing — any workflow engine without these is a toy
- Process variables with type system — routing conditions require typed variables
- User inbox and work item lifecycle (acquire, complete, reject) — the primary human interaction surface
- Activity performer assignment (user, group, alias, work queue) — workflows need to route to someone
- Document upload, versioning (major/minor), and check-in/check-out locking
- Workflow packages — attaching documents to workflow instances
- Audit trail — non-negotiable for any compliance-adjacent system
- User and group management with ACL system
- Visual workflow designer (drag-and-drop process template authoring)
- Workflow template versioning — running instances must not break when templates are edited

**Should have (differentiators):**
- Reject flows / backward routing — send documents back for rework
- User delegation and work queues — advanced task distribution
- Auto activities (server-side method execution) and the Workflow Agent daemon
- Document lifecycle state management (Draft, Review, Approved, Archived)
- BAM dashboards with real-time metrics and SLA tracking
- Task notifications (email or in-app)
- Alias sets — abstract performer mapping without hardcoding users

**Defer (v2+):**
- DQL-like query interface — power-user admin, non-essential for core function
- Digital signatures — high complexity, narrow use case
- Webhook/REST integration to external systems — useful but not core to the engine
- Full-text document search — metadata search is sufficient initially

**Explicit anti-features (never build):**
- BPMN 2.0 XML import/export, AI process optimization, CMMN case management, process simulation, DMN decision tables, multi-tenant SaaS, mobile native app

### Architecture Approach

The system is a layered monolith with background workers, not microservices. All components share a single PostgreSQL database. The API layer (FastAPI) owns CRUD and user-facing operations. The Process Engine (Celery task) is the sole owner of workflow state transitions — the API dispatches to it via Celery tasks but never mutates workflow state directly. The Workflow Agent (Celery beat) polls for and executes auto activities. Real-time updates flow via PostgreSQL LISTEN/NOTIFY into WebSocket connections managed by FastAPI. See ARCHITECTURE.md for the full data flow diagrams and data model.

**Major components:**
1. **Process Engine (Celery worker)** — state machine runtime; advances workflows, creates work items, evaluates AND/OR joins and conditional flows, logs audit events
2. **Workflow Agent (Celery beat)** — polls for queued auto activities, executes Python callables (dm_method equivalents) with timeout and retry
3. **REST API (FastAPI)** — user-facing endpoints; dispatches to Process Engine, manages CRUD, enforces ACLs
4. **Visual Workflow Designer (React + React Flow)** — drag-and-drop process template authoring; validates on save using the same schema the engine uses
5. **Document Service** — file storage in MinIO, version metadata in PostgreSQL, check-in/check-out locking
6. **Security Service** — ACL evaluation and replacement-based permission updates at each workflow step
7. **Audit Service** — append-only event log written atomically with every state transition

### Critical Pitfalls

1. **AND-join deadlocks (Pitfall 1)** — use a token-based execution model; track active branch tokens per instance; require every AND-split to have a matching AND-join at design-time validation. Build a stuck-instance detector for production. This must be in the core engine from Phase 1.

2. **Race conditions in parallel completion (Pitfall 2)** — use `SELECT FOR UPDATE` on the workflow instance row when evaluating join conditions; make all activity completion handlers idempotent; use optimistic locking (version column) on the instance. Must be designed into the data model before any code is written.

3. **Template versioning vs. running instances (Pitfall 3)** — templates are immutable once published; every edit creates a new version; running instances pin to the version they started with. This must be in the first database migration. Adding it retroactively requires migrating all existing instances.

4. **Celery task loss on worker crash (Pitfall 4)** — set `task_acks_late = True` and `task_reject_on_worker_lost = True`; store task execution state in the database (not just the broker); implement a watchdog for auto activities stuck in "executing" state; make all auto activities idempotent.

5. **Audit trail as afterthought (Pitfall 5)** — every state transition goes through a single audit-emitting function; audit record is written in the same database transaction as the state change; the table is INSERT-only. Design this cross-cutting concern before writing any feature code.

6. **ACL/permission drift (Pitfall 6)** — workflow permissions are replacement-based (not additive) when an activity starts; store the pre-workflow permission snapshot for restoration on cancellation; test effective permissions explicitly after each activity transition.

---

## Implications for Roadmap

Based on combined research, a clear dependency hierarchy dictates phase ordering. The Process Engine is the riskiest and most critical component — it must be built and validated before any user-facing feature is layered on top.

### Phase 1: Foundation and Data Model
**Rationale:** Every component depends on the data model. Template versioning, the dual document-ID/version-ID model, and the audit event schema are architectural decisions that are expensive to change after data exists. Must also establish the state machine transition table and token tracking before any engine code is written.
**Delivers:** Working database schema, auth, user/group management, Alembic migrations, Docker Compose stack
**Addresses:** User and group management (FEATURES Phase 1), token model for AND-joins, immutable template versioning, document dual-ID model
**Avoids:** Pitfall 3 (template versioning), Pitfall 2 (race conditions — optimistic locking columns must be in schema from day one), Pitfall 10 (document version confusion)

### Phase 2: Process Definition and Document Management
**Rationale:** The engine cannot run workflows until templates exist and documents can be attached. These are also the components most accessible via API/admin — they can be tested without a UI.
**Delivers:** Process template CRUD API (activities, flows, process variables, alias sets), document upload/versioning service, workflow package attachment
**Addresses:** FEATURES Phase 1 (document upload, versioning, metadata), workflow template data model
**Avoids:** Pitfall 8 (designer-engine schema mismatch) — define the canonical workflow schema here, before either the engine or designer is built

### Phase 3: Process Engine Core
**Rationale:** This is the heart of the system. Sequential routing, AND/OR join evaluation, performer resolution, work item creation, and the state machine are all built here. Everything user-facing depends on a working engine. This is the riskiest phase.
**Delivers:** Working workflow execution for sequential and parallel paths; work items created correctly; audit trail emitting from day one
**Uses:** Celery + Redis (Canvas workflow primitives for parallel routing), PostgreSQL SELECT FOR UPDATE for atomic join evaluation, asyncpg for async state transitions
**Implements:** Process Engine component, Routing Engine, Audit Service
**Avoids:** Pitfall 1 (AND-join deadlocks — token model), Pitfall 2 (race conditions — atomic join eval), Pitfall 5 (audit as afterthought), Pitfall 7 (state machine explosion — write state transition table first)

### Phase 4: User Inbox and Task Management
**Rationale:** Once the engine creates work items, users need to interact with them. This phase adds the human-facing side of the engine: the inbox, work item completion, conditional routing via process variables, and real-time WebSocket updates.
**Delivers:** User inbox (filterable, sortable), work item acquire/complete/reject, task priority and due dates, real-time inbox updates via WebSocket
**Uses:** FastAPI WebSockets, PostgreSQL LISTEN/NOTIFY, TanStack Query for frontend data management
**Implements:** Work Item Service, Inbox UI
**Avoids:** Pitfall 13 (process variable type safety — enforce typed variables before routing goes to users)

### Phase 5: Document Integration and ACL
**Rationale:** Workflow packages, check-in/check-out, document lifecycle, and ACLs tie the document management layer to the workflow engine. These interact tightly with the engine's state transitions and must come after the engine is stable.
**Delivers:** Document packages attached to workflow instances, check-in/check-out locking, document lifecycle state machine (Draft/Review/Approved/Archived), object-level ACL system with workflow-step permission updates
**Implements:** Document Service (full), Security Service, lifecycle integration in Process Engine
**Avoids:** Pitfall 6 (ACL permission drift — replacement-based permissions built here)

### Phase 6: Visual Workflow Designer
**Rationale:** The designer is high-effort but not a dependency for the engine or any backend feature. Building it after the engine is stable means the designer can be validated against a real execution runtime. It consumes the same canonical schema defined in Phase 2.
**Delivers:** Drag-and-drop process template authoring, graph validation (unreachable nodes, missing performers, structural errors), save/load to Phase 2 API
**Uses:** React Flow (@xyflow/react), Zustand for designer UI state
**Implements:** Workflow Designer UI component
**Avoids:** Pitfall 8 (designer uses the same schema as the engine — no translation layer)

### Phase 7: Workflow Agent and Auto Activities
**Rationale:** Auto activities require a stable Process Engine to advance workflows after execution. The agent is a separate concern from manual task management.
**Delivers:** dm_method equivalents (Python callables), Celery beat scheduler for agent polling, timeout and retry logic, dead letter queue for failed methods
**Uses:** Celery beat, `task_acks_late = True`, database-stored task execution state
**Implements:** Workflow Agent, Method registry
**Avoids:** Pitfall 4 (task loss — correct Celery config and watchdog)

### Phase 8: Advanced Routing and Delegation
**Rationale:** Reject flows, alias sets, delegation, and work queues require a fully working engine core and inbox. These are differentiating features that can be added incrementally.
**Delivers:** Reject flows (backward routing), alias set resolution, user delegation with cycle detection, work queues (shared task pools)
**Avoids:** Pitfall 12 (delegation cycles — cycle detection at setup time), Pitfall 11 (work queue starvation — fair distribution policies)

### Phase 9: BAM Dashboards, SLA, and Notifications
**Rationale:** Analytics requires running workflows generating data. This phase has no blocking dependencies on Phase 8 but needs several weeks of real workflow data to be meaningful.
**Delivers:** Real-time BAM dashboards (throughput, cycle time, bottleneck detection), SLA tracking per activity and process, task notifications (in-app), workflow monitoring for admins
**Uses:** Recharts for dashboard charts, Server-Sent Events for one-way metric streams, Celery beat for SLA timer polling
**Avoids:** Pitfall 9 (lost timers — database-stored SLA deadlines, periodic poller as source of truth)

### Phase Ordering Rationale

- **Schema-first:** Template versioning (Pitfall 3), token model (Pitfall 1), optimistic locking columns (Pitfall 2), and dual document IDs (Pitfall 10) are all database-schema decisions that cannot be retrofitted cheaply. They must land in Phase 1.
- **Engine before UI:** The Process Engine (Phase 3) must be validated with integration tests before the visual designer (Phase 6) is built on top of it. Building the designer first would mean validating it against a moving target.
- **Canonical schema before designer:** Defining the workflow schema in Phase 2 (before the engine and the designer) prevents the most common pitfall in workflow tooling: designer and engine diverging into incompatible formats (Pitfall 8).
- **ACL after engine:** Workflow-triggered permission changes require the engine to be stable. Attempting this earlier mixes concerns and introduces complexity before the core is proven.
- **Analytics last:** BAM dashboards and SLA tracking require real data. Building them before the engine is running produces placeholder infrastructure that will be rewritten.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Process Engine):** The token-based execution model for AND/OR joins is the most nuanced part of workflow engine design. Review Temporal's architecture articles and SpiffWorkflow's source before detailing tasks.
- **Phase 7 (Workflow Agent):** Celery's reliability patterns (`acks_late`, `reject_on_worker_lost`, ETA countdown + database poller) need concrete implementation research before task estimation.
- **Phase 9 (BAM/SLA):** SLA timer architecture (database-stored + periodic poller) needs validation against the Celery beat scheduler to confirm the polling pattern is correct for the chosen task queue.

Phases with well-documented patterns (can skip deep research):
- **Phase 1 (Foundation):** SQLAlchemy migrations, FastAPI project setup, Docker Compose — standard patterns with excellent official documentation.
- **Phase 2 (Process Definition):** REST CRUD APIs with Pydantic validation and SQLAlchemy — thoroughly documented, low risk.
- **Phase 4 (Inbox/Tasks):** TanStack Query + FastAPI WebSockets — well-documented patterns, extensive community examples.
- **Phase 6 (Visual Designer):** React Flow documentation is comprehensive and includes workflow editor examples directly applicable to this use case.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All major technology choices verified against official docs and PyPI release history. FastAPI, SQLAlchemy 2.0, Celery 5.6, React Flow all have current stable releases. Django async limitations sourced from a 2026 engineering post (MEDIUM for that specific claim, but the FastAPI choice is independently justified). |
| Features | HIGH | Derived from Documentum official documentation, multiple BPM tool comparisons, and open-source BPM engine analysis. Feature prioritization aligns with standard ECM/BPM literature. |
| Architecture | HIGH | Layered monolith + background workers pattern is well-validated for this class of system. Temporal's workflow engine principles, SpiffWorkflow reference architecture, and Documentum-specific workflow architecture sources all converge on the same patterns. |
| Pitfalls | HIGH | All 6 critical pitfalls are documented in multiple independent sources (Temporal, Flowable, Camunda, Hatchet). The AND-join deadlock and template versioning pitfalls are explicitly cited as "most common mistakes" in custom workflow engine development. |

**Overall confidence:** HIGH

### Gaps to Address

- **Expression evaluator for routing conditions:** The AST-based safe evaluator approach (Pitfall 13, Pattern 4 in ARCHITECTURE.md) is directionally correct, but the specific implementation should be prototyped early in Phase 3 to confirm performance and security characteristics against realistic condition expressions.
- **PostgreSQL LISTEN/NOTIFY under WebSocket load:** The real-time update architecture (NOTIFY -> FastAPI listener -> WebSocket) works cleanly for 1-10 users but the connection management pattern needs validation. Confirm that asyncpg's LISTEN support is compatible with the chosen SQLAlchemy async session pattern.
- **Celery Canvas vs. custom token tracking:** Celery groups/chords model parallel execution, but the token-based AND-join evaluation is a database-level concern, not a Celery-level concern. The boundary between "Celery orchestrates tasks" and "engine tracks tokens in PostgreSQL" needs explicit design in Phase 3.
- **Django references in ARCHITECTURE.md:** The architecture research file contains several Django-specific code snippets (Django ORM, Django Channels, Django Signals). These are illustrative only — the actual implementation uses FastAPI + SQLAlchemy async. The patterns are valid; the specific API calls are not.

---

## Sources

### Primary (HIGH confidence)
- [FastAPI Official Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0.48 Release](https://www.sqlalchemy.org/blog/2026/03/02/sqlalchemy-2.0.48-released/)
- [Celery 5.6.x Docs](https://docs.celeryq.dev/en/stable/)
- [React Flow / @xyflow/react](https://reactflow.dev)
- [Pydantic v2.12.x Docs](https://docs.pydantic.dev/latest/)
- [TanStack Query v5 Docs](https://tanstack.com/query/latest)
- [shadcn/ui](https://ui.shadcn.com/)
- [MinIO Python SDK](https://minio-py.min.io/)
- [Temporal: Workflow Engine Principles](https://temporal.io/blog/workflow-engine-principles)
- [Camunda: Versioning Process Definitions](https://docs.camunda.io/docs/components/best-practices/operations/versioning-process-definitions/)
- [OpenText Documentum Content Management](https://www.opentext.com/products/documentum-content-management)
- [Documentum Workflow Designer CE 22.4 User Guide](https://www.scribd.com/document/643787889/OpenText-Documentum-Workflow-Designer-CE-22-4-User-Guide-English-EDCPKL220400-AWF-EN-01-pdf)
- [SpiffWorkflow Python BPMN Engine](https://spiffworkflow.readthedocs.io/en/latest/bpmn/index.html)

### Secondary (MEDIUM confidence)
- [Django async ORM limitations in 2026](https://engineering.kraken.tech/news/2026/01/12/using-django-async.html) — supports FastAPI choice
- [Hatchet: Problems with Celery](https://hatchet.run/blog/problems-with-celery) — informs Celery reliability configuration
- [Flowable Forum: Stuck Process Instances](https://forum.flowable.org/t/stuck-process-instances-how-to-find-them/9579) — validates stuck-instance detector recommendation
- [Open Source BPM Comparison - Capital One](https://medium.com/capital-one-tech/2022-open-source-bpm-comparison-33b7b53e9c98)
- [Documentum Workflow Architecture - CrazyApple](https://www.crazyapple.com/content-management-foundations/workflow/)
- [Process Engine details - dm_misc](https://msroth.wordpress.com/tag/process-engine/)

### Tertiary (informational)
- [BPM Trends 2026 - GBTEC](https://www.gbtec.com/blog/bpm-trends-2026/)
- [7 BPM Challenges 2026 - Kissflow](https://kissflow.com/workflow/bpm/business-process-management-challlenges/)
- [5 Common Pitfalls in Enterprise BPM Implementation - FlyingDog](https://www.flyingdog.de/portal/en/blog/bpm-implementation-mistakes-avoid-enterprise/)

---
*Research completed: 2026-03-30*
*Ready for roadmap: yes*
