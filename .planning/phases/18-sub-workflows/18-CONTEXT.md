# Phase 18: Sub-Workflows - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via autonomous YOLO mode)

<domain>
## Phase Boundary

Workflow designers can compose complex processes from reusable sub-workflows, with the parent pausing until the child completes. Admin can add a SUB_WORKFLOW activity node in the workflow designer and configure it to reference another installed template. When execution reaches a SUB_WORKFLOW activity, a child workflow instance is spawned and the parent workflow visibly pauses. When the child completes, the parent resumes automatically. Variables are mapped from parent to child. System enforces depth limits to prevent infinite recursion.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — discuss phase was skipped per user setting. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — discuss phase skipped. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
