# Phase 17: Timer Activities & Escalation - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped via autonomous YOLO mode)

<domain>
## Phase Boundary

Work items automatically enforce deadlines and escalate when overdue, so tasks do not silently stall. Admin can set deadline durations on activity templates in the workflow designer. When a workflow reaches a timed activity, the resulting work item receives a due date. A Celery Beat task periodically detects overdue work items and triggers escalation actions (priority bump, reassignment, or notification). Escalated work items show updated priority or reassigned performer, and the affected user receives a notification.

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
