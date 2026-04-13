---
phase: 28
slug: cabinet-folder-hierarchy
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24.x |
| **Config file** | `tests/conftest.py` (session-scoped fixtures, in-memory SQLite) |
| **Quick run command** | `python -m pytest tests/test_folders.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_folders.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 28-01-01 | 01 | 0 | FOLD-01 | unit | `python -m pytest tests/test_folders.py -x` | ❌ W0 | ⬜ pending |
| 28-01-02 | 01 | 1 | FOLD-01,02,03,04 | unit | `python -m pytest tests/test_folders.py -x` | ✅ W0 | ⬜ pending |
| 28-02-01 | 02 | 2 | FOLD-01,02,03,04 | unit | `python -m pytest tests/test_folders.py -x` | ✅ W0 | ⬜ pending |
| 28-02-02 | 02 | 2 | FOLD-03 | unit | `python -m pytest tests/test_folders.py::test_document_response_includes_folder_ids -x` | ✅ W0 | ⬜ pending |
| 28-03-01 | 03 | 3 | FOLD-02 | manual | Browser: expand/collapse FolderTree | — | ⬜ pending |
| 28-03-02 | 03 | 3 | FOLD-03 | manual | Browser: file/unfile document from detail panel | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_folders.py` — stubs for FOLD-01 through FOLD-04 (18 test stubs, created in Plan 01 Task 1)

*Existing infrastructure (`tests/conftest.py`, async test setup) covers all phase requirements — no new test infrastructure needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FolderTree expand/collapse | FOLD-02 | UI interaction state | Navigate to /admin/folders, expand/collapse nodes |
| File document into folder | FOLD-03 | UI interaction in detail panel | Open document, click "Add to Folder", select folder |
| Breadcrumb navigation display | FOLD-04 | UI rendering | Create nested folder hierarchy, verify path shows |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
