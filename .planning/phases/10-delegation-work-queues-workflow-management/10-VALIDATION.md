---
phase: 10
slug: delegation-work-queues-workflow-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24.x |
| **Config file** | `tests/conftest.py` (session-scoped fixtures, SQLite in-memory) |
| **Quick run command** | `cd src && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd src && python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd src && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd src && python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | USER-05 | integration | `cd src && python -m pytest tests/test_delegation.py::test_set_availability -x` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | INBOX-08 | integration | `cd src && python -m pytest tests/test_delegation.py::test_delegation_routing -x` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | QUEUE-01 | integration | `cd src && python -m pytest tests/test_queues.py::test_queue_crud -x` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 1 | QUEUE-02 | integration | `cd src && python -m pytest tests/test_queues.py::test_queue_performer -x` | ❌ W0 | ⬜ pending |
| 10-02-03 | 02 | 1 | QUEUE-03 | integration | `cd src && python -m pytest tests/test_queues.py::test_queue_claim -x` | ❌ W0 | ⬜ pending |
| 10-02-04 | 02 | 1 | QUEUE-04 | integration | `cd src && python -m pytest tests/test_queues.py::test_queue_lock -x` | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 2 | MGMT-01 | integration | `cd src && python -m pytest tests/test_workflow_mgmt.py::test_halt -x` | ❌ W0 | ⬜ pending |
| 10-03-02 | 03 | 2 | MGMT-02 | integration | `cd src && python -m pytest tests/test_workflow_mgmt.py::test_resume -x` | ❌ W0 | ⬜ pending |
| 10-03-03 | 03 | 2 | MGMT-03 | integration | `cd src && python -m pytest tests/test_workflow_mgmt.py::test_abort -x` | ❌ W0 | ⬜ pending |
| 10-03-04 | 03 | 2 | MGMT-04 | integration | `cd src && python -m pytest tests/test_workflow_mgmt.py::test_list_filtered -x` | ❌ W0 | ⬜ pending |
| 10-03-05 | 03 | 2 | MGMT-05 | integration | `cd src && python -m pytest tests/test_workflow_mgmt.py::test_restart -x` | ❌ W0 | ⬜ pending |
| 10-04-01 | 04 | 2 | AUDIT-05 | integration | `cd src && python -m pytest tests/test_audit_query.py::test_audit_query -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_delegation.py` — stubs for USER-05, INBOX-08
- [ ] `tests/test_queues.py` — stubs for QUEUE-01 through QUEUE-04
- [ ] `tests/test_workflow_mgmt.py` — stubs for MGMT-01 through MGMT-05
- [ ] `tests/test_audit_query.py` — stubs for AUDIT-05

*Existing `tests/conftest.py` covers shared fixtures.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
