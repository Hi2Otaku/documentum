---
phase: 04
slug: process-engine-core
status: draft
nyquist_compliant: false
wave_0_complete: false
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | EXEC-04 | unit | `pytest tests/test_workflows.py -k state_machine` | ❌ W0 | pending |
| 04-01-02 | 01 | 1 | EXEC-13, EXEC-14 | unit | `pytest tests/test_workflows.py -k expression` | ❌ W0 | pending |
| 04-02-01 | 02 | 2 | EXEC-01, EXEC-02, EXEC-03 | integration | `pytest tests/test_workflows.py -k start_workflow` | ❌ W0 | pending |
| 04-02-02 | 02 | 2 | EXEC-05, EXEC-06, EXEC-07, EXEC-12 | integration | `pytest tests/test_workflows.py -k routing` | ❌ W0 | pending |
| 04-03-01 | 03 | 3 | ALL EXEC | integration | `pytest tests/test_workflows.py -q` | ❌ W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_workflows.py` — stubs for EXEC-01 through EXEC-14
- [ ] `tests/conftest.py` — workflow fixtures (installed template, test users)

*Existing test infrastructure from Phase 1/2/3 covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Parallel activities run simultaneously | EXEC-07 | Timing-dependent | Start workflow with AND-split, verify both branches active before either completes |

*Most behaviors have automated verification via integration tests.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
