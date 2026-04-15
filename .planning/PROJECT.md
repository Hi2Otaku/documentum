# Documentum Workflow Clone

## What This Is

A Python-based clone of OpenText Documentum's ECM and Workflow Management system, with a full web UI. Four milestones shipped: a complete Petri-net workflow engine (v1.0), a full React frontend (v1.1), an advanced engine layer with timers, sub-workflows, event-driven activities, notifications, renditions, virtual documents, retention, and digital signatures (v1.2), and a document-centric ECM platform with folders, types, search, relationships, and document-first navigation (v1.3). v1.4 targets enterprise completeness — wiring up existing backend features to the frontend, plus SSO, CMIS, bulk operations, workflow resilience, desktop integration, and operational tooling.

## Current State (v1.4 in progress)

v1.3 shipped 2026-04-14 as a full document-centric ECM platform. Audit against real Documentum identified gaps: 6 backend features with no frontend UI, and ~13 missing enterprise capabilities. v1.4 addresses all of them.

Previously shipped (v1.0–v1.3):
- Petri-net workflow engine with visual designer, auto/timer/event-driven activities, sub-workflows
- Full React frontend with inbox, dashboards, document management, folder browser
- Document types, cabinet/folder hierarchy, folder ACL inheritance, full-text search
- Document relationships, saved searches, smart folders, digital signatures, retention, renditions

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

### Active (v1.4 targets)

*Frontend gap closure (backend exists, UI missing):*
- [ ] Digital signatures UI — sign, verify, view certificates from the web interface
- [ ] Retention & legal hold management UI — set policies, place/release holds
- [ ] Document-level ACL UI — manage permissions per document (not just folder)
- [ ] Queue administration UI — create, edit, delete queues and manage members
- [ ] Fix document lifecycle state filter — dropdown exists but doesn't send filter to API
- [ ] Notification preferences UI — configure which events trigger notifications

*Authentication & integration:*
- [ ] LDAP/SAML/OAuth2 SSO — enterprise identity provider integration
- [ ] CMIS standard API — OASIS content management interoperability services
- [ ] WebDAV file access — mount repository as network drive
- [ ] Email archiving — capture, index, and store emails as documents

*Workflow resilience:*
- [ ] Workflow error handling & compensation — declarative exception handlers, rollback activities
- [ ] Workflow versioning — concurrent active template versions with in-flight migration
- [ ] Advanced join semantics — weighted, cancelling, timeout sync beyond basic AND/OR

*Operations & administration:*
- [ ] Bulk/batch operations — mass update, delete, reclassify with job tracking
- [ ] Import/Export — standard format packages for migration and backup
- [ ] System monitoring & health dashboard — deep health checks, alerting, queue depth
- [ ] Tiered storage management — policy-based migration between hot/warm/cold storage
- [ ] Tamper-proof audit trail — cryptographic signing of audit logs
- [ ] Process analytics & mining — discover workflows from execution logs, optimization insights

### Out of Scope

- xCP platform bundling (Composer, TaskSpace as separate products) — too broad, focus on engine
- xCelerators industry templates — domain-specific; beyond current scope
- Process Integrator protocol support (JMS, FTP, SOAP) — use modern REST/webhook instead
- Mobile native app — web-responsive UI is sufficient
- Real-time collaborative editing — check-in/check-out prevents conflicts; OT/CRDT is excessive
- Full PKI/CA infrastructure — self-signed certs in DB suffice for internal use
- Multi-tenant isolation — internal/personal use, adds complexity everywhere

## Current Milestone: v1.4 Enterprise Completeness

**Goal:** Close all functional gaps identified in the Documentum comparison audit — wire up existing backend features to the frontend, and build the missing enterprise capabilities (SSO, CMIS, bulk operations, workflow resilience, desktop integration, and operational tooling).

**Phases:** TBD — defined via roadmapper

## Context

- Inspired by the OpenText Documentum Workflow Management technical specification (Vietnamese, March 2026)
- 4 milestones shipped: v1.0 (engine), v1.1 (frontend), v1.2 (advanced engine), v1.3 (document-centric ECM)
- Stack locked in: FastAPI + SQLAlchemy async + PostgreSQL + Redis + MinIO + Celery + React 19 + Vite
- Internal/personal use — not a SaaS product
- Key gap identified (v1.4): audit against real Documentum found 6 backend features without frontend UI, ~13 missing enterprise capabilities

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

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-15 — v1.3 complete. Starting v1.4 Enterprise Completeness milestone.*
