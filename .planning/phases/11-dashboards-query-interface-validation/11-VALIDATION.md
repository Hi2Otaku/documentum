---
phase: 11
slug: dashboards-query-interface-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend), vitest 3.x (frontend) |
| **Config file** | `pytest.ini` / `frontend/vitest.config.ts` |
| **Quick run command** | `pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `pytest tests/ -v --timeout=60 && cd frontend && npx vitest run` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | BAM-01 | integration | `pytest tests/test_dashboard.py -k "test_workflow_counts"` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | BAM-02 | integration | `pytest tests/test_dashboard.py -k "test_avg_completion"` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | BAM-03 | integration | `pytest tests/test_dashboard.py -k "test_bottleneck"` | ❌ W0 | ⬜ pending |
| 11-01-04 | 01 | 1 | BAM-04 | integration | `pytest tests/test_dashboard.py -k "test_workload"` | ❌ W0 | ⬜ pending |
| 11-01-05 | 01 | 1 | BAM-05 | integration | `pytest tests/test_dashboard.py -k "test_sla"` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | QUERY-01 | integration | `pytest tests/test_query.py -k "test_query_workflows"` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | QUERY-02 | integration | `pytest tests/test_query.py -k "test_query_work_items"` | ❌ W0 | ⬜ pending |
| 11-02-03 | 02 | 1 | QUERY-03 | integration | `pytest tests/test_query.py -k "test_query_documents"` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 2 | EXAMPLE-01 | e2e | `pytest tests/test_contract_approval.py -k "test_seed_template"` | ❌ W0 | ⬜ pending |
| 11-03-02 | 03 | 2 | EXAMPLE-02 | e2e | `pytest tests/test_contract_approval.py -k "test_e2e_execution"` | ❌ W0 | ⬜ pending |
| 11-03-03 | 03 | 2 | EXAMPLE-03 | e2e | `pytest tests/test_contract_approval.py -k "test_audit_trail"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dashboard.py` — stubs for BAM-01 through BAM-05
- [ ] `tests/test_query.py` — stubs for QUERY-01 through QUERY-03
- [ ] `tests/test_contract_approval.py` — stubs for EXAMPLE-01 through EXAMPLE-03

*Existing infrastructure covers test framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE live updates in browser | BAM-01 | Real-time stream requires browser/EventSource client | Open dashboard, start a workflow, verify counts update without page refresh |
| Dashboard chart rendering | BAM-03 | Visual chart correctness | Open dashboard, verify bottleneck bar chart renders with correct data |
| Query result click-through | QUERY-01 | Navigation behavior | Search workflows, click row, verify detail view loads |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
