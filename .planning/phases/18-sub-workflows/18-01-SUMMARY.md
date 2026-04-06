---
phase: 18-sub-workflows
plan: 01
subsystem: workflow-engine
tags: [sub-workflows, data-layer, enum, migration, schemas]
dependency_graph:
  requires: []
  provides: [SUB_WORKFLOW-enum, sub-workflow-model-columns, sub-workflow-schemas, depth-limit-config]
  affects: [activity_templates, workflow_instances, process_templates]
tech_stack:
  added: []
  patterns: [self-referential-FK, ambiguous-FK-resolution]
key_files:
  created:
    - alembic/versions/phase18_001_sub_workflows.py
    - tests/test_sub_workflows.py
  modified:
    - src/app/models/enums.py
    - src/app/models/workflow.py
    - src/app/core/config.py
    - src/app/schemas/template.py
    - src/app/schemas/workflow.py
decisions:
  - "Used string-based foreign_keys on ProcessTemplate.activity_templates to resolve ambiguity from dual FK paths"
  - "Added parent_workflow_id as self-referential FK on workflow_instances for parent-child hierarchy"
metrics:
  duration: 2m
  completed: "2026-04-06"
---

# Phase 18 Plan 01: Sub-Workflow Data Layer Summary

SUB_WORKFLOW activity type enum, model columns, migration, Pydantic schemas, config depth limit, and test scaffold.

## What Was Done

### Task 1: Add SUB_WORKFLOW enum, model columns, migration, and config
- Added `SUB_WORKFLOW = "sub_workflow"` to `ActivityType` enum
- Added `sub_template_id` (UUID FK to process_templates) and `variable_mapping` (JSON) columns to `ActivityTemplate`
- Added `parent_workflow_id` (UUID self-ref FK), `parent_activity_instance_id` (UUID FK), `nesting_depth` (int, default 0) to `WorkflowInstance`
- Added `max_sub_workflow_depth: int = 5` to `Settings`
- Created migration `phase18_001_sub_workflows.py` with SQLite guard for ALTER TYPE, full upgrade/downgrade

### Task 2: Update Pydantic schemas and create test scaffold
- Added `sub_template_id` and `variable_mapping` to `ActivityTemplateCreate`, `ActivityTemplateUpdate`, `ActivityTemplateResponse`
- Added `parent_workflow_id` and `nesting_depth` to `WorkflowInstanceResponse`, `WorkflowDetailResponse`, `WorkflowAdminListResponse`
- Created `tests/test_sub_workflows.py` with 7 test functions (2 passing, 5 skipped stubs for Plan 02)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ambiguous FK on ProcessTemplate.activity_templates relationship**
- **Found during:** Task 2 (test run)
- **Issue:** Adding `sub_template_id` FK to `ActivityTemplate` created a second FK path to `process_templates`, causing SQLAlchemy `AmbiguousForeignKeysError` on the `ProcessTemplate.activity_templates` relationship
- **Fix:** Added explicit `foreign_keys="[ActivityTemplate.process_template_id]"` to the `ProcessTemplate.activity_templates` relationship, and `foreign_keys=[process_template_id]` to `ActivityTemplate.process_template` relationship
- **Files modified:** `src/app/models/workflow.py`
- **Commit:** 58d4321

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 6d129b1 | feat(18-01): add SUB_WORKFLOW enum, model columns, migration, and config |
| 2 | 58d4321 | feat(18-01): update Pydantic schemas and create test scaffold |

## Known Stubs

Test stubs in `tests/test_sub_workflows.py` (intentional -- implemented in Plan 02):
- `test_sub_workflow_spawns_child` (line ~82)
- `test_parent_resumes_on_child_complete` (line ~88)
- `test_variable_mapping_parent_to_child` (line ~94)
- `test_depth_limit_rejected` (line ~100)
- `test_child_failure_propagates_to_parent` (line ~106)

These stubs are placeholders for Plan 02 engine logic and do not prevent this plan's goal (data layer foundation) from being achieved.

## Self-Check: PASSED

All 7 created/modified files verified present. Both commit hashes (6d129b1, 58d4321) confirmed in git log.
