---
phase: 06
slug: advanced-routing-alias-sets
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_routing.py tests/test_alias.py -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_routing.py tests/test_alias.py -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | ALIAS-01,02,03 | integration | `pytest tests/test_alias.py` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | EXEC-08,09,10,11 | integration | `pytest tests/test_routing.py` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | PERF-04,05 | integration | `pytest tests/test_routing.py` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 3 | All phase reqs | integration | `pytest tests/ -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_routing.py` — stubs for EXEC-08, EXEC-09, EXEC-10, EXEC-11
- [ ] `tests/test_alias.py` — stubs for ALIAS-01, ALIAS-02, ALIAS-03

*Existing infrastructure (conftest.py, test fixtures) covers shared needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Concurrent alias resolution | ALIAS-02 | Race condition under real load | Start 10 workflows simultaneously with same alias set |

*Most behaviors have automated verification via integration tests.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
