---
phase: 08
slug: visual-workflow-designer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 3.x (frontend), pytest 8.x (backend — existing) |
| **Config file** | `frontend/vitest.config.ts` (Wave 0 installs) |
| **Quick run command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd frontend && npx vitest run --coverage` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd frontend && npx vitest run --coverage`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | DESIGN-01 | integration | `npx vitest run` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | DESIGN-07 | integration | `npx vitest run` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | DESIGN-02 | unit | `npx vitest run` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | DESIGN-03 | unit | `npx vitest run` | ❌ W0 | ⬜ pending |
| 08-02-03 | 02 | 2 | DESIGN-04 | unit | `npx vitest run` | ❌ W0 | ⬜ pending |
| 08-02-04 | 02 | 2 | DESIGN-05 | unit | `npx vitest run` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 3 | DESIGN-06 | integration | `npx vitest run` | ❌ W0 | ⬜ pending |
| 08-03-02 | 03 | 3 | DESIGN-07 | e2e | manual | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/vitest.config.ts` — Vitest configuration with jsdom environment
- [ ] `frontend/src/test/setup.ts` — Test setup file (React Testing Library)
- [ ] `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` — Test dependencies
- [ ] `frontend/src/test/mocks/handlers.ts` — MSW handlers for API mocking

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drag-and-drop from palette | DESIGN-02 | HTML5 DnD API hard to simulate in jsdom | 1. Open designer 2. Drag "Manual" from palette 3. Drop on canvas 4. Verify node appears |
| Draw flow connection | DESIGN-03 | React Flow handle interactions require browser | 1. Add two nodes 2. Drag from source handle to target 3. Verify edge appears |
| Visual validation errors on canvas | DESIGN-06 | CSS visual indicators need visual verification | 1. Create invalid template 2. Click validate 3. Verify red borders on invalid nodes |
| Save/load round-trip | DESIGN-07 | Full backend integration needed | 1. Create template with nodes/edges 2. Save 3. Reload page 4. Verify layout preserved |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
