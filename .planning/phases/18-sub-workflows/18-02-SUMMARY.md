---
phase: 18-sub-workflows
plan: "02"
subsystem: workflow-engine
tags: [sub-workflow, engine, event-bus, template-validation]
dependency_graph:
  requires: [18-01]
  provides: [sub-workflow-dispatch, parent-resumption, depth-validation]
  affects: [engine_service, template_service, event_handlers]
tech_stack:
  added: []
  patterns: [event-driven-parent-resumption, recursive-workflow-spawn, depth-limit-enforcement]
key_files:
  created: []
  modified:
    - src/app/services/engine_service.py
    - src/app/services/template_service.py
    - src/app/services/event_handlers.py
    - tests/test_sub_workflows.py
    - pyproject.toml
decisions:
  - "Event handler does NOT pre-mark parent activity as COMPLETE before calling _advance_from_activity -- the function handles the state transition internally"
  - "Depth limit checked at both install time (cycle detection) and runtime (nesting_depth check)"
  - "Variable mapping uses parent var_context built from process variables, maps to child initial_variables"
metrics:
  duration: "33min"
  completed: "2026-04-06"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
---

# Phase 18 Plan 02: Sub-Workflow Engine Logic Summary

SUB_WORKFLOW dispatch with variable mapping, event-driven parent resumption, and cycle/depth validation at template install and runtime.

## What Was Built

### Task 1: SUB_WORKFLOW Engine Dispatch and Template Depth Validation

- Added `SUB_WORKFLOW` branch in `_advance_from_activity` (engine_service.py):
  - Resolves variable_mapping from parent process variables to child initial_variables
  - Checks runtime depth limit against `settings.max_sub_workflow_depth`
  - Calls `start_workflow` recursively for the child template
  - Sets `parent_workflow_id`, `parent_activity_instance_id`, `nesting_depth` on child
  - Parent activity stays ACTIVE until child completes

- Added `_check_sub_workflow_depth` helper (template_service.py):
  - Recursive DFS traversal detecting circular sub-workflow references
  - Enforces max nesting depth at template install time
  - Returns (ok, error_message) tuple

- Added `MISSING_SUB_TEMPLATE` validation in `validate_template`:
  - Every SUB_WORKFLOW activity must have non-null `sub_template_id`

- Added depth/cycle check in `install_template` before activating template

### Task 2: Event Handlers and Tests

- Added `@event_bus.on("workflow.completed")` handler `_resume_parent_on_child_complete`:
  - Loads child workflow, checks for parent linkage
  - Loads parent workflow, template, activity instances, and variables
  - Calls `_advance_from_activity` on the parent to continue past SUB_WORKFLOW

- Added `@event_bus.on("workflow.failed")` handler `_fail_parent_on_child_failure`:
  - Marks parent activity as ERROR when child fails

- Implemented 8 passing tests (6 new, 2 existing from Plan 01):
  - test_create_sub_workflow_activity (SUBWF-01)
  - test_workflow_instance_parent_fields (SUBWF-01)
  - test_sub_workflow_spawns_child (SUBWF-02)
  - test_parent_resumes_on_child_complete (SUBWF-03)
  - test_variable_mapping_parent_to_child (SUBWF-04)
  - test_depth_limit_rejected (SUBWF-05)
  - test_child_failure_propagates_to_parent
  - test_runtime_depth_limit_exceeded

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed pytest pythonpath resolution for worktree**
- **Found during:** Task 2 test execution
- **Issue:** pytest loaded app modules from the main repo (editable install) instead of the worktree
- **Fix:** Added `pythonpath = ["src"]` to pyproject.toml [tool.pytest.ini_options]
- **Files modified:** pyproject.toml
- **Commit:** f6c5e64

**2. [Rule 1 - Bug] Fixed event handler double-completing parent activity**
- **Found during:** Task 2 test_parent_resumes_on_child_complete
- **Issue:** Event handler set parent_ai.state = COMPLETE, then _advance_from_activity tried COMPLETE -> COMPLETE transition (invalid)
- **Fix:** Removed pre-completion from handler; _advance_from_activity handles the ACTIVE -> COMPLETE transition itself
- **Files modified:** src/app/services/event_handlers.py
- **Commit:** f6c5e64

## Decisions Made

1. **Event handler delegates state transition to _advance_from_activity** -- The handler does not mark the parent activity as COMPLETE before calling `_advance_from_activity`. The function already handles ACTIVE -> COMPLETE transition internally.

2. **Depth validation at two layers** -- Cycle detection and depth limit enforcement happen at template installation time (preventing bad templates) AND at runtime (preventing depth exceeded during execution).

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 5bcedaf | SUB_WORKFLOW engine dispatch and template depth validation |
| 2 | f6c5e64 | Event handlers for parent resumption and sub-workflow tests |

## Known Stubs

None -- all functionality is fully wired.

## Self-Check: PASSED
