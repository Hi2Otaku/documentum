---
phase: 29
slug: folder-acl-inheritance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `docker compose exec api pytest tests/test_acl.py tests/test_folder_acl.py -x -q` |
| **Full suite command** | `docker compose exec api pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec api pytest tests/test_folder_acl.py -x -q`
- **After every plan wave:** Run `docker compose exec api pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 29-01-01 | 01 | 1 | FOLD-05 | unit | `pytest tests/test_folder_acl.py::test_folder_acl_model -x -q` | ❌ W0 | ⬜ pending |
| 29-01-02 | 01 | 1 | FOLD-05 | unit | `pytest tests/test_folder_acl.py::test_check_permission_folder_inheritance -x -q` | ❌ W0 | ⬜ pending |
| 29-01-03 | 01 | 1 | FOLD-05 | unit | `pytest tests/test_folder_acl.py::test_document_acl_overrides_folder -x -q` | ❌ W0 | ⬜ pending |
| 29-02-01 | 02 | 1 | FOLD-05 | integration | `pytest tests/test_folder_acl.py::test_folder_acl_api_crud -x -q` | ❌ W0 | ⬜ pending |
| 29-02-02 | 02 | 1 | FOLD-05 | integration | `pytest tests/test_folder_acl.py::test_get_folder_documents_acl_filtered -x -q` | ❌ W0 | ⬜ pending |
| 29-03-01 | 03 | 2 | FOLD-05 | manual | see Manual-Only Verifications | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_folder_acl.py` — test stubs for FOLD-05 (model, check_permission extension, API CRUD, document listing filter)
- [ ] `tests/conftest.py` — extend with `folder_with_acl` and `folder_without_acl` fixtures

*Existing test infrastructure (pytest + pytest-asyncio + httpx AsyncClient) covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Inherited access badge shown on document detail | FOLD-05 | Frontend rendering | File doc in folder with ACL, open doc detail as authorized user, verify "Inherited from [folder]" badge appears |
| Permissions tab renders in folder admin panel | FOLD-05 | Frontend rendering | Open FoldersPage, select a folder, click Permissions tab, verify ACL list + Add button shown |
| Silent omission of inaccessible docs in folder browse | FOLD-05 | Frontend rendering | Browse folder as user without ACL, verify documents are not shown (no error, no count) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
