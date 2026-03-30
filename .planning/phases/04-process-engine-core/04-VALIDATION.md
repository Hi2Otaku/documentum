---
phase: 04
slug: process-engine-core
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-30
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio 0.24.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_workflows.py -q --tb=short` |
| **Full suite command** | `python -m pytest -q --tb=short` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_workflows.py -q --tb=short`
- **After every plan wave:** Run `python -m pytest -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 04-01-01 | 01 | 1 | EXEC-04 | import | `python -c "from app.models.enums import ActivityState; print(ActivityState.DORMANT.value)"` | pending |
| 04-01-02 | 01 | 1 | EXEC-13, EXEC-14 | import | `python -c "from app.services.expression_evaluator import validate_expression, evaluate_expression"` | pending |
| 04-02-01 | 02 | 2 | EXEC-01, EXEC-02, EXEC-03 | import | `python -c "from app.services.engine_service import start_workflow"` | pending |
| 04-02-02 | 02 | 2 | EXEC-05, EXEC-06, EXEC-07, EXEC-12 | import | `python -c "from app.routers.workflows import router"` | pending |
| 04-03-01 | 03 | 3 | ALL EXEC | integration | `pytest tests/test_expression_evaluator.py -x` | pending |
| 04-03-02 | 03 | 3 | ALL EXEC | integration | `pytest tests/test_workflows.py -q` | pending |

*Status: pending / green / red / flaky*

*Note: Waves 1-2 use import-only verification since they produce models, schemas, and services. Wave 3 (Plan 03) creates the full test suite that exercises all EXEC requirements end-to-end.*

---

## Wave 0 Requirements

No Wave 0 plan required. Waves 1-2 produce foundational code verified by import checks. Wave 3 creates the comprehensive test suite. This avoids creating throwaway stubs that would be immediately replaced.

*Existing test infrastructure from Phase 1/2/3 covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Parallel activities run simultaneously | EXEC-07 | Timing-dependent | Start workflow with AND-split, verify both branches active before either completes |

*Most behaviors have automated verification via integration tests.*

---

## Validation Sign-Off

- [x] All tasks have automated verify or documented rationale for import-only
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 not needed (import verification for W1-W2, full tests in W3)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
