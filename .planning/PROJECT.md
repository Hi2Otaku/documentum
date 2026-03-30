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

### Active

- [ ] Workflow template design (dm_process equivalent) with visual drag-and-drop designer
- [ ] Manual activities with configurable performer assignment (supervisor, specific user, group, sequential performers, runtime selection)
- [ ] Auto activities executing server-side methods (Python equivalents of dm_method)
- [ ] Alias sets for flexible performer mapping without hardcoding users
- [ ] Flow routing: sequential, parallel, conditional (performer-chosen, broadcast, condition-based)
- [ ] Reject flows allowing documents to loop back to previous activities
- [ ] Workflow instance lifecycle: Dormant → Running → Halted → Failed → Finished
- [ ] Work items appearing in user inboxes (dmi_queue_item equivalent)
- [ ] Document management: upload, versioning, packages attached to workflows
- [ ] Delegation: users mark unavailable, tasks auto-route to delegates
- [ ] Work queues: shared task pools where any qualified user can claim tasks
- [ ] Trigger conditions: AND-join and OR-join for activities with multiple incoming flows
- [ ] Process variables: read/write by activities, usable in routing conditions
- [ ] Process Engine: background runtime executing workflow instances
- [ ] Workflow Agent: background daemon executing auto activities
- [ ] Lifecycle management: document states (Draft → Review → Approved → Archived) with workflow-triggered transitions
- [ ] Audit trail: full logging of who did what, when, with what decision
- [ ] ACL/Security integration: automatic permission changes at workflow steps
- [ ] BAM dashboards: real-time process metrics, bottleneck detection, SLA compliance
- [ ] External system integration capability (webhook/API-based)
- [ ] Contract approval example workflow running end-to-end (the full 7-step example from the spec)
- [ ] DQL-like query interface for workflow administration

### Out of Scope

- xCP platform bundling (Composer, TaskSpace as separate products) — too broad, focus on workflow engine
- xCelerators industry templates — domain-specific templates are beyond v1
- Process Integrator protocol support (JMS, FTP, SOAP) — use modern REST/webhook instead
- Mobile native app — web-responsive UI is sufficient

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
*Last updated: 2026-03-30 after Phase 1 completion*
