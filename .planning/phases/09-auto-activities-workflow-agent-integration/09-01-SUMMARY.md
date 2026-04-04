---
phase: 09-auto-activities-workflow-agent-integration
plan: 01
subsystem: auto-methods
tags: [auto-activity, registry, context, engine, smtp]
dependency_graph:
  requires: [04-process-engine-core, 07-document-lifecycle-acl]
  provides: [auto-method-registry, activity-context, execution-log-model, engine-auto-handling]
  affects: [engine_service, models]
tech_stack:
  added: [httpx-for-external-api]
  patterns: [decorator-registry, dataclass-context, lazy-import]
key_files:
  created:
    - src/app/auto_methods/__init__.py
    - src/app/auto_methods/context.py
    - src/app/auto_methods/builtin.py
    - src/app/models/execution_log.py
  modified:
    - src/app/core/config.py
    - src/app/models/__init__.py
    - src/app/services/engine_service.py
decisions:
  - Decorator-based registry pattern for auto method discovery
  - ActivityContext uses dataclass (not Pydantic) for lightweight DB session passing
  - Dev-mode email logging when smtp_host is empty string
  - AUTO activities left in ACTIVE state for Celery pickup (not auto-completed)
metrics:
  duration: 3min
  completed: "2026-04-04"
---

# Phase 9 Plan 1: Auto Method Registry, Context, and Engine Handling Summary

Decorator-based auto method registry with four built-in methods, ActivityContext for variable/document access, AutoActivityLog model for execution tracking, and engine updated to leave AUTO activities ACTIVE for Celery pickup.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Auto method registry, ActivityContext, built-in methods, Settings update | ae52eed | auto_methods/__init__.py, context.py, builtin.py, config.py |
| 2 | AutoActivityLog model and engine AUTO handling | 1804fd0 | execution_log.py, models/__init__.py, engine_service.py |

## What Was Built

### Auto Method Registry (src/app/auto_methods/__init__.py)
- `@auto_method(name)` decorator registers async functions in module-level dict
- `get_auto_method(name)` retrieves callable by name (returns None if not found)
- `list_auto_methods()` returns all registered method names
- Auto-imports builtin module at bottom to trigger registration

### ActivityContext (src/app/auto_methods/context.py)
- Dataclass with db session, workflow/activity instances, variables dict, document_ids
- `get_variable(name)` reads from in-memory snapshot
- `set_variable(name, value)` updates in-memory AND persists to ProcessVariable table
- Handles typed column mapping (string, int, bool, date) matching engine_service pattern

### Built-in Auto Methods (src/app/auto_methods/builtin.py)
1. **send_email** - Dev mode logs, prod mode uses SMTP via asyncio.to_thread
2. **change_lifecycle_state** - Transitions all workflow documents via lifecycle_service
3. **modify_acl** - Add/remove ACL entries via acl_service for each document
4. **call_external_api** - POST to external URL with workflow context, stores response in variables

### AutoActivityLog Model (src/app/models/execution_log.py)
- Tracks activity_instance_id, method_name, attempt_number, status, errors, timing, result_data
- Status values: success, error, timeout, skipped
- Indexed on activity_instance_id for efficient querying

### Engine AUTO Handling (src/app/services/engine_service.py)
- New `elif ActivityType.AUTO: pass` clause between START/END and MANUAL handling
- AUTO activities are activated (state=ACTIVE, started_at set) but NOT auto-completed
- Celery Workflow Agent (Plan 02) will discover and execute them

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- `list_auto_methods()` returns exactly 4 methods: send_email, change_lifecycle_state, modify_acl, call_external_api
- `ActivityContext` importable from app.auto_methods.context
- `AutoActivityLog` importable from app.models and app.models.execution_log
- Engine service has explicit `ActivityType.AUTO` handling with pass (leave ACTIVE)
- Settings has smtp_host config with empty string default

## Known Stubs

None - all methods are fully implemented (send_email has working dev/prod modes, external API uses httpx).
