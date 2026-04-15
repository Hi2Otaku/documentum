# Phase 39: Advanced Join Semantics - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous YOLO mode)

<domain>
## Phase Boundary

Add N-of-M, cancelling, and timeout joins to the workflow engine. Fix existing AND-join race condition (missing FOR UPDATE locking in _should_activate). Designer UI for configuring join parameters.

Requirements: JOIN-01, JOIN-02, JOIN-03, JOIN-04

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Add join_type enum: AND_JOIN, OR_JOIN, N_OF_M_JOIN, CANCELLING_JOIN, TIMEOUT_JOIN
- Add join_threshold (int) and join_timeout_hours (float) to ActivityTemplate
- Fix _should_activate() with SELECT FOR UPDATE to prevent race conditions
- N-of-M: fires when join_threshold tokens arrive out of total incoming flows
- Cancelling: when join fires, cancel all remaining incomplete branches (mark activities CANCELLED)
- Timeout: Celery Beat task checks timeout joins, fires them after duration even if not all branches complete
- Designer UI: dropdown for join type + threshold/timeout inputs on activity properties

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- src/app/services/engine_service.py — _should_activate(), advance_workflow()
- src/app/models/workflow.py — ActivityTemplate, ActivityInstance
- frontend/src/components/designer/PropertiesPanel.tsx

</code_context>

<specifics>
## Specific Ideas

None beyond research guidance.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
