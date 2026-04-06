---
phase: 15
slug: workflow-operations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (not yet configured for frontend) |
| **Config file** | None — no frontend test infrastructure exists |
| **Quick run command** | N/A (no frontend tests) |
| **Full suite command** | Backend: `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds (backend only) |

---

## Sampling Rate

- **After every task commit:** Visual verification in browser (dev server)
- **After every plan wave:** Full visual walkthrough of all 4 requirements
- **Before `/gsd:verify-work`:** All 4 success criteria verified manually in running app
- **Max feedback latency:** Manual (browser reload)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | WF-01 | manual | Manual browser test | N/A | ⬜ pending |
| 15-02-01 | 02 | 1 | WF-02 | manual | Manual browser test | N/A | ⬜ pending |
| 15-02-02 | 02 | 1 | WF-03 | manual | Manual browser test | N/A | ⬜ pending |
| 15-03-01 | 03 | 2 | WF-04 | manual | Manual browser test | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- No frontend test infrastructure (Vitest not installed/configured)
- All validation is manual for this phase (consistent with prior frontend phases 12-14)

*Existing infrastructure covers backend. Frontend validation is manual.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Start workflow wizard submits correct payload | WF-01 | Frontend-only, no Vitest setup | Open app, click Start Workflow, complete wizard, verify instance created |
| Instance list renders with filters | WF-02 | Frontend-only, no Vitest setup | Open Workflows page, verify table columns, apply filters |
| Admin actions call correct endpoints | WF-03 | Frontend-only, requires auth state | Login as admin, halt/resume/terminate instance, verify state changes |
| Progress graph shows activity states | WF-04 | React Flow rendering, no Vitest setup | Open instance detail, verify node colors match activity states |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < manual
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
