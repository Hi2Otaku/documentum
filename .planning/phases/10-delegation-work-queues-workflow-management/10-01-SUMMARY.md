---
phase: 10-delegation-work-queues-workflow-management
plan: 01
subsystem: models-schemas
tags: [delegation, work-queues, workflow-management, data-models, schemas, migration]
dependency_graph:
  requires: [01-foundation, 05-work-items]
  provides: [delegation-models, queue-models, admin-schemas, phase10-migration]
  affects: [work-items, user-management, workflow-engine]
tech_stack:
  added: []
  patterns: [work-queue-members-association-table, user-self-referencing-fk]
key_files:
  created:
    - src/app/schemas/queue.py
    - alembic/versions/phase10_001_delegation_queues.py
  modified:
    - src/app/models/enums.py
    - src/app/models/user.py
    - src/app/models/workflow.py
    - src/app/schemas/user.py
    - src/app/schemas/workflow.py
decisions:
  - WorkQueue uses string "User" relationship reference to avoid circular imports
  - work_queue_members uses SQLAlchemy Table (not ORM model) for M2M association
  - User.delegate_id is self-referencing FK without explicit relationship (queried on demand)
  - is_available uses server_default="true" for existing rows compatibility
metrics:
  duration: 4min
  completed: 2026-04-04
---

# Phase 10 Plan 01: Models, Schemas & Migration Summary

Data foundation for delegation, work queues, and workflow admin: enum extensions, User delegation fields, WorkQueue/WorkQueueMember models, queue-aware WorkItem, all Pydantic schemas, and Alembic migration.

## What Was Built

### Task 1: Extend enums and models (ddeae9a)
- Added `QUEUE` to `PerformerType` enum for queue-based performer assignment
- Added `SUSPENDED` to `WorkItemState` enum for halted workflow work items
- Added `is_available` (bool, default True) and `delegate_id` (nullable self-FK) to User model
- Created `WorkQueue` model with name, description, is_active fields and members relationship
- Created `work_queue_members` association Table for M2M queue-user membership
- Added `queue_id` nullable FK on WorkItem pointing to work_queues

### Task 2: Pydantic schemas and Alembic migration (d556acd)
- Created `AvailabilityUpdate` schema for setting user availability and delegate
- Extended `UserResponse` with `is_available` and `delegate_id` fields
- Created `src/app/schemas/queue.py` with WorkQueueCreate, WorkQueueUpdate, WorkQueueResponse, WorkQueueDetailResponse, QueueMemberResponse, WorkQueueMemberAdd
- Added `WorkflowAdminListResponse` (with template_name, started_by_username, active_activity_name) and `WorkflowActionResponse` to workflow schemas
- Created `phase10_001_delegation_queues.py` migration covering all schema changes with PostgreSQL enum extension and SQLite compatibility

## Verification

- All model imports verified: enums, User fields, WorkQueue, work_queue_members, WorkItem.queue_id
- All schema imports verified: AvailabilityUpdate, queue schemas, workflow admin schemas
- 211 existing tests pass (no regressions)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all models and schemas are fully defined with proper types and constraints.

## Self-Check: PASSED

- All 7 files verified present on disk
- Both commits verified: ddeae9a, d556acd
