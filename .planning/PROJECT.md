# Documentum Workflow Clone

## What This Is

A near-complete clone of OpenText Documentum's Workflow Management system built in Python with a full web UI. It provides a general-purpose workflow engine that can model and execute arbitrary business processes — including document management with versioning, visual workflow design, user inboxes, dashboards, and all routing/delegation mechanisms described in Documentum's architecture.

## Core Value

Any workflow use case described in the Documentum specification (sequential, parallel, conditional routing, reject flows, auto activities, delegation, work queues, BAM dashboards, lifecycle integration, audit trail, ACL management) can be modeled and executed end-to-end through the system.

## Requirements

### Validated

- ✓ Docker Compose stack with FastAPI, PostgreSQL, Redis, MinIO, Celery — Phase 1
- ✓ Database schema for 5 core Documentum object types with audit columns — Phase 1
- ✓ User/group/role management with JWT authentication — Phase 1
- ✓ Audit trail: full before/after state logging on every mutation — Phase 1
- ✓ Document upload, versioning (major/minor), check-in/check-out with MinIO storage — Phase 2
- ✓ Extensible document metadata with custom properties — Phase 2

### Active

- ✓ Workflow template design API (dm_process equivalent) — CRUD, validation, installation, versioning — Phase 3
- ✓ Manual activities with full performer assignment (supervisor, user, group, sequential, runtime selection) — Phase 5/6
- ✓ Auto activities executing server-side methods (Python equivalents of dm_method) — Phase 9
- ✓ Alias sets for flexible performer mapping without hardcoding users — Phase 6
- ✓ Flow routing: sequential, parallel, conditional (template-level definition) — Phase 3
- ✓ Reject flows allowing workflows to loop back to previous activities — Phase 6
- ✓ Workflow instance lifecycle: Dormant → Running → Halted → Failed → Finished — Phase 4
- ✓ Work items appearing in user inboxes with complete/reject/comment — Phase 5
- [ ] Document management: upload, versioning, packages attached to workflows
- ✓ Delegation: users mark unavailable, tasks auto-route to delegates — Phase 10
- ✓ Work queues: shared task pools where any qualified user can claim tasks — Phase 10
- ✓ Trigger conditions: AND-join and OR-join for activities with multiple incoming flows — Phase 3
- ✓ Process variables: read/write by activities, usable in routing conditions — Phase 3
- ✓ Process Engine: synchronous workflow execution with sequential/parallel routing — Phase 4
- ✓ Workflow Agent: background daemon executing auto activities — Phase 9
- ✓ Lifecycle management: document states (Draft → Review → Approved → Archived) with workflow-triggered transitions — Phase 7
- ✓ Audit trail: full logging of who did what, when, with what decision — Phase 10
- ✓ ACL/Security integration: automatic permission changes at workflow steps — Phase 7
- ✓ Visual workflow designer: drag-and-drop React Flow canvas with custom nodes, edges, properties panel, save/load, validation — Phase 8
- ✓ BAM dashboards: real-time process metrics, bottleneck detection, SLA compliance — Phase 11
- ✓ External system integration capability (webhook/API-based) — Phase 9
- ✓ Contract approval example workflow running end-to-end (the full 7-step example from the spec) — Phase 11
- ✓ DQL-like query interface for workflow administration — Phase 11

### Out of Scope

- xCP platform bundling (Composer, TaskSpace as separate products) — too broad, focus on workflow engine
- xCelerators industry templates — domain-specific templates are beyond v1
- Process Integrator protocol support (JMS, FTP, SOAP) — use modern REST/webhook instead
- Mobile native app — web-responsive UI is sufficient

## Current Milestone: v1.1 Full Frontend Experience

**Goal:** Make every backend capability accessible through the web UI — users should never need the API or Swagger to operate the system.

**Target features:**
- Inbox page — view/acquire/complete/reject work items, comments & history, delegate tasks, browse & claim from work queues, toast/badge notifications
- Documents page — upload & browse files, check-in/check-out locking, version history with download, lifecycle state transitions
- Workflows page — start workflows (template picker + document attachment + variables), instance monitoring, admin controls (halt/resume/terminate), visual progress with React Flow read-only view
- Navigation — proper sidebar/nav menu connecting all pages (Templates, Inbox, Documents, Workflows, Dashboard, Query)

## Context

- This is inspired by the OpenText Documentum Workflow Management technical specification (Vietnamese, March 2026)
- The spec describes a mature enterprise ECM workflow system with 5 core object types: Process, Activity, Flow, Package, Work Item
- The contract approval workflow (7 steps: initiate → draft → parallel legal/financial review → director approval → digital signing → archival → end) serves as the primary validation scenario
- Python ecosystem with full web UI including visual workflow designer, user inboxes, and monitoring dashboards
- Internal/personal use — not a SaaS product

## Constraints

- **Tech stack**: Python backend — framework to be determined by research (Django/FastAPI)
- **Frontend**: Full web UI with visual workflow designer (drag-and-drop), inbox, dashboards
- **Document storage**: Must support file upload, versioning, and package attachment to workflows
- **Background processing**: Needs a task queue/worker system for Process Engine and Workflow Agent

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python backend | User preference | — Pending |
| Full web UI with visual designer | Need drag-and-drop workflow design like Process Builder | — Pending |
| REST/webhook over legacy protocols | Modern alternative to JMS/SOAP/FTP integration | — Pending |
| Near-complete Documentum replication | All use cases in spec must work smoothly | — Pending |

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
*Last updated: 2026-04-06 — Phase 12 complete (Navigation & App Shell)*
