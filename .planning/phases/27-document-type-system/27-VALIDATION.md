---
phase: 27
slug: document-type-system
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `pytest tests/test_document_types.py -x` |
| **Full suite command** | `pytest tests/ -x --timeout=60` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_document_types.py -x`
- **After every plan wave:** Run `pytest tests/ -x --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 0 | TYPE-01–04 | unit/integration | `pytest tests/test_document_types.py -x` | ❌ W0 | ⬜ pending |
| 27-01-02 | 01 | 1 | TYPE-01 | integration | `pytest tests/test_document_types.py::test_create_type -x` | ❌ W0 | ⬜ pending |
| 27-01-03 | 01 | 1 | TYPE-01 | integration | `pytest tests/test_document_types.py::test_create_type_non_admin -x` | ❌ W0 | ⬜ pending |
| 27-01-04 | 01 | 1 | TYPE-04 | integration | `pytest tests/test_document_types.py::test_child_type_inherits_parent -x` | ❌ W0 | ⬜ pending |
| 27-02-01 | 02 | 2 | TYPE-02 | integration | `pytest tests/test_document_types.py::test_upload_with_type -x` | ❌ W0 | ⬜ pending |
| 27-02-02 | 02 | 2 | TYPE-02 | integration | `pytest tests/test_document_types.py::test_update_document_type -x` | ❌ W0 | ⬜ pending |
| 27-02-03 | 02 | 2 | TYPE-03 | integration | `pytest tests/test_document_types.py::test_validation_rejects_missing_required -x` | ❌ W0 | ⬜ pending |
| 27-02-04 | 02 | 2 | TYPE-03 | integration | `pytest tests/test_document_types.py::test_validation_passes_valid_metadata -x` | ❌ W0 | ⬜ pending |
| 27-02-05 | 02 | 2 | TYPE-03 | integration | `pytest tests/test_document_types.py::test_untyped_skips_validation -x` | ❌ W0 | ⬜ pending |
| 27-03-01 | 03 | 3 | TYPE-05 | manual | Manual: open upload form, select type, verify fields render | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_document_types.py` — stubs for TYPE-01 through TYPE-04 (all backend requirements)
- [ ] No new conftest fixtures needed — existing `admin_user`, `admin_token`, `regular_user`, `regular_token`, `async_client` fixtures are sufficient

*Note: TYPE-05 (frontend type-specific fields rendering) is manual-only — no automated test path.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Type-specific metadata fields render dynamically in document form | TYPE-05 | Frontend rendering requires browser; no Playwright tests in scope | 1. Navigate to document upload form. 2. Select a document type with required fields. 3. Verify form section appears below standard fields. 4. Verify fields match the type schema (correct types: text, number, checkbox, date, select). 5. Submit and verify metadata saved correctly. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
