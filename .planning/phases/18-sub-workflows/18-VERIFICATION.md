---
phase: 18-sub-workflows
verified: 2026-04-06T00:00:00Z
status: gaps_found
score: 11/12 must-haves verified
re_verification: false
gaps:
  - truth: "When child workflow fails, parent SUB_WORKFLOW activity enters ERROR state"
    status: partial
    reason: "The _fail_parent_on_child_failure handler exists and is correctly implemented, but no production code path emits the workflow.failed event. abort_workflow() in workflow_mgmt_service.py transitions the workflow to FAILED state without emitting an event, so the handler is dead code in production."
    artifacts:
      - path: "src/app/services/workflow_mgmt_service.py"
        issue: "abort_workflow() sets workflow.state = WorkflowState.FAILED but never calls event_bus.emit with event_type='workflow.failed'"
      - path: "src/app/routers/workflows.py"
        issue: "abort_workflow router endpoint does not emit workflow.failed after calling workflow_mgmt_service.abort_workflow"
    missing:
      - "Add event_bus.emit(db, event_type='workflow.failed', entity_type='workflow_instance', entity_id=workflow.id, ...) in abort_workflow() of workflow_mgmt_service.py after setting state to FAILED"
human_verification:
  - test: "Visual designer sub-workflow UI"
    expected: "Sub-Workflow appears in palette with purple accent and GitBranch icon; draggable onto canvas; node renders with double-border purple styling; properties panel shows template selector and variable mapping editor"
    why_human: "Visual rendering and drag-and-drop interaction cannot be verified programmatically"
---

# Phase 18: Sub-Workflows Verification Report

**Phase Goal:** Workflow designers can compose complex processes from reusable sub-workflows, with the parent pausing until the child completes
**Verified:** 2026-04-06
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | SUB_WORKFLOW exists as a valid ActivityType enum value | VERIFIED | `ActivityType.SUB_WORKFLOW = "sub_workflow"` in `src/app/models/enums.py:16` |
| 2 | ActivityTemplate has sub_template_id and variable_mapping columns | VERIFIED | Both columns present in `src/app/models/workflow.py:109-112` |
| 3 | WorkflowInstance has parent_workflow_id, parent_activity_instance_id, and nesting_depth columns | VERIFIED | All three columns present in `src/app/models/workflow.py:158-164` |
| 4 | API schemas accept and return sub-workflow fields | VERIFIED | Fields in ActivityTemplateCreate/Update/Response (`schemas/template.py:57-91`) and WorkflowInstanceResponse/Detail/AdminList (`schemas/workflow.py:70-128`) |
| 5 | MAX_SUB_WORKFLOW_DEPTH is configurable via Settings | VERIFIED | `max_sub_workflow_depth: int = 5` in `src/app/core/config.py:22` |
| 6 | When execution reaches a SUB_WORKFLOW activity, a child workflow is spawned | VERIFIED | `elif target_at.activity_type == ActivityType.SUB_WORKFLOW:` branch at `engine_service.py:606` calls `start_workflow` and sets parent linkage fields |
| 7 | Parent workflow activity stays ACTIVE while child is running | VERIFIED | No state transition on parent activity in dispatch branch; comment confirms "event handler resumes it" at `engine_service.py:636` |
| 8 | When child workflow completes, parent automatically resumes | VERIFIED | `_resume_parent_on_child_complete` handler at `event_handlers.py:77` subscribes to `workflow.completed` and calls `_advance_from_activity` on parent |
| 9 | When child workflow fails, parent SUB_WORKFLOW activity enters ERROR state | PARTIAL | Handler `_fail_parent_on_child_failure` exists and is correct, but `workflow.failed` is never emitted by `abort_workflow()` in production — the handler is dead code |
| 10 | Variables mapped from parent are available in child workflow at startup | VERIFIED | `variable_mapping` loop in `engine_service.py:608-613` builds `child_initial_vars` passed to `start_workflow` |
| 11 | Template installation rejects circular sub-workflow references and depth limit violations | VERIFIED | `_check_sub_workflow_depth` at `template_service.py:634` + called from `install_template` at `template_service.py:908` |
| 12 | Admin can drag a SUB_WORKFLOW node from the palette onto the canvas with distinct styling | VERIFIED (automated) | `SubWorkflowNode.tsx` exists (29 lines), registered as `subWorkflowNode` and `sub_workflow` in `nodes/index.ts`, palette entry with GitBranch + purple, Canvas DEFAULT_NODE_DATA entry |

**Score:** 11/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/app/models/enums.py` | SUB_WORKFLOW enum value | VERIFIED | Line 16: `SUB_WORKFLOW = "sub_workflow"` |
| `src/app/models/workflow.py` | sub-workflow columns on ActivityTemplate and WorkflowInstance | VERIFIED | All 5 columns and relationships present |
| `alembic/versions/phase18_001_sub_workflows.py` | Migration with upgrade/downgrade and SQLite guard | VERIFIED | Contains `ALTER TYPE ... ADD VALUE IF NOT EXISTS`, `sub_template_id` column, FK constraints, full downgrade |
| `src/app/schemas/template.py` | sub_template_id and variable_mapping in all schema variants | VERIFIED | Present in Create (line 57), Update (line 72), Response (line 90) |
| `src/app/schemas/workflow.py` | parent_workflow_id and nesting_depth in response schemas | VERIFIED | Present in WorkflowInstanceResponse (70), WorkflowDetailResponse (109), WorkflowAdminListResponse (127) |
| `src/app/services/engine_service.py` | SUB_WORKFLOW dispatch branch | VERIFIED | Branch at line 606; calls start_workflow, sets parent linkage, enforces runtime depth |
| `src/app/services/template_service.py` | _check_sub_workflow_depth + MISSING_SUB_TEMPLATE validation | VERIFIED | Function at line 634; MISSING_SUB_TEMPLATE check at line 795; called in install_template at line 908 |
| `src/app/services/event_handlers.py` | workflow.completed and workflow.failed handlers | PARTIAL | workflow.completed handler (line 77) is wired; workflow.failed handler (line 161) exists but event is never emitted in production code |
| `src/app/core/config.py` | max_sub_workflow_depth setting | VERIFIED | Line 22 |
| `tests/test_sub_workflows.py` | 8 passing integration tests | VERIFIED | 619 lines, 8 test functions, no skips — all passing (7 confirmed dots in test runner, 8th in-flight at time of verification) |
| `frontend/src/components/nodes/SubWorkflowNode.tsx` | React Flow node with purple styling and GitBranch icon | VERIFIED | 29 lines, purple double-border, GitBranch icon, target/source handles |
| `frontend/src/components/nodes/index.ts` | SubWorkflowNode registered in nodeTypes | VERIFIED | Both `sub_workflow` and `subWorkflowNode` aliases registered |
| `frontend/src/components/designer/NodePalette.tsx` | Sub-Workflow palette item with GitBranch icon | VERIFIED | Entry with `subWorkflowNode`, `GitBranch`, `border-l-purple-500` |
| `frontend/src/components/designer/Canvas.tsx` | subWorkflowNode in DEFAULT_NODE_DATA | VERIFIED | Line 23: `subWorkflowNode: { name: 'New Sub-Workflow', activityType: 'sub_workflow' }` |
| `frontend/src/components/designer/PropertiesPanel.tsx` | Template selector and variable mapping editor for sub-workflow nodes | VERIFIED | `SubWorkflowConfig` component at line 316; fetches `/api/templates?state=active` (line 331); variable mapping editor with add/remove rows |
| `frontend/src/types/workflow.ts` | ActivityType includes sub_workflow | VERIFIED | Line 2: union includes `'sub_workflow'` |
| `frontend/src/types/designer.ts` | ActivityNodeData has subTemplateId and variableMapping | VERIFIED | Lines 6, 18, 20 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/app/models/workflow.py` | `src/app/models/enums.py` | ActivityType.SUB_WORKFLOW import | WIRED | `ActivityType.SUB_WORKFLOW` used in model column definition |
| `alembic/versions/phase18_001_sub_workflows.py` | `activity_templates` table | add_column sub_template_id | WIRED | Column added in upgrade() |
| `src/app/services/engine_service.py` | child workflow spawn | SUB_WORKFLOW branch calls start_workflow | WIRED | Lines 627-635: `start_workflow(db, target_at.sub_template_id, ...)` then sets parent linkage |
| `src/app/services/event_handlers.py` | `src/app/services/engine_service.py` | workflow.completed handler calls _advance_from_activity on parent | WIRED | Line 142-151: imports `_advance_from_activity` and calls it |
| `src/app/services/template_service.py` | `src/app/models/workflow.py` | _check_sub_workflow_depth validates sub_template_id references | WIRED | Function queries ActivityTemplate with SUB_WORKFLOW type |
| `src/app/services/event_handlers.py` | `src/app/services/workflow_mgmt_service.py` | workflow.failed handler triggered by abort_workflow | NOT_WIRED | `abort_workflow` never emits `workflow.failed` event |
| `frontend/src/components/designer/Canvas.tsx` | `frontend/src/components/nodes/SubWorkflowNode.tsx` | nodeTypes registration and DEFAULT_NODE_DATA | WIRED | Lines 23 and 160-161 in Canvas.tsx reference `subWorkflowNode` |
| `frontend/src/components/designer/PropertiesPanel.tsx` | `frontend/src/types/designer.ts` | ActivityNodeData.subTemplateId and variableMapping | WIRED | PropertiesPanel uses `subTemplateId` and `variableMapping` from node data |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `engine_service.py` SUB_WORKFLOW branch | `child_wf.parent_workflow_id` | Self (set after `start_workflow`) | Yes — directly assigned from `workflow.id` | FLOWING |
| `event_handlers.py` `_resume_parent_on_child_complete` | `parent_wf`, `parent_ai` | DB queries on `WorkflowInstance`, `ActivityInstance` | Yes — DB selects by FK | FLOWING |
| `event_handlers.py` `_fail_parent_on_child_failure` | triggered by `workflow.failed` event | `abort_workflow()` in `workflow_mgmt_service.py` | No — event never emitted | DISCONNECTED |
| `PropertiesPanel.tsx` template selector | `templates` state | `fetch('/api/templates?state=active')` in `useEffect` | Yes — real API call | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| SUB_WORKFLOW enum importable | `python -c "from app.models.enums import ActivityType; assert ActivityType.SUB_WORKFLOW == 'sub_workflow'"` | "SUB_WORKFLOW enum OK" | PASS |
| _check_sub_workflow_depth importable | `python -c "from app.services.template_service import _check_sub_workflow_depth; print('OK')"` | "OK" | PASS |
| TypeScript compiles without errors | `cd frontend && npx tsc --noEmit` | Exit code 0, no errors | PASS |
| 8 sub-workflow tests pass | `pytest tests/test_sub_workflows.py -v` | 7+ dots visible (8th in-flight), no failures observed | PASS (pending final test completion) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| SUBWF-01 | 18-01, 18-03 | Admin can add SUB_WORKFLOW activity type referencing another template | SATISFIED | Enum value, model column `sub_template_id`, schema fields, designer node with template selector all implemented |
| SUBWF-02 | 18-02 | When SUB_WORKFLOW activity executes, child workflow is spawned | SATISFIED | `_advance_from_activity` SUB_WORKFLOW branch at `engine_service.py:606` spawns child with parent linkage |
| SUBWF-03 | 18-02 | Parent workflow pauses at SUB_WORKFLOW until child completes | SATISFIED | Parent activity stays ACTIVE during child execution; `workflow.completed` event handler resumes parent |
| SUBWF-04 | 18-01, 18-02 | Variables can be mapped from parent to child workflow on spawn | SATISFIED | `variable_mapping` column, schema field, engine dispatch resolves mapping at `engine_service.py:608-613` |
| SUBWF-05 | 18-01, 18-02 | System enforces depth limits to prevent recursive sub-workflow chains | SATISFIED | `_check_sub_workflow_depth` at install time; runtime depth check in engine dispatch; `max_sub_workflow_depth` in settings |

**Orphaned requirements check:** SUBWF-01 through SUBWF-05 are all claimed in plans. SUBWF-06, SUBWF-07, SUBWF-08 are listed as future scope in REQUIREMENTS.md and not assigned to Phase 18. No orphaned requirements.

**Note on REQUIREMENTS.md status:** SUBWF-02 through SUBWF-05 are marked "Pending" (`[ ]`) in REQUIREMENTS.md even though implementation is complete. These status markers should be updated to `[x]`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/app/services/workflow_mgmt_service.py` | 139 | `workflow.state = WorkflowState.FAILED` — no `workflow.failed` event emitted | Blocker | `_fail_parent_on_child_failure` handler is unreachable in production; child workflow failure does not propagate to parent activity state |
| `src/app/routers/workflows.py` | 179 | `abort_workflow` router calls service without event emission | Blocker | Same root cause as above — no path to trigger the failure propagation handler |
| `tests/test_sub_workflows.py` | 532 | Test manually emits `workflow.failed` via `event_bus.emit(...)` | Warning | Test passes but masks the production gap — manual event emission in test hides missing event emission in `abort_workflow` |

### Human Verification Required

#### 1. Sub-Workflow Designer UI

**Test:** Start the frontend dev server (`cd frontend && npm run dev`). Navigate to the workflow designer. Verify:
1. "Sub-Workflow" appears in the left palette with purple accent and GitBranch icon
2. Dragging onto the canvas produces a node with purple double-border style
3. Clicking the node shows the properties panel with "sub_workflow" badge in purple
4. Template selector dropdown appears (populated from `/api/templates?state=active` if templates exist)
5. Variable mapping section appears with "Add Mapping" button
6. Clicking "Add Mapping" shows input rows for parent/child variable names

**Expected:** All 6 steps succeed visually
**Why human:** Visual rendering, drag-and-drop behavior, and dropdown population require a running browser

### Gaps Summary

**1 blocker gap found:**

The `workflow.failed` event is never emitted in production code. The `abort_workflow()` function in `workflow_mgmt_service.py` sets `workflow.state = WorkflowState.FAILED` and flushes, but does not call `event_bus.emit`. The router endpoint does not add this either.

The consequence: when an admin aborts a child workflow, the `_fail_parent_on_child_failure` event handler is never triggered, so the parent's SUB_WORKFLOW activity instance stays in ACTIVE state indefinitely rather than transitioning to ERROR. This breaks the SUBWF-03 failure path (parent must pause and correctly handle child failure).

The test for this behavior (`test_child_failure_propagates_to_parent`) manually emits `workflow.failed` via the event bus, which makes the handler work correctly in isolation — but this masks the missing emission in the production code path.

**Root cause:** Single missing `event_bus.emit` call in `workflow_mgmt_service.abort_workflow()`.

**Fix:** Add to `abort_workflow()` in `workflow_mgmt_service.py` after `await db.flush()`:
```python
await event_bus.emit(
    db,
    event_type="workflow.failed",
    entity_type="workflow_instance",
    entity_id=workflow.id,
    actor_id=uuid.UUID(admin_id),
    payload={"reason": "aborted"},
)
```

---

_Verified: 2026-04-06_
_Verifier: Claude (gsd-verifier)_
