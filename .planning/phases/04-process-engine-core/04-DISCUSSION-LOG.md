# Phase 4: Process Engine Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 04-process-engine-core
**Areas discussed:** Execution model, Instance startup, State machine rules, Condition expressions

---

## Execution Model

### Advancement Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Synchronous | API call evaluates flows and activates next activities in same request | ✓ |
| Async Celery task | Enqueue Celery task for evaluation | |
| Hybrid | Sync for simple, Celery for complex | |

**User's choice:** Synchronous
**Notes:** Simple, predictable, easy to test. Celery only needed later for auto activities (Phase 9).

### Parallel Branch Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| Count-based | Check all incoming source activities complete | |
| Token-based | Petri-net style tokens on flows, AND-join waits for all tokens | ✓ |
| Completion bitmap | JSON bitmap on activity instance | |

**User's choice:** Token-based
**Notes:** More formal execution semantics for enterprise-grade engine.

### Chaining Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Iterative loop | Loop: evaluate → execute if auto → repeat until manual | ✓ |
| Recursive | advance() calls advance() recursively | |
| Queue-based | In-memory queue of pending activations | |

**User's choice:** Iterative loop
**Notes:** Single call stack, no recursion risk.

---

## Instance Startup

### Document Attachment

| Option | Description | Selected |
|--------|-------------|----------|
| Optional | Start with or without documents, attach later | ✓ |
| Required | At least one document required | |
| Template-configured | Template specifies requirement | |

**User's choice:** Optional
**Notes:** Matches Documentum behavior.

### Alias Resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to Phase 6 | Basic performer_id from template, full alias resolution later | ✓ |
| Stub alias resolution | Build interface now, fill in Phase 6 | |
| Skip entirely | Null performer_id, assign later | |

**User's choice:** Defer to Phase 6
**Notes:** Phase 4 accepts optional performer overrides as simple map.

### Start Mode

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate start | POST creates + starts + advances in one call | ✓ |
| Two-step | Create Dormant, then separate start call | |
| Configurable | Default immediate, optional auto_start=false | |

**User's choice:** Immediate start
**Notes:** Most natural UX.

---

## State Machine Rules

### Activity State Representation

| Option | Description | Selected |
|--------|-------------|----------|
| Full enum + transitions | ActivityState enum with enforced valid transitions | ✓ |
| String with validation | Keep string, add validation function | |
| Minimal for Phase 4 | Just Dormant/Active/Complete | |

**User's choice:** Full enum + transitions
**Notes:** Matches workflow instance state machine pattern.

### Workflow Completion

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-finish | Engine detects End completion, marks Finished | ✓ |
| All-activities check | Finish only when ALL activities complete | |
| Explicit finish call | End sets flag, admin action finishes | |

**User's choice:** Auto-finish
**Notes:** No manual step needed.

### Halt/Resume Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Model + basic enforcement | Transitions enforced, admin endpoints in Phase 10 | ✓ |
| Fully functional now | Build halt/resume endpoints now | |
| States only, no enforcement | Define enum, don't enforce | |

**User's choice:** Model + basic enforcement
**Notes:** State machine complete, admin controls come later.

---

## Condition Expressions

### Expression Language

| Option | Description | Selected |
|--------|-------------|----------|
| Simple Python subset | Expressions like `amount > 10000 and department == 'legal'`, ast module | ✓ |
| JSON predicate objects | Structured JSON predicates | |
| Custom DSL | Minimal expression language with custom parser | |

**User's choice:** Simple Python subset
**Notes:** Familiar syntax, easy to validate.

### Sandbox Strictness

| Option | Description | Selected |
|--------|-------------|----------|
| AST whitelist | Parse ast, walk tree, whitelist allowed node types | ✓ |
| Restrictive eval | eval() with empty __builtins__ | |
| Full sandboxed interpreter | RestrictedPython or similar | |

**User's choice:** AST whitelist
**Notes:** Secure and sufficient for routing expressions.

---

## Claude's Discretion

- Engine service structure
- Token table schema design
- Workflow start endpoint shape
- Process variable template-to-instance copying
- Test strategy and fixtures

## Deferred Ideas

None — discussion stayed within phase scope
