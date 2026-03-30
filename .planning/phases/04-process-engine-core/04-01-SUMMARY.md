---
phase: 04-process-engine-core
plan: 01
subsystem: database
tags: [sqlalchemy, pydantic, alembic, ast, enums, workflow-engine]

# Dependency graph
requires:
  - phase: 03-template-management
    provides: ProcessTemplate, ActivityTemplate, FlowTemplate, ProcessVariable models and CRUD
provides:
  - ActivityState enum with 5 states (dormant, active, paused, complete, error)
  - ExecutionToken model for parallel routing token tracking
  - Bidirectional relationships on all workflow instance models
  - Pydantic schemas for workflow start, complete, detail responses
  - AST-based expression evaluator with whitelist sandbox
  - Alembic migration for ActivityInstance.state enum conversion and execution_tokens table
affects: [04-02-engine-service, 04-03-workflow-router, process-engine, workflow-agent]

# Tech tracking
tech-stack:
  added: []
  patterns: [ast-whitelist-sandbox, viewonly-relationship-with-secondary-join]

key-files:
  created:
    - src/app/schemas/workflow.py
    - src/app/services/expression_evaluator.py
    - alembic/versions/a1b2c3d4e5f6_add_activity_state_enum_and_execution_tokens.py
  modified:
    - src/app/models/enums.py
    - src/app/models/workflow.py
    - src/app/models/__init__.py

key-decisions:
  - "Viewonly relationships (WorkflowInstance.work_items, WorkItem.workflow_instance) use secondary join through activity_instances table since no direct FK exists"
  - "Expression evaluator uses compile+eval with __builtins__={} for sandboxed execution"

patterns-established:
  - "AST whitelist pattern: validate expression AST nodes against allowed set before eval"
  - "Secondary join pattern: viewonly relationships through intermediate tables for indirect FK paths"

requirements-completed: [EXEC-04, EXEC-07, EXEC-12, EXEC-13, EXEC-14]

# Metrics
duration: 5min
completed: 2026-03-30
---

# Phase 4 Plan 1: Process Engine Data Layer Summary

**ActivityState enum, ExecutionToken model, workflow instance relationships, Pydantic schemas, and AST-based expression evaluator for process engine foundation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-30T14:20:33Z
- **Completed:** 2026-03-30T14:25:10Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- ActivityState enum with 5 states added to enums module, replacing string-based ActivityInstance.state
- ExecutionToken model created for tracking flow traversals in parallel routing scenarios
- Bidirectional relationships added to all workflow instance models (WorkflowInstance, ActivityInstance, WorkItem, ProcessVariable, WorkflowPackage)
- 8 Pydantic schemas created for workflow API operations (start, complete, update variable, responses)
- AST-based expression evaluator with whitelist sandbox for safe condition evaluation on flows
- Alembic migration for String-to-Enum conversion on ActivityInstance.state and new execution_tokens table

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ActivityState enum, ExecutionToken model, instance relationships, and Alembic migration** - `1ba6187` (feat)
2. **Task 2: Create Pydantic schemas and expression evaluator** - `60a2a06` (feat)

## Files Created/Modified
- `src/app/models/enums.py` - Added ActivityState enum with 5 states
- `src/app/models/workflow.py` - Added ExecutionToken model, bidirectional relationships on all instance models, ActivityState enum for ActivityInstance.state
- `src/app/models/__init__.py` - Exported ActivityState and ExecutionToken
- `src/app/schemas/workflow.py` - 8 Pydantic schemas for workflow API operations
- `src/app/services/expression_evaluator.py` - AST-based expression evaluator with whitelist sandbox
- `alembic/versions/a1b2c3d4e5f6_add_activity_state_enum_and_execution_tokens.py` - Migration for enum conversion and new table

## Decisions Made
- Viewonly relationships (WorkflowInstance.work_items, WorkItem.workflow_instance) use secondary join through activity_instances table since there is no direct foreign key between WorkItem and WorkflowInstance
- Expression evaluator uses compile+eval with `__builtins__={}` for sandboxed execution, rejecting function calls, attribute access, imports, and subscripts

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed viewonly relationship join conditions**
- **Found during:** Task 1 (Instance relationships)
- **Issue:** WorkflowInstance.work_items and WorkItem.workflow_instance used `viewonly=True` without specifying join paths, causing NoForeignKeysError since there is no direct FK between these tables
- **Fix:** Added explicit primaryjoin/secondary/secondaryjoin through the activity_instances intermediate table
- **Files modified:** src/app/models/workflow.py
- **Verification:** All 99 existing tests pass
- **Committed in:** 1ba6187 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for model relationships to work correctly. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All data contracts ready for Plan 02 (engine service implementation)
- ActivityState enum enables state machine logic in engine service
- ExecutionToken model enables parallel routing with AND-join/OR-join tracking
- Expression evaluator ready for conditional flow routing
- Pydantic schemas ready for workflow router endpoints

---
*Phase: 04-process-engine-core*
*Completed: 2026-03-30*
