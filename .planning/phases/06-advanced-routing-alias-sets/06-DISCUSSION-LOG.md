# Phase 6: Advanced Routing & Alias Sets - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 06-advanced-routing-alias-sets
**Areas discussed:** Conditional routing UX, Reject flow behavior, Alias set management, Sequential/runtime performers

---

## Conditional Routing UX

### Performer-chosen routing mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Named path selection | Each outgoing flow has a display label. User picks from labels when completing. | ✓ |
| Variable-based selection | User sets a process variable, condition expressions evaluate against it. | |
| You decide | Claude picks best approach. | |

**User's choice:** Named path selection
**Notes:** Template designer sets the labels on outgoing flows.

### Broadcast routing mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Activity-level flag | A `routing_type` field on activity template: conditional, performer_chosen, or broadcast. | ✓ |
| Flow-level attribute | Each flow has a `broadcast` boolean. | |
| You decide | Claude picks. | |

**User's choice:** Activity-level flag
**Notes:** When broadcast, all outgoing normal flows fire unconditionally.

---

## Reject Flow Behavior

### Reject target

| Option | Description | Selected |
|--------|-------------|----------|
| Follow reject flow edges | Engine follows explicit FlowType.REJECT edges. No reject flow = rejection denied. | ✓ |
| Always previous activity | Always loops back to immediately preceding activity. | |
| You decide | Claude picks. | |

**User's choice:** Follow reject flow edges
**Notes:** FlowType.REJECT already exists in the codebase from Phase 3.

### Reject state handling

| Option | Description | Selected |
|--------|-------------|----------|
| Reset to ACTIVE, new work items | Target activity resets, new work items created. Old items remain in history. Variables preserved. | ✓ |
| Reopen original work items | Original work items set back to AVAILABLE. | |
| You decide | Claude picks. | |

**User's choice:** Reset to ACTIVE, new work items
**Notes:** Preserves audit trail integrity — old work items stay as historical record.

---

## Alias Set Management

### Alias set structure and scope

| Option | Description | Selected |
|--------|-------------|----------|
| Shared alias sets | Standalone entities, templates reference by FK. Multiple templates can share. | ✓ |
| Per-template alias sets | Each template has embedded alias mappings. | |
| You decide | Claude picks. | |

**User's choice:** Shared alias sets
**Notes:** Updating the set affects future workflow starts only.

### Alias resolution timing

| Option | Description | Selected |
|--------|-------------|----------|
| At workflow start | Mappings snapshotted at start. Mid-workflow changes don't affect running instances. | ✓ |
| At activity activation | Aliases resolve lazily at each activity. More dynamic. | |
| You decide | Claude picks. | |

**User's choice:** At workflow start
**Notes:** Consistent with Documentum's model.

---

## Sequential/Runtime Performers

### Sequential performer storage and rejection

| Option | Description | Selected |
|--------|-------------|----------|
| JSON list on activity template | `performer_list` JSON field with ordered IDs. Rejection goes to previous in list. | ✓ |
| Separate PerformerSequence table | Join table with position. More normalized. | |
| You decide | Claude picks. | |

**User's choice:** JSON list on activity template
**Notes:** All must complete for activity to be COMPLETE.

### Runtime selection mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Select from group members | Activity has candidate group. Performer selects from group members via API. | ✓ |
| Free-text user ID | Any valid user ID accepted. Maximum flexibility, no guardrails. | |
| You decide | Claude picks. | |

**User's choice:** Select from group members
**Notes:** Engine rejects completion if no selection provided.

---

## Claude's Discretion

- Expression evaluator extensions for new condition patterns
- Internal tracking for sequential performer position
- Broadcast routing token/join handling details

## Deferred Ideas

None — discussion stayed within phase scope
