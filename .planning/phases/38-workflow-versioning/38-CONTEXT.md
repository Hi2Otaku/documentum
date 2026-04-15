# Phase 38: Workflow Versioning - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous YOLO mode)

<domain>
## Phase Boundary

Multiple template versions can coexist — new instances use latest installed version, running instances stay on their original immutable version. Admin can view which version each running instance uses.

Requirements: WFVER-01, WFVER-02, WFVER-03

Critical pitfall: current WorkflowInstance.process_template_id points to a mutable template row. Need immutable installed template snapshots so in-place edits never corrupt running instances.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Make installed templates immutable snapshots (new row per install, not in-place update)
- WorkflowInstance FK points to specific installed version, never changes
- Template family identified by a `template_family_id` (the original template ID)
- `is_installed` + `version` fields distinguish draft from installed versions
- Starting a workflow resolves to latest installed version of the family
- Admin UI shows version column on running workflows
- Designer shows version history of a template family

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- src/app/models/workflow.py — ProcessTemplate, WorkflowInstance
- src/app/services/template_service.py — template CRUD + install
- src/app/services/engine_service.py — start_workflow
- frontend/src/pages/DesignerPage.tsx — template designer

</code_context>

<specifics>
## Specific Ideas

None beyond research guidance.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
