# Phase 5: Work Items & Inbox - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 05-work-items-inbox
**Areas discussed:** Inbox API design, Rejection & comments, Performer assignment, Work item lifecycle

---

## Inbox API Design

### Endpoint Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated /inbox | Separate user-facing endpoint with rich context | |
| Extend /work-items | Generic endpoint with filters | |
| Both | Dedicated /inbox for users, /work-items for admin | ✓ |

**User's choice:** Both
**Notes:** Clean separation between user inbox and admin queries.

### Filtering & Sorting

| Option | Description | Selected |
|--------|-------------|----------|
| Essential filters | State, priority, workflow template. Sort by priority, due_date, created_at | ✓ |
| Rich filters | Essential + date range, activity name, keyword search | |
| Minimal | Just state filter and default sort | |

**User's choice:** Essential filters

### Item Detail Level

| Option | Description | Selected |
|--------|-------------|----------|
| Nested response | Full context in one call: activity info + workflow + documents | ✓ |
| Separate detail endpoint | List basic, detail separate | |
| Expandable | Query param to control includes | |

**User's choice:** Nested response

---

## Rejection & Comments

### Rejection Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Mark + defer flows | Mark as REJECTED, audit it, flow routing in Phase 6 | ✓ |
| Full reject flow now | Find reject flow and route back immediately | |
| Reject = halt | Set activity to ERROR, halt workflow | |

**User's choice:** Mark + defer flows

### Comment Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated table | work_item_comments with proper FKs | ✓ |
| JSON column | Comments JSON array on work_items table | |
| Audit entries | Store as audit_log records | |

**User's choice:** Dedicated comments table

---

## Performer Assignment

### Group Assignment

| Option | Description | Selected |
|--------|-------------|----------|
| One per member | Separate work item for each group member (parallel) | ✓ |
| Shared claimable | One item visible to all, first to claim owns it | |
| Configurable | Activity-level group_mode field | |

**User's choice:** One per member

### Resolution Location

| Option | Description | Selected |
|--------|-------------|----------|
| Engine service | Add resolve_performers() to engine_service.py | ✓ |
| Separate service | New performer_service.py | |
| Inline | Logic at work item creation point | |

**User's choice:** Engine service

---

## Work Item Lifecycle

### Claiming Requirement

| Option | Description | Selected |
|--------|-------------|----------|
| Require claiming | Must acquire before complete/reject | ✓ |
| Direct complete | No claiming needed | |
| Optional claiming | Available but not required | |

**User's choice:** Require claiming

### Release Support

| Option | Description | Selected |
|--------|-------------|----------|
| Allow release | ACQUIRED -> AVAILABLE, clear performer | ✓ |
| No release | Once claimed, must finish | |
| Admin-only release | Only admins can unclaim | |

**User's choice:** Allow release

---

## Claude's Discretion

- Comment model schema details
- Inbox Pydantic schema nesting
- Engine service integration approach
- Migration strategy
- Test fixture design

## Deferred Ideas

None — discussion stayed within phase scope
