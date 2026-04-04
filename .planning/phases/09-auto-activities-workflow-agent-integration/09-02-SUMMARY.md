---
phase: 09-auto-activities-workflow-agent-integration
plan: 02
subsystem: workflow-agent
tags: [celery, workflow-agent, auto-activity, retry, skip]
dependency_graph:
  requires: [09-01-auto-method-registry]
  provides: [celery-app, poll-task, execute-task, retry-endpoint, skip-endpoint]
  affects: [workflows-router, workflow-schemas]
tech_stack:
  added: [celery-beat-schedule]
  patterns: [asyncio-run-bridge, session-per-task, exponential-backoff]
key_files:
  created:
    - src/app/celery_app.py
    - src/app/tasks/__init__.py
    - src/app/tasks/auto_activity.py
  modified:
    - src/app/routers/workflows.py
    - src/app/schemas/workflow.py
decisions:
  - asyncio.run bridges Celery sync tasks to async DB/method execution
  - Separate error session (async_session_factory) after rollback for error logging
  - Row-level locking (with_for_update skip_locked) for PostgreSQL; sqlite fallback for tests
  - ERROR->ACTIVE->COMPLETE two-step transition for skip (uses existing valid transitions)
metrics:
  duration: 3min
  completed: "2026-04-04"
---

# Phase 9 Plan 2: Celery App, Workflow Agent Tasks, and Admin Retry/Skip Summary

Celery app module with Redis broker and 10-second beat poll schedule, Workflow Agent tasks (poll + execute) with 3-retry exponential backoff and timeout handling, and admin retry/skip endpoints for failed auto activities.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Celery app and Workflow Agent tasks (poll + execute) | 91ed8c8 | celery_app.py, tasks/auto_activity.py |
| 2 | Admin retry and skip endpoints for failed auto activities | 075d25e | routers/workflows.py, schemas/workflow.py |

## What Was Built

### Celery App (src/app/celery_app.py)
- Celery instance named "documentum" with Redis broker matching Docker Compose config
- JSON serialization, UTC timezone, late ack, prefetch=1 for reliable execution
- Beat schedule: poll-auto-activities every 10.0 seconds
- Matches `celery -A app.celery_app worker` and `celery -A app.celery_app beat` from docker-compose.yml

### Workflow Agent Tasks (src/app/tasks/auto_activity.py)
- `poll_auto_activities`: periodic beat task that queries ACTIVE AUTO ActivityInstances, dispatches execute tasks
  - PostgreSQL row-level locking (with_for_update skip_locked) prevents duplicate dispatch
  - SQLite fallback (no locking) for test compatibility
- `execute_auto_activity`: bound task with bind=True, max_retries=3, soft_time_limit=60
  - Loads activity instance, template, workflow, variables, documents
  - Builds ActivityContext and calls registered auto method
  - On success: logs result, advances workflow via _advance_from_activity
  - On error: logs error with traceback, retries with exponential backoff (10s, 30s, 90s)
  - After 3 failed attempts: marks ActivityState.ERROR
  - On timeout (SoftTimeLimitExceeded): treated as error with timeout status
  - Separate error sessions after rollback to persist error logs

### Admin Retry Endpoint (POST /workflows/{id}/activities/{id}/retry)
- Validates activity is in ERROR state
- Resets state to ACTIVE for Workflow Agent re-pickup on next poll cycle
- Creates audit record with action "auto_activity_retried"

### Admin Skip Endpoint (POST /workflows/{id}/activities/{id}/skip)
- Validates activity is in ERROR state
- Transitions ERROR->ACTIVE->COMPLETE (two-step using existing valid transitions)
- Loads full template and builds advancement context
- Calls _advance_from_activity to advance workflow past skipped activity
- Creates AutoActivityLog with status="skipped"
- Creates audit record with action "auto_activity_skipped"

### New Schemas (src/app/schemas/workflow.py)
- `AutoActivityLogResponse`: log entry details (id, method_name, attempt_number, status, errors, timing)
- `ActivityRetryResponse`: retry/skip result (activity_instance_id, status, message)

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- `from app.celery_app import celery_app` succeeds, main == "documentum"
- Beat schedule contains "poll-auto-activities" at 10.0s interval
- `from app.tasks.auto_activity import poll_auto_activities, execute_auto_activity` succeeds
- Retry and skip endpoints present in workflows router
- AutoActivityLogResponse and ActivityRetryResponse schemas importable
- All grep acceptance criteria pass (ActivityState.ERROR, audit actions, async_session_factory, etc.)

## Known Stubs

None - all functionality is fully implemented.
