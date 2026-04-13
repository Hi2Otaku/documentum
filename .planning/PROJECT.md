# Documentum Workflow Clone

## What This Is

A Python-based clone of OpenText Documentum's ECM and Workflow Management system, with a full web UI. Three milestones shipped: a complete Petri-net workflow engine (v1.0), a full React frontend (v1.1), and an advanced engine layer adding timers, sub-workflows, event-driven activities, notifications, renditions, virtual documents, retention, and digital signatures (v1.2).

The next milestone (v1.3) reorients the system from **workflow-centric** to **document-centric** — matching Documentum's ECM platform model where documents are the primary object and workflows exist to route them.

## Core Value

Any workflow use case described in the Documentum specification can be modeled and executed end-to-end. From v1.3 onward: any *document management* use case described in the Documentum specification can also be managed end-to-end — with folders, types, search, and document-first navigation.

## Requirements

### Validated

- ✓ Docker Compose stack (FastAPI, PostgreSQL, Redis, MinIO, Celery) — v1.0 Phase 1
- ✓ Database schema for 5 core Documentum object types with audit columns — v1.0 Phase 1
- ✓ User/group/role management with JWT authentication — v1.0 Phase 1
- ✓ Audit trail: full before/after state logging on every mutation — v1.0 Phase 1
- ✓ Document upload, versioning (major/minor), check-in/check-out with MinIO storage — v1.0 Phase 2
- ✓ Extensible document metadata with custom properties — v1.0 Phase 2
- ✓ Workflow template design API (dm_process equivalent) — CRUD, validation, installation, versioning — v1.0 Phase 3
- ✓ Manual activities with full performer assignment (supervisor, user, group, sequential, runtime selection) — v1.0 Phase 5/6
- ✓ Auto activities executing server-side methods (Python equivalents of dm_method) — v1.0 Phase 9
- ✓ Alias sets for flexible performer mapping without hardcoding users — v1.0 Phase 6
- ✓ Flow routing: sequential, parallel, conditional (template-level definition) — v1.0 Phase 3
- ✓ Reject flows allowing workflows to loop back to previous activities — v1.0 Phase 6
- ✓ Workflow instance lifecycle: Dormant → Running → Halted → Failed → Finished — v1.0 Phase 4
- ✓ Work items in user inboxes with complete/reject/comment — v1.0 Phase 5
- ✓ Delegation: users mark unavailable, tasks auto-route to delegates — v1.0 Phase 10
- ✓ Work queues: shared task pools where any qualified user can claim tasks — v1.0 Phase 10
- ✓ Trigger conditions: AND-join and OR-join for activities with multiple incoming flows — v1.0 Phase 3
- ✓ Process variables: read/write by activities, usable in routing conditions — v1.0 Phase 3
- ✓ Process Engine: synchronous workflow execution with sequential/parallel routing — v1.0 Phase 4
- ✓ Workflow Agent: background daemon executing auto activities — v1.0 Phase 9
- ✓ Document lifecycle states (Draft → Review → Approved → Archived) with workflow-triggered transitions — v1.0 Phase 7
- ✓ ACL/Security integration: automatic permission changes at workflow steps — v1.0 Phase 7
- ✓ Visual workflow designer: drag-and-drop React Flow canvas with custom nodes, edges, properties panel — v1.0 Phase 8
- ✓ BAM dashboards: real-time process metrics, bottleneck detection, SLA compliance — v1.0 Phase 11
- ✓ External system integration capability (webhook/API-based) — v1.0 Phase 9
- ✓ Contract approval demo workflow running end-to-end — v1.0 Phase 11
- ✓ DQL-like query interface for workflow administration — v1.0 Phase 11
- ✓ Navigation shell, inbox UI, document pages, workflow operations UI — v1.1 Phases 12–15
- ✓ Domain event bus (Redis pub/sub + persistent events table) — v1.2 Phase 16
- ✓ In-app and email notifications with unread badge and mark-read — v1.2 Phase 16
- ✓ Timer activities: deadline enforcement, Celery Beat escalation actions — v1.2 Phase 17
- ✓ Sub-workflows: child spawning, parent pause/resume, variable mapping, depth limits — v1.2 Phase 18
- ✓ Event-driven activities: auto-complete on domain event match — v1.2 Phase 19
- ✓ Document renditions: auto PDF and thumbnail via LibreOffice headless worker — v1.2 Phase 20
- ✓ Virtual documents: child assembly, ordering, cycle detection, merged PDF — v1.2 Phase 21
- ✓ Retention policies and legal holds blocking premature document deletion — v1.2 Phase 22
- ✓ Digital signatures (PKCS7/CMS) with post-signing immutability — v1.2 Phase 23

### Active (v1.3 targets)

- [ ] Cabinet/folder hierarchy — documents organized in a navigable tree (dm_cabinet, dm_folder equivalent)
- [ ] Document type system — custom types extending a base document type, with type-specific metadata schemas
- [ ] Full-text search — content indexing and search across document body and metadata
- [ ] Document-first navigation — browse by folder/cabinet, not just by workflow or search
- [ ] dm_sysobject supertype — unified base object model so documents, folders, and workflows share common attributes
- [ ] Folder-level ACL inheritance — permissions flow down from cabinet to folder to document
- [ ] Document relationships — relate documents to each other (supersedes, references, is-part-of)
- [ ] Saved searches / smart folders — named queries that act like virtual folders

### Out of Scope

- xCP platform bundling (Composer, TaskSpace as separate products) — too broad, focus on engine
- xCelerators industry templates — domain-specific; beyond current scope
- Process Integrator protocol support (JMS, FTP, SOAP) — use modern REST/webhook instead
- Mobile native app — web-responsive UI is sufficient
- Real-time collaborative editing — check-in/check-out prevents conflicts; OT/CRDT is excessive
- Full PKI/CA infrastructure — self-signed certs in DB suffice for internal use
- Multi-tenant isolation — internal/personal use, adds complexity everywhere

## Current Milestone: v1.3 Document-Centric ECM

**Goal:** Reorient from workflow-centric to document-centric. Add a cabinet/folder hierarchy, document type system, full-text search, and document-first navigation — so the system operates as a genuine ECM platform, not just a workflow engine with document attachments.

**Phases:** TBD — defined via `/gsd:new-milestone`

## Context

- Inspired by the OpenText Documentum Workflow Management technical specification (Vietnamese, March 2026)
- 3 milestones shipped: v1.0 (engine), v1.1 (frontend), v1.2 (advanced engine)
- Stack locked in: FastAPI + SQLAlchemy async + PostgreSQL + Redis + MinIO + Celery + React 19 + Vite
- ~17,400 Python LOC, ~13,800 TypeScript LOC
- Internal/personal use — not a SaaS product
- Key gap identified: the system is workflow-centric; Documentum is document-centric. v1.3 closes this.

## Constraints

- **Tech stack:** FastAPI (async) + SQLAlchemy 2.0 + PostgreSQL — locked in
- **Frontend:** React 19 + TypeScript + shadcn/ui + Tailwind — locked in
- **Document storage:** MinIO (S3-compatible) — locked in
- **Background processing:** Celery + Redis — locked in

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI over Django | Native async needed for WebSocket dashboards and concurrent workflow execution | ✓ Good — async was essential for event bus and real-time features |
| SQLAlchemy 2.0 async | Full async ORM, superior relationship modeling | ✓ Good — complex object graph handled cleanly |
| Celery over asyncio-only | Persistent task state, Beat scheduler, Canvas workflows | ✓ Good — Beat polling pattern worked well for timers and sub-workflow polling |
| MinIO over PostgreSQL BLOB | No DB bloat, presigned URLs, bucket policies | ✓ Good — renditions stored in separate bucket cleanly |
| React Flow for workflow designer | Best node-based UI library in the React ecosystem | ✓ Good — implemented full drag-and-drop designer |
| Event-first build order (v1.2) | Event bus as architectural keystone for all v1.2 features | ✓ Good — 6/8 features consumed the event bus as designed |
| Phases 24–26 gap closure pattern | Separate integration/alignment phases after feature code written | ✓ Good — isolated wiring work from feature design |
| REST/webhook over legacy protocols | Modern alternative to JMS/SOAP/FTP | ✓ Good — no legacy protocol debt |

---
*Last updated: 2026-04-13 — Milestone v1.2 shipped (Advanced Engine & Document Platform). v1.3 Document-Centric ECM next.*
