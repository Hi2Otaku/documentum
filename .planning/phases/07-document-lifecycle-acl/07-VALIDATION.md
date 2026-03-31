---
phase: 07
slug: document-lifecycle-acl
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_lifecycle.py tests/test_acl.py -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~35 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_lifecycle.py tests/test_acl.py -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 35 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | LIFE-01, ACL-01 | integration | `pytest tests/test_lifecycle.py tests/test_acl.py` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 2 | LIFE-02, LIFE-03, LIFE-04, ACL-02, ACL-03, ACL-04 | integration | `pytest tests/test_lifecycle.py tests/test_acl.py` | ❌ W0 | ⬜ pending |
| 07-03-01 | 03 | 3 | All phase reqs | integration | `pytest tests/ -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_lifecycle.py` — stubs for LIFE-01, LIFE-02, LIFE-03, LIFE-04
- [ ] `tests/test_acl.py` — stubs for ACL-01, ACL-02, ACL-03, ACL-04

*Existing infrastructure (conftest.py, test fixtures) covers shared needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | - | - | - |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 35s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
