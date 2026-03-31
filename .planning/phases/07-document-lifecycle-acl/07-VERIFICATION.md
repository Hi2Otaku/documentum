---
phase: 07-document-lifecycle-acl
verified: 2026-03-31T09:00:00Z
status: passed
score: 18/18 must-haves verified
re_verification: false
human_verification:
  - test: "Add-action branch of apply_lifecycle_acl_rules"
    expected: "When a LifecycleACLRule has action='add', it should create ACL entries for the matching principals. Currently only an audit record is written."
    why_human: "No requirement explicitly mandates the 'add' branch behavior, and no test exercises it. A human should decide whether this is acceptable scope or a gap to fill in a later plan."
---

# Phase 7: Document Lifecycle & ACL Verification Report

**Phase Goal:** Documents transition through defined lifecycle states with workflow-triggered transitions, and object-level permissions automatically change at workflow steps
**Verified:** 2026-03-31
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | LifecycleState enum has DRAFT, REVIEW, APPROVED, ARCHIVED values | VERIFIED | `src/app/models/enums.py` lines 67-71, all four values present with lowercase string values |
| 2 | PermissionLevel enum has READ, WRITE, DELETE, ADMIN values | VERIFIED | `src/app/models/enums.py` lines 74-79, hierarchy enforced via PERMISSION_HIERARCHY dict |
| 3 | Document model has lifecycle_state field defaulting to DRAFT | VERIFIED | `src/app/models/document.py` line 45, nullable column; service defaults to DRAFT when NULL |
| 4 | ActivityTemplate model has lifecycle_action nullable field | VERIFIED | `src/app/models/workflow.py` line 87 |
| 5 | DocumentACL model stores per-document per-principal permissions | VERIFIED | `src/app/models/acl.py` lines 10-28, FK to documents.id, unique constraint on 4-tuple |
| 6 | LifecycleACLRule model stores transition-to-ACL-change mappings | VERIFIED | `src/app/models/acl.py` lines 31-44, from_state/to_state/action/permission_level/principal_filter |
| 7 | Lifecycle transitions enforced via LIFECYCLE_TRANSITIONS set | VERIFIED | `src/app/services/lifecycle_service.py` lines 24-29, 4 valid transitions defined |
| 8 | ACL service can create, check, and remove permissions | VERIFIED | `acl_service.py`: create_acl_entry, remove_acl_entry, check_permission all implemented |
| 9 | ADMIN permission implies all lower permissions | VERIFIED | PERMISSION_HIERARCHY dict + has_sufficient_permission; hierarchy test passes (test_acl_permission_hierarchy) |
| 10 | Completing a workflow activity with lifecycle_action triggers document lifecycle transition | VERIFIED | engine_service.py lines 363-385, lazy import hook with try/except; test_workflow_triggered_transition passes |
| 11 | Manual API endpoint allows lifecycle transition on a single document | VERIFIED | `src/app/routers/lifecycle.py` POST /{document_id}/lifecycle/transition; registered in main.py |
| 12 | Permission checks enforced on all document routes via require_permission dependency | VERIFIED | documents.py: 6 routes use require_permission (READ on get/list_versions/download, WRITE on update/checkout/checkin) |
| 13 | Upload endpoint creates ADMIN ACL entry for document creator | VERIFIED | document_service.py line 88, create_owner_acl called after flush |
| 14 | No ACL entries on a document means open access (backward compat) | VERIFIED | acl_service.py lines 155-156, count=0 returns True; test_no_acl_entries_means_open_access passes |
| 15 | All lifecycle transitions and ACL changes produce audit records | VERIFIED | Both services call create_audit_record on every mutation; LIFE-03 and ACL-03 tests confirm records exist |
| 16 | Documents transition through DRAFT -> REVIEW -> APPROVED -> ARCHIVED with invalid transitions rejected | VERIFIED | 7 LIFE-01 tests cover all valid chains and 3 invalid transitions (all return 400) |
| 17 | ACL permissions automatically change when lifecycle state changes via rules | VERIFIED | test_acl_changes_on_approval and test_workflow_acl_modification pass; remove action fully implemented |
| 18 | Permission checks block unauthorized document API access with 403 | VERIFIED | 4 ACL-04 tests confirm 403 responses; test_group_based_permission confirms group resolution |

**Score:** 18/18 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/app/models/enums.py` | LifecycleState and PermissionLevel enums | VERIFIED | Both enums present with correct lowercase values |
| `src/app/models/acl.py` | DocumentACL and LifecycleACLRule models | VERIFIED | Both models with FK, constraints, and relationship |
| `src/app/services/lifecycle_service.py` | Lifecycle transition logic with ACL rule application | VERIFIED | LIFECYCLE_TRANSITIONS, transition_lifecycle_state, apply_lifecycle_acl_rules, execute_lifecycle_action |
| `src/app/services/acl_service.py` | ACL CRUD and permission checking | VERIFIED | check_permission, create_acl_entry, remove_acl_entry, create_owner_acl, get_document_acls |
| `alembic/versions/phase7_001_lifecycle_acl.py` | Database migration for new tables and columns | VERIFIED | 2 op.create_table calls (document_acl, lifecycle_acl_rules) |
| `src/app/services/engine_service.py` | Lifecycle action hook in advancement loop | VERIFIED | lifecycle_action check + execute_lifecycle_action call in _advance_from_activity |
| `src/app/core/dependencies.py` | require_permission dependency factory | VERIFIED | def require_permission(level) with acl_service lazy import and 403 raise |
| `src/app/routers/lifecycle.py` | Manual lifecycle transition endpoint | VERIFIED | 5 endpoints: POST transition, GET state, GET/POST/DELETE acl |
| `src/app/routers/documents.py` | ACL-protected document routes | VERIFIED | 6 routes updated with require_permission (READ and WRITE as appropriate) |
| `tests/test_lifecycle.py` | Integration tests for LIFE-01 through LIFE-04 | VERIFIED | 13 tests, 562 lines |
| `tests/test_acl.py` | Integration tests for ACL-01 through ACL-04 | VERIFIED | 15 tests, 667 lines |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `lifecycle_service.py` | `acl_service.py` | apply_lifecycle_acl_rules directly calls DocumentACL queries | WIRED | Lines 107-148 directly query and delete DocumentACL entries |
| `acl.py` | `document.py` | DocumentACL.document_id FK to documents.id | WIRED | Line 20: `ForeignKey("documents.id")` |
| `engine_service.py` | `lifecycle_service.py` | lazy import in _advance_from_activity | WIRED | Lines 375-377: `from app.services import lifecycle_service; await lifecycle_service.execute_lifecycle_action(...)` |
| `dependencies.py` | `acl_service.py` | check_permission call in require_permission | WIRED | Line 70: `acl_service.check_permission(db, document_id, current_user.id, level)` |
| `documents.py` | `dependencies.py` | Depends(require_permission(PermissionLevel.X)) on 6 routes | WIRED | get_document, update_document, checkout, checkin, list_versions, download_version all use require_permission |
| `tests/test_lifecycle.py` | `routers/lifecycle.py` | HTTP calls to lifecycle transition endpoint | WIRED | Pattern `/documents/.*/lifecycle/transition` present in multiple tests |
| `tests/test_acl.py` | `routers/documents.py` | HTTP calls testing 403 responses | WIRED | 4 tests explicitly assert status_code == 403 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `lifecycle_service.py:transition_lifecycle_state` | `document.lifecycle_state` | `db.execute(select(Document)...)` DB query | Yes — real document fetched and mutated | FLOWING |
| `acl_service.py:check_permission` | `total_entries`, `user_entries`, `group_entries` | DB queries via select(DocumentACL) and user_groups | Yes — real ACL rows queried | FLOWING |
| `lifecycle_service.py:apply_lifecycle_acl_rules` | `rules`, `acl_entries` | DB queries via select(LifecycleACLRule) and select(DocumentACL) | Yes — real rule and ACL data | FLOWING |
| `routers/lifecycle.py:transition_document_lifecycle` | `document` | calls lifecycle_service.transition_lifecycle_state | Yes — returns updated Document ORM object | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All lifecycle and ACL tests pass | `pytest tests/test_lifecycle.py tests/test_acl.py -x -q` | 28 passed in 5.67s | PASS |
| Full test suite regression-free | `pytest tests/ -x -q` | 211 passed in 44.20s | PASS |
| Service imports resolve | `python -c "from app.services.lifecycle_service import LIFECYCLE_TRANSITIONS; from app.services.acl_service import check_permission; print('OK')"` | OK | PASS |
| Model imports resolve | `python -c "from app.models import DocumentACL, LifecycleACLRule, LifecycleState, PermissionLevel; print('OK')"` | OK | PASS |
| Document.lifecycle_state column exists | Python column introspection | True | PASS |
| ActivityTemplate.lifecycle_action column exists | Python column introspection | True | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LIFE-01 | 07-01, 07-03 | Documents transition through defined states: Draft -> Review -> Approved -> Archived | SATISFIED | 7 tests in test_lifecycle.py; LIFECYCLE_TRANSITIONS set enforces valid paths; invalid transitions return 400 |
| LIFE-02 | 07-02, 07-03 | Lifecycle transitions triggered automatically by workflow activity completion | SATISFIED | Engine hook in engine_service.py _advance_from_activity; test_workflow_triggered_transition + multi-doc test pass |
| LIFE-03 | 07-01, 07-03 | Lifecycle state changes recorded in audit trail | SATISFIED | create_audit_record called for both successful and failed transitions; test_lifecycle_transition_creates_audit_record and test_failed_transition_creates_audit_record pass |
| LIFE-04 | 07-01, 07-03 | ACL permissions automatically change when lifecycle state changes | SATISFIED | apply_lifecycle_acl_rules queries LifecycleACLRule table and applies remove actions; test_acl_changes_on_approval passes |
| ACL-01 | 07-01, 07-03 | Objects have Access Control Lists defining who can read/write/delete | SATISFIED | DocumentACL model + 5 tests for CRUD, permission hierarchy, no-ACL fallback |
| ACL-02 | 07-02, 07-03 | Workflow activities can automatically modify document ACLs | SATISFIED | Engine -> lifecycle_service -> apply_lifecycle_acl_rules chain; test_workflow_acl_modification passes |
| ACL-03 | 07-01, 07-03 | ACL changes recorded in audit trail | SATISFIED | acl_service.create_acl_entry and remove_acl_entry call create_audit_record; test_acl_grant_creates_audit_record and test_acl_removal_creates_audit_record pass |
| ACL-04 | 07-02, 07-03 | Permission checks enforced on all API operations | SATISFIED | require_permission dependency on 6 document routes; 7 ACL-04 tests confirm enforcement, group-based access, open upload/list |

All 8 requirement IDs from plan frontmatter accounted for. REQUIREMENTS.md marks all 8 as Complete for Phase 7. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/app/services/lifecycle_service.py` | 138-148 | `add` action branch only writes audit record, does not create ACL entries | Warning | No current requirement or test exercises the `add` action branch. `remove` action (the tested path) works correctly. The SUMMARY acknowledged this as intentional, pending context on principal resolution. If a future phase seeds `add`-type lifecycle rules, they will silently no-op on ACL creation while still producing an audit record. |

No blocker anti-patterns found. The `add` branch incompleteness is a warning only.

### Human Verification Required

#### 1. ACL Rule "add" Action Branch

**Test:** Create a LifecycleACLRule with `action="add"`, `principal_filter="creator"`, trigger the transition, and observe whether any ACL entry is created.
**Expected:** An ACL entry should be created for the document creator (or appropriate principal).
**Why human:** No passing test covers this path. The code reaches the `elif rule.action == "add":` branch and writes an audit record, but the principal resolution logic (determining which user to grant access to) is not implemented. A human should decide whether this is acceptable scope debt or needs a follow-up plan.

### Gaps Summary

No gaps blocking goal achievement. All 8 requirements are satisfied with passing integration tests. The one warning item (the `add` action branch in `apply_lifecycle_acl_rules`) does not block any current requirement and is not exercised by any test or test scenario.

The phase goal is fully achieved: documents transition through defined lifecycle states (DRAFT -> REVIEW -> APPROVED -> ARCHIVED), workflow activity completion triggers these transitions on all package documents, invalid transitions are rejected, and object-level permissions (DocumentACL) automatically change at workflow steps via the LifecycleACLRule table. All transitions and ACL mutations are audited.

---

_Verified: 2026-03-31_
_Verifier: Claude (gsd-verifier)_
