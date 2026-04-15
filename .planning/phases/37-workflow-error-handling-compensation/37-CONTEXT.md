# Phase 37: Workflow Error Handling & Compensation - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous YOLO mode)

<domain>
## Phase Boundary

Add declarative exception handlers and compensation activities to the workflow engine. Template designers attach error handlers to activities that execute on failure. Compensation activities undo completed work in reverse chronological order. Operators can retry or skip failed activities from the UI.

Requirements: WFERR-01, WFERR-02, WFERR-03, WFERR-04

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
Key research guidance (Saga pattern from Camunda/Flowable):

- **Error handler**: New activity type or property on existing activities. When activity fails, engine checks for attached error handler and executes it instead of halting.
- **Compensation handler**: Activities can have a compensation activity defined. On flow-level failure, engine runs compensation handlers in reverse chronological order of completed activities.
- **DB model changes**: Add error_handler_activity_id and compensation_activity_id to ActivityTemplate. Add error state tracking to ActivityInstance.
- **Engine changes in engine_service.py**: Modify activity failure path to check for error handlers. Add compensation trigger on workflow-level failure.
- **Retry/skip UI**: Add retry and skip buttons to failed activities in the workflow operations page. Backend endpoints for retry (re-execute) and skip (mark complete, advance).
- **Designer UI**: Add ability to attach error handlers and compensation activities in the visual workflow designer.

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- src/app/services/engine_service.py — workflow execution engine
- src/app/models/workflow.py — ActivityTemplate, ActivityInstance models
- frontend/src/pages/DesignerPage.tsx — visual workflow designer

</code_context>

<specifics>
## Specific Ideas

None beyond research guidance.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
