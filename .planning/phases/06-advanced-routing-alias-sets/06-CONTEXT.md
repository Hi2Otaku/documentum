# Phase 6: Advanced Routing & Alias Sets - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds all remaining Documentum routing patterns and performer assignment modes to the engine: conditional routing (performer-chosen, expression-based, broadcast), reject flows, sequential and runtime performer selection, and alias set resolution. After this phase, every routing pattern described in the Documentum spec works end-to-end.

</domain>

<decisions>
## Implementation Decisions

### Conditional Routing
- **D-01:** Performer-chosen routing uses named path selection. Each outgoing flow has a `display_label` field. When completing a work item at a performer-chosen activity, the user selects from these labels. The engine fires only the selected flow.
- **D-02:** An activity-level `routing_type` field controls routing behavior: `conditional` (evaluate expressions), `performer_chosen` (user picks path), or `broadcast` (all outgoing flows fire unconditionally). Default is `conditional` for backward compatibility.

### Reject Flows
- **D-03:** Rejection follows explicit reject flow edges (`FlowType.REJECT`). The engine traverses reject flows the same way it traverses normal flows, but triggered by rejection instead of completion. If no reject flow exists from the current activity, rejection is denied (error).
- **D-04:** When a reject flow activates a previous activity, that activity resets from COMPLETE to ACTIVE with new work items created for its original performers. Old work items remain in history. Process variables are preserved so the re-performer sees updated context.

### Alias Sets
- **D-05:** Alias sets are shared, standalone entities (own DB table: `AliasSet` + `AliasMapping`). Templates reference an alias set by FK. Multiple templates can share the same alias set. Updating the set affects future workflow starts only.
- **D-06:** Alias-to-user mappings are resolved (snapshotted) at workflow start time. The resolved mappings are stored on the workflow instance so mid-workflow alias changes don't affect running instances.

### Sequential & Runtime Performers
- **D-07:** Sequential performers use a `performer_list` JSON field on ActivityTemplate — an ordered array of user/group IDs. Task goes to performer[0] first, then performer[1] on completion, etc. On rejection within the sequence, it goes back to the previous performer in the list. All must complete for the activity to be COMPLETE.
- **D-08:** Runtime selection: activity has a candidate group (via `performer_id` pointing to a group). When completing, the current performer selects the next performer from that group's members (pass `next_performer_id` in completion request). Engine rejects completion if no selection provided.
- **D-09:** New `PerformerType` enum values needed: `SEQUENTIAL` and `RUNTIME_SELECTION` added alongside existing USER, GROUP, SUPERVISOR, ALIAS.

### Claude's Discretion
- Expression evaluator extensions (if needed for new condition patterns)
- Internal state tracking for sequential performer position (e.g., a `current_performer_index` field on ActivityInstance or WorkItem)
- Whether broadcast routing needs special token/join handling or just fires all flows

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Engine Code
- `src/app/services/engine_service.py` — Core advancement loop, resolve_performers(), token-based Petri-net model
- `src/app/services/expression_evaluator.py` — Sandboxed expression evaluation for condition routing
- `src/app/models/enums.py` — All enum types including FlowType.REJECT, PerformerType.ALIAS (already defined)
- `src/app/models/workflow.py` — ActivityTemplate, FlowTemplate, WorkItem, ExecutionToken models
- `src/app/services/inbox_service.py` — complete_inbox_item and reject_inbox_item (will need path selection and next_performer params)

### Spec Reference
- `documentum-workflow-management.docx` — Original Documentum spec (Vietnamese, March 2026) — routing patterns, alias sets, performer assignment modes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FlowType.REJECT` enum already exists — just not traversed by the engine yet
- `PerformerType.ALIAS` enum exists — `resolve_performers()` currently returns `[]` for it
- `condition_expression` field on FlowTemplate already evaluated during advancement
- Expression evaluator with sandboxed eval is ready for reuse
- Token-based Petri-net advancement loop handles AND/OR joins — extend for reject flow tokens

### Established Patterns
- Service layer pattern: routers delegate to service functions, services handle business logic and audit
- `resolve_performers()` uses match/case on performer_type string — extend with new cases
- `_advance_workflow()` iterative queue loop processes outgoing flows — add reject flow handling
- Work item creation loop in advancement already handles multi-performer fan-out (GROUP)

### Integration Points
- `engine_service.complete_work_item()` — needs `selected_path` param for performer-chosen routing
- `engine_service.reject_work_item()` or new function — needs to trigger reject flow traversal
- `inbox_service.complete_inbox_item()` — needs to pass through `selected_path` and `next_performer_id`
- `inbox_service.reject_inbox_item()` — needs to trigger engine reject flow instead of just state change
- `start_workflow()` — needs to resolve alias mappings and store snapshot
- ActivityTemplate model — needs `routing_type`, `performer_list`, `display_label` fields

</code_context>

<specifics>
## Specific Ideas

- Named paths with display labels match Documentum's Process Builder UX where designers label outgoing flows
- Alias snapshot at start time is consistent with Documentum's model where performer overrides are set at instantiation
- Sequential performer rejection loops within the performer list, not via reject flows (separate mechanism)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-advanced-routing-alias-sets*
*Context gathered: 2026-03-31*
