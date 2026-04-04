---
phase: 09
slug: auto-activities-workflow-agent-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing) |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `python -m pytest tests/ -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short --cov=src` |
| **Estimated runtime** | ~80 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -q --tb=short --cov=src`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 80 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | AUTO-01 | unit | `python -m pytest tests/ -q` | ✅ existing | ⬜ pending |
| 09-01-02 | 01 | 1 | AUTO-02 | unit | `python -m pytest tests/ -q` | ✅ existing | ⬜ pending |
| 09-02-01 | 02 | 2 | AUTO-03 | integration | `python -m pytest tests/ -q` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 2 | AUTO-04 | integration | `python -m pytest tests/ -q` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 3 | AUTO-05 | integration | `python -m pytest tests/ -q` | ❌ W0 | ⬜ pending |
| 09-03-02 | 03 | 3 | INTG-01,02,03 | integration | `python -m pytest tests/ -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing test infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Celery beat actually polls | AUTO-02 | Requires running Docker Compose with Celery beat | 1. Start docker compose 2. Create workflow with auto activity 3. Verify Celery worker log shows execution |
| Email sending in dev mode | AUTO-03 | Requires SMTP or log verification | 1. Trigger send_email auto method 2. Check application logs for email output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 80s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
