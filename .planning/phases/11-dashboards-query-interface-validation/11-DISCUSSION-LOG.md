# Phase 11: Dashboards, Query Interface & Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 11-dashboards-query-interface-validation
**Areas discussed:** Dashboard layout & metrics, Real-time update strategy, Query interface design, Contract approval example

---

## Dashboard Layout & Metrics

### Organization

| Option | Description | Selected |
|--------|-------------|----------|
| KPI cards + charts | Top row summary cards, below charts for bottlenecks and workload, bottom SLA | ✓ |
| Full data table with sparklines | Table-first with inline sparklines, more admin-oriented | |
| Tabbed sections | Separate tabs per concern (Overview, Bottlenecks, Workload, SLA) | |

**User's choice:** KPI cards + charts
**Notes:** Clean executive overview layout with summary cards on top and charts below

### SLA Compliance

| Option | Description | Selected |
|--------|-------------|----------|
| Per-activity time limit | Optional expected_duration_hours on activity templates, SLA % from that | ✓ |
| Per-template time limit | Single SLA target on whole workflow template | |
| Both levels | Activity-level AND template-level SLA | |

**User's choice:** Per-activity time limit
**Notes:** Activities without a limit excluded from SLA calculations

### Dashboard Filtering

| Option | Description | Selected |
|--------|-------------|----------|
| Template dropdown filter | Default all templates, dropdown to filter specific template | ✓ |
| Always all templates | Single unified view, no filtering | |
| Template comparison mode | Side-by-side comparison of 2-3 templates | |

**User's choice:** Template dropdown filter

---

## Real-Time Update Strategy

### Live Data Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Periodic polling | REST API fetch every 15-30 seconds | |
| SSE (Server-Sent Events) | Server pushes via StreamingResponse + PostgreSQL LISTEN/NOTIFY | ✓ |
| WebSocket | Bidirectional real-time connection | |

**User's choice:** SSE (Server-Sent Events)
**Notes:** Chose SSE over polling for lower latency, leveraging PostgreSQL LISTEN/NOTIFY

### Metrics Computation

| Option | Description | Selected |
|--------|-------------|----------|
| On-the-fly queries | Live COUNT/AVG queries, always accurate | |
| Pre-aggregated with Celery | Celery beat pre-computes into summary table | |
| Hybrid | KPI counts live, chart data pre-aggregated | ✓ |

**User's choice:** Hybrid
**Notes:** Best of both — KPIs always accurate, charts pre-aggregated for performance

---

## Query Interface Design

### Search UX

| Option | Description | Selected |
|--------|-------------|----------|
| Form-based filters | Structured filter panel with dropdowns, date pickers, entity tabs | ✓ |
| DQL-like text query | Text input for typed queries like SQL | |
| Combined search + filters | Search bar + expandable filter panel | |

**User's choice:** Form-based filters
**Notes:** Three tabs (Workflows, Work Items, Documents) with entity-specific filters

### Result Interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Clickable rows to detail | Click row navigates to full detail view | ✓ |
| Table with expandable rows | Inline expand for details | |
| Table only, no drill-down | Just search results | |

**User's choice:** Clickable rows to detail
**Notes:** Workflow detail shows active activities, work items, audit trail

---

## Contract Approval Example

### Template Creation

| Option | Description | Selected |
|--------|-------------|----------|
| Seed script via API | Python script calling backend APIs, CLI command | ✓ |
| Alembic data migration | Database migration inserting template directly | |
| UI walkthrough guide | Manual step-by-step instructions | |

**User's choice:** Seed script via API
**Notes:** Reproducible and testable via CLI command

### Auto-Activity Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Simulated actions | Signing = set process variable, Archival = lifecycle transition | ✓ |
| Stub/no-op actions | Just log messages | |
| Full realistic actions | Hash generation, MinIO bucket move, read-only ACL | |

**User's choice:** Simulated actions
**Notes:** Uses existing lifecycle APIs for archival, no external dependencies

### Demo Data Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full demo run | Creates template + users + runs workflow + produces audit trail | ✓ |
| Template + users only | Creates template and test users, manual execution | |
| Template only | Just the template definition | |

**User's choice:** Full demo run
**Notes:** One command proves E2E with 4 test users and complete audit trail

---

## Claude's Discretion

- Recharts chart types and styling
- SSE implementation details (event format, reconnection)
- Celery beat interval for metrics aggregation
- Summary table schema
- Detail view layouts
- Seed script error handling
- Filter component choices

## Deferred Ideas

None — discussion stayed within phase scope.
