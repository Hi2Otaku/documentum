---
phase: 11-dashboards-query-interface-validation
plan: 03
subsystem: testing
tags: [contract-approval, e2e, integration-test, seed-script, workflow-validation]

requires:
  - phase: 04-process-engine-core
    provides: workflow execution engine with token-based advancement
  - phase: 05-work-items-inbox
    provides: work item creation and inbox completion
  - phase: 06-advanced-routing-alias-sets
    provides: parallel routing, reject flows, performer-chosen routing

provides:
  - Contract approval seed script for live E2E demos
  - Integration tests proving all routing types work together in a single workflow
  - Validation that the full Documentum workflow engine executes the 7-step example correctly

affects: [11-04, 11-05]

tech-stack:
  added: []
  patterns:
    - "Direct engine_service advancement for auto activities in tests (no Celery)"
    - "Fixture-based template construction for complex multi-activity workflows"

key-files:
  created:
    - scripts/__init__.py
    - scripts/seed_contract_approval.py
    - tests/test_contract_approval.py
  modified: []

key-decisions:
  - "Auto activities advanced manually in tests via engine_service._advance_from_activity since no Celery worker runs in test context"
  - "Tests use workflow API complete_work_item (engine_service direct route) which does not require ACQUIRED state, avoiding acquire/complete dance in tests"
  - "Seed script uses inbox API with acquire+complete flow for production realism"

patterns-established:
  - "Complex workflow test fixture: contract_approval_template builds 8 activities, 9 flows, variables, validates, installs"
  - "Auto activity test pattern: manually call _advance_from_activity to simulate Workflow Agent"

requirements-completed: [EXAMPLE-01, EXAMPLE-02, EXAMPLE-03]

duration: 5min
completed: 2026-04-04
---

# Phase 11 Plan 03: Contract Approval E2E Summary

**7-step contract approval seed script and integration tests validating sequential, parallel, conditional, and reject routing in a single end-to-end workflow execution**

## What Was Built

### Seed Script (scripts/seed_contract_approval.py)
- Async CLI script using httpx to call REST APIs
- Creates 4 test users (drafter, lawyer, accountant, director)
- Builds 7-step template: Initiate -> Draft Contract -> Legal Review + Financial Review (parallel) -> Director Approval (AND-join, performer-chosen) -> Digital Signing (auto) -> Archival (auto) -> End
- Starts workflow and completes all manual steps via inbox API
- Retry-based polling for auto activity completion (up to 60s)
- Runnable as `python -m scripts.seed_contract_approval`

### Integration Tests (tests/test_contract_approval.py)
- **test_contract_approval_template_creation (EXAMPLE-01)**: Verifies 8 activities with correct type distribution (1 start, 4 manual, 2 auto, 1 end)
- **test_contract_approval_routing_types (EXAMPLE-02)**: Verifies parallel split (2 outgoing from Draft), AND-join on Director (2 incoming + trigger_type), performer-chosen routing with "Approve" label, reject flow to Draft Contract
- **test_contract_approval_e2e_execution (EXAMPLE-03)**: Full execution proving parallel activation, AND-join gating, performer-chosen path selection, auto activity advancement, FINISHED state, and audit trail (5+ entries)

## Deviations from Plan

None - plan executed exactly as written. Tests passed on first run without requiring fixes.

## Self-Check: PASSED
