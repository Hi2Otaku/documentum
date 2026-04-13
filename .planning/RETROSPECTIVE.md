# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v1.2 — Advanced Engine & Document Platform

**Shipped:** 2026-04-13
**Phases:** 11 (16–26) | **Plans:** 26 | **Tasks:** 45
**Python:** ~17,400 LOC | **TypeScript:** ~13,800 LOC
**Timeline:** 2026-03-30 → 2026-04-13 (~14 days)

### What Was Built

- Domain event bus (Redis pub/sub + persistent `events` table) as the v1.2 architectural keystone
- In-app and email notification framework: unread badge, notification list, mark-read, Celery email dispatch
- Timer activities: deadline configuration on ActivityTemplate, Celery Beat overdue detection, escalation actions
- Sub-workflow spawning with parent pause/resume, variable mapping, depth-limit recursion guard
- Event-driven activities (`ActivityType.EVENT`) that auto-complete on domain event match
- Document renditions: LibreOffice headless PDF + Pillow thumbnail generation via isolated Celery worker
- Virtual documents: child assembly, drag-and-drop reordering, cycle detection via PostgreSQL recursive CTE, merged PDF
- Retention policies and legal holds blocking premature document deletion
- PKCS7/CMS digital signatures with post-signing version immutability
- Infrastructure wiring phases (24–26): linearized Alembic migration chain, all routers mounted, all tests passing

### What Worked

- **Event-first build order** — building the event bus in Phase 16 before any consuming feature meant all 6 event-consuming features (timers, sub-workflows, event activities, renditions, notifications, lifecycle) had a shared integration layer from day one. No retroactive wiring required.
- **Separate gap-closure phases** — Phases 24–26 as dedicated integration/alignment phases (not retrofitted into feature phases) kept feature design clean and isolated the wiring work into auditable, focused plans.
- **Celery Beat polling pattern** — consistent use of database-backed Beat polling (not `apply_async(eta=...)`) across timers, sub-workflow completion, and event processing meant all time-based logic survived worker restarts.
- **Milestone audit before completion** — running the audit (v1.2-MILESTONE-AUDIT.md) before declaring done surfaced the 8 integration gaps that became phases 24–26. Without the audit, those gaps would have shipped silently.

### What Was Inefficient

- **Feature phases written without wiring** — Phases 16–23 produced code that wasn't fully wired into the application (missing router mounts, missing event handler imports, missing model exports). This caused a second pass (phases 24–26). Better practice: each feature phase should include a wiring task.
- **one_liner field not populated in SUMMARY.md** — the `summary-extract --fields one_liner` tool returned null for most summaries because the one_liner field wasn't written consistently. Milestone stats extraction was therefore sparse.

### Patterns Established

- Build event bus first when multiple features share an event integration layer
- Gap-closure phases (decimal or integer) are a legitimate pattern — not a sign of failure
- Audit before milestone completion is non-negotiable; it reliably surfaces integration debt
- Each feature phase should include: (1) models, (2) service, (3) router, (4) router mount in main.py, (5) event wiring — all in a single phase to avoid orphaned code

### Key Lessons

- **Wiring is a feature.** Mounting a router and registering an event handler is not boilerplate — it is part of the feature. Treat it as a required task in the phase plan, not an afterthought.
- **Beat polling > ETA tasks.** Every time-based operation (deadline check, sub-workflow poll, disposition) was implemented with database-backed Beat polling. None of them broke on worker restart.
- **PostgreSQL recursive CTEs for graph problems** — virtual document cycle detection used a recursive CTE at the service layer. Correct and fast; no application-level graph traversal needed.

---

## Cross-Milestone Trends

| Milestone | Phases | Plans | Python LOC | TS LOC | Shipped |
|-----------|--------|-------|-----------|--------|---------|
| v1.0 Core Engine | 11 | 47 | ~10,000 | — | 2026-03-30 |
| v1.1 Full Frontend | 4 | 4 | ~11,000 | ~9,000 | 2026-04-06 |
| v1.2 Advanced Engine | 11 | 26 | ~17,400 | ~13,800 | 2026-04-13 |
| v1.3 Document-Centric | TBD | TBD | — | — | — |
