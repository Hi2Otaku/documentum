---
phase: 04-process-engine-core
plan: 03
subsystem: testing
tags: [pytest, integration-tests, expression-evaluator, workflow-engine, async]

requires:
  - phase: 04-02
    provides: "Engine service, workflow router, 7 endpoints"
  - phase: 04-01
    provides: "ExecutionToken model, enums, schemas, expression evaluator"
provides:
  - "36 expression evaluator unit tests (validation + evaluation + security)"
  - "15 workflow integration tests covering EXEC-01 through EXEC-14"
  - "3 reusable workflow template fixtures (installed, parallel, sequential)"
affects: [05-manual-activities, 06-auto-activities, testing]

tech-stack:
  added: []
  patterns:
    - "Fixture-based template creation via HTTP API for integration tests"
    - "Pass variables explicitly to avoid lazy-load in async context"

key-files:
  created:
    - tests/test_expression_evaluator.py
    - tests/test_workflows.py
  modified:
    - tests/conftest.py
    - src/app/services/expression_evaluator.py
    - src/app/services/engine_service.py
    - src/app/services/template_service.py
    - src/app/schemas/template.py

key-decisions:
  - "AST Tuple node added to ALLOWED_NODES for 'in' operator support in expressions"
  - "FlowTemplate condition_expression accepts both string (AST) and dict (JSON) formats"
  - "Template validation tries AST expression validation before JSON condition validation"
  - "Variables passed explicitly to advancement loop instead of assigning to relationship"

patterns-established:
  - "Explicit variable passing: avoid assigning to SQLAlchemy relationships in async context to prevent lazy-load errors"
  - "Dual condition format: flow conditions support both AST string expressions and legacy JSON dicts"

requirements-completed: [EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05, EXEC-06, EXEC-07, EXEC-12, EXEC-13, EXEC-14]

duration: 10min
completed: 2026-03-30
---

# Phase 04 Plan 03: Process Engine Tests Summary

**51 tests proving all EXEC requirements: expression evaluator sandbox (36 unit tests), workflow lifecycle/routing/variables (15 integration tests), with 4 engine bug fixes discovered and resolved during testing**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-30T14:33:07Z
- **Completed:** 2026-03-30T14:43:08Z
- **Tasks:** 2/2
- **Files modified:** 7

## Accomplishments

### Task 1: Expression Evaluator Unit Tests + Fixtures
- **Commit:** 80ebbbb
- Created 36 unit tests for AST-based expression evaluator
  - 17 validation tests (valid expressions + security rejections for calls, imports, attributes, subscripts, lambda, comprehensions)
  - 19 evaluation tests (comparisons, boolean ops, arithmetic, string equality, in operator, missing variable error, complex expressions)
- Added 3 reusable fixtures to conftest.py:
  - `installed_template`: start -> manual -> end (validated + installed)
  - `parallel_template`: start -> [reviewA, reviewB] (AND-join) -> merge -> end
  - `sequential_3step_template`: start -> step1 -> step2 -> step3 -> end

### Task 2: Workflow Integration Tests
- **Commit:** 3a1f4dc
- Created 15 HTTP integration tests covering all 10 EXEC requirements:
  - EXEC-01: Start workflow (positive + 2 negative cases)
  - EXEC-02: Document attachment at startup
  - EXEC-03: Performer overrides
  - EXEC-04: State transitions (running -> finished)
  - EXEC-05: Auto-advance through start activity
  - EXEC-06: Sequential A->B->C routing (3-step)
  - EXEC-07: Parallel AND-split/AND-join
  - EXEC-12: OR-join fires on first completion + double-activation guard
  - EXEC-13: Process variable read/write via API
  - EXEC-14: Condition expression routing based on variable values

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ast.Tuple missing from ALLOWED_NODES**
- **Found during:** Task 1
- **Issue:** `in` operator with tuple literals (e.g., `status in ('approved', 'pending')`) creates ast.Tuple nodes not in the whitelist
- **Fix:** Added `ast.Tuple` to ALLOWED_NODES set
- **Files modified:** src/app/services/expression_evaluator.py
- **Commit:** 80ebbbb

**2. [Rule 1 - Bug] Lazy-load MissingGreenlet on process_variables assignment**
- **Found during:** Task 2
- **Issue:** `workflow.process_variables = instance_variables` triggers lazy-load of old value in async context, raising MissingGreenlet
- **Fix:** Pass variables as explicit parameter to `_advance_from_activity` instead of assigning to relationship
- **Files modified:** src/app/services/engine_service.py
- **Commit:** 3a1f4dc

**3. [Rule 1 - Bug] ACTIVE->ACTIVE invalid state transition on work item completion**
- **Found during:** Task 2
- **Issue:** `_advance_from_activity` always tried DORMANT->ACTIVE transition, but activities are already ACTIVE when called from `complete_work_item`
- **Fix:** Skip DORMANT->ACTIVE transition if activity is already ACTIVE
- **Files modified:** src/app/services/engine_service.py
- **Commit:** 3a1f4dc

**4. [Rule 1 - Bug] FlowTemplate condition_expression only accepted dict, not string expressions**
- **Found during:** Task 2
- **Issue:** FlowTemplateCreate schema typed `condition_expression` as `dict[str, Any]`, rejecting AST string expressions like `"amount > 1000"`; template validation also only checked JSON format
- **Fix:** Updated schema to accept `str | dict`, updated template_service to store strings directly, updated validation to try AST validation before JSON fallback
- **Files modified:** src/app/schemas/template.py, src/app/services/template_service.py
- **Commit:** 3a1f4dc

## Test Results

- Expression evaluator: 36/36 passed
- Workflow integration: 15/15 passed
- Full test suite: 150/150 passed (zero regressions)

## Known Stubs

None -- all tests exercise real endpoints with real data flow.

## Self-Check: PASSED

- All 7 key files exist
- Both task commits (80ebbbb, 3a1f4dc) found in git log
- Full test suite: 150/150 passed
