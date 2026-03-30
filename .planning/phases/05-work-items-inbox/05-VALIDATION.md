---
phase: 05
slug: work-items-inbox
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-30
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio 0.24.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_inbox.py -q --tb=short` |
| **Full suite command** | `python -m pytest -q --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_inbox.py -q --tb=short`
- **After every plan wave:** Run `python -m pytest -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 05-01-01 | 01 | 1 | INBOX-06, PERF-01/02/03 | import | `python -c "from app.models.workflow import WorkItemComment"` | pending |
| 05-01-02 | 01 | 1 | INBOX-01/02/03 | import | `python -c "from app.schemas.inbox import InboxItemResponse"` | pending |
| 05-02-01 | 02 | 2 | INBOX-01/04/05, PERF-01/02/03 | import | `python -c "from app.services.inbox_service import get_inbox"` | pending |
| 05-02-02 | 02 | 2 | INBOX-02/03/06/07 | import | `python -c "from app.routers.inbox import router"` | pending |
| 05-03-01 | 03 | 3 | ALL INBOX/PERF | integration | `pytest tests/test_inbox.py -q` | pending |

*Status: pending / green / red / flaky*

*Note: Waves 1-2 use import-only verification since they produce models, schemas, and services. Wave 3 creates the full test suite.*

---

## Wave 0 Requirements

No Wave 0 plan required. Waves 1-2 produce foundational code verified by import checks. Wave 3 creates the comprehensive test suite.

*Existing test infrastructure from Phase 1-4 covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Inbox shows priority/due date indicators | INBOX-07 | Visual verification | Start workflow, check inbox response includes priority and due_date fields |

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
