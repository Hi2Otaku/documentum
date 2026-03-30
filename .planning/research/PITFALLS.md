# Domain Pitfalls

**Domain:** Workflow Engine / BPM System (Documentum Clone)
**Researched:** 2026-03-30

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or fundamentally broken systems.

### Pitfall 1: AND-Join / OR-Join Synchronization Deadlocks

**What goes wrong:** Parallel branches (AND-split) converge at a join gateway, but the join never fires because one branch was skipped by a conditional, or the wrong gateway type is used at the merge point. The workflow instance freezes permanently.

**Why it happens:** Mixing gateway types (e.g., AND-split with OR-join, or vice versa) is extremely error-prone. An AND-join waits for ALL incoming tokens, but if a conditional path skipped one branch, that token never arrives -- deadlock. OR-joins have the inverse problem: determining which branches were actually activated and should be waited for (the "OR-Join problem" in BPM literature).

**Consequences:** Workflow instances get permanently stuck. No automatic recovery. Users see tasks vanish into a black hole. In a Documentum clone with parallel legal/financial review, this is the contract approval workflow's most likely failure mode.

**Prevention:**
- Enforce structural validation at design time: every split gateway must have a matching join of the same type
- Track active branch tokens explicitly per workflow instance (token-based execution model, not just "current activity" tracking)
- For conditional splits, always emit a token down a default path so AND-joins always receive all expected tokens
- Build a "stuck instance detector" that queries for instances with no progress beyond a configurable timeout

**Detection:** Workflow instances in "Running" state with no active work items for extended periods. Dashboard metric: average time-in-activity exceeding SLA by 10x+.

**Phase relevance:** Must be solved in the core engine phase (flow routing implementation). Retrofitting token tracking is a rewrite.

---

### Pitfall 2: Race Conditions in Parallel Activity Completion

**What goes wrong:** Two parallel activities complete at nearly the same time. Both try to update the workflow instance state and evaluate the join condition simultaneously. One update is lost (last-write-wins), or both conclude they are the "last to arrive" and both trigger the downstream activity -- which then executes twice.

**Why it happens:** Workflow state is stored in a database. Without transactional consistency between "mark my activity complete" and "check if all parallel branches are done," concurrent completions race. This is not a theoretical concern -- it happens under normal usage whenever two reviewers finish within seconds of each other.

**Consequences:** Duplicate downstream activity execution (double emails, double approvals, double state transitions). Or conversely, the join never fires because both threads read "1 of 2 complete" before either writes "2 of 2 complete."

**Prevention:**
- Use database-level optimistic locking (version column) on the workflow instance row
- Make join evaluation atomic: SELECT FOR UPDATE on the instance, count completed branches, and advance -- all in one transaction
- Make all activity completion handlers idempotent: completing the same activity twice should be a no-op, not a duplicate
- Use a single-threaded-per-instance pattern: route all state mutations for a given workflow instance through a serial queue or lock

**Detection:** Duplicate work items in user inboxes. Activity audit log showing the same transition fired twice. Integration tests with concurrent completion scenarios.

**Phase relevance:** Core engine phase. Must be designed into the data model from day one -- concurrency control retrofitting is painful.

---

### Pitfall 3: Workflow Template Versioning vs. Running Instances

**What goes wrong:** An administrator modifies a workflow template (adds a new approval step, changes routing). Running instances that were started under the old template version break because the engine tries to apply the new template to in-flight processes. Activities reference steps that no longer exist, or new required steps are missing from the instance's history.

**Why it happens:** Naive implementations store a reference from instance to template (foreign key to the "current" template). When the template is updated in-place, all running instances are affected. This is the single most common architectural mistake in custom workflow engines.

**Consequences:** Running workflow instances crash, get stuck, or skip steps. Audit trail becomes inconsistent (instance history references activities that no longer exist in the template). In a compliance-oriented system like Documentum, this is catastrophic.

**Prevention:**
- Immutable versioned templates: every edit creates a new version, never modifies in-place
- Running instances pin to the template version they started with
- New instances always start on the latest published version
- Provide an optional migration tool for admins who explicitly want to migrate running instances to a new template version (with warnings and validation)
- Store the full template snapshot (or version ID) with each workflow instance

**Detection:** After template modification, running instances showing errors or unexpected behavior. Template table having UPDATE operations instead of only INSERTs.

**Phase relevance:** Database schema design phase. The instance-to-template relationship must be versioned from the first migration. Adding versioning later requires migrating all existing instances.

---

### Pitfall 4: Celery/Background Worker Task Loss

**What goes wrong:** The workflow agent (background daemon executing auto activities) loses tasks. A worker crashes mid-execution, and the task disappears because it was already acknowledged. Or tasks pile up in a dead state with no recovery path.

**Why it happens:** Celery's default behavior sends acknowledgment BEFORE task execution (early ack). If the worker crashes during execution, the broker considers the message handled. Additionally, Celery has no first-class dead letter queue support, so tasks that repeatedly fail have no standardized recovery path.

**Consequences:** Auto activities silently never execute. Workflow instances stall waiting for an auto activity completion signal that will never come. In a Documentum clone, this means methods (Python equivalents of dm_method) fail to run, and documents are stuck mid-process with no visible error.

**Prevention:**
- Set `task_acks_late = True` in Celery config so tasks are acknowledged only after successful completion
- Set `task_reject_on_worker_lost = True` so crashed-worker tasks are requeued
- Implement a dead letter queue pattern: after N retries, move to a DLQ table for manual inspection
- Build a "watchdog" that scans for auto activities in "executing" state beyond their expected duration and triggers re-execution or alerts
- Make all auto activities idempotent (safe to retry)
- Store task execution state in the database, not just in the broker -- the DB is the source of truth

**Detection:** Auto activities in "executing" state for longer than max expected duration. Celery worker logs showing task receipt but no completion. Gap between tasks dispatched and tasks completed.

**Phase relevance:** Background processing / Workflow Agent phase. Configuration must be correct from the start, but the watchdog can be added later.

---

### Pitfall 5: Audit Trail as an Afterthought

**What goes wrong:** Audit logging is bolted on after the core engine is built. The audit trail has gaps -- some state transitions are logged, others are not. Timestamps are inconsistent. The audit log captures what happened but not who decided, or captures the decision but not the state of the document at that point.

**Why it happens:** Developers treat audit as "just add a log statement." But audit in a compliance-oriented system like Documentum requires capturing: who, what, when, on which document version, with what decision, from which activity, and the resulting state change. Missing any dimension makes the audit incomplete for compliance purposes.

**Consequences:** Audit trail has gaps that become visible during compliance review. Reconstructing "what happened to this document" requires correlating multiple tables manually. Retroactively adding audit events to already-deployed code paths is tedious and error-prone.

**Prevention:**
- Design audit as a cross-cutting concern from the start: every state transition goes through a single function that creates the audit record atomically with the state change
- Use an append-only audit table (never update or delete audit records)
- Capture a complete audit event: timestamp, actor, action, activity_id, workflow_instance_id, document_id, document_version, old_state, new_state, decision, comments
- Write the audit record in the same database transaction as the state change -- if the transaction rolls back, the audit record rolls back too (consistency)
- Consider event sourcing: the audit log IS the source of truth, and current state is derived from it

**Detection:** Manual review: pick a completed workflow instance and try to reconstruct the full history from audit records alone. Any gaps indicate missing instrumentation.

**Phase relevance:** Must be designed into the core engine from Phase 1. The audit event structure and the "all mutations go through one function" pattern must exist before any feature code is written.

---

### Pitfall 6: ACL/Permission Drift Between Workflow Steps

**What goes wrong:** Documentum-style workflows change document permissions at each step (e.g., "during legal review, only legal team can edit"). But permissions set by Step 3 are not properly cleaned up before Step 4's permissions are applied. Over time, documents accumulate stale permission entries, creating either security holes (too much access) or lockouts (too little access).

**Why it happens:** Each activity independently sets permissions on entry but does not know or clean up what the previous activity set. Without a clear "permission lifecycle" tied to workflow progression, permissions become additive -- they only grow, never shrink.

**Consequences:** Documents accessible to users who should no longer have access (security violation). Or documents locked to the point where even the current performer cannot access them. Both failures are silent -- no error is thrown, the user simply sees or doesn't see the document.

**Prevention:**
- Define a permission model that is workflow-aware: each activity declares its required permissions, and the engine applies them as a complete replacement (not additive) when the activity starts
- Store the "pre-workflow" permission state so it can be restored when the workflow completes or is cancelled
- Implement permission snapshots at each activity transition in the audit trail
- Test permission state explicitly: after each activity transition, assert that the document's effective permissions match expectations
- Separate "workflow permissions" (temporary, tied to the instance) from "permanent permissions" (the document's base ACL)

**Detection:** Query for documents where ACL entries reference workflow activities from completed/cancelled workflow instances. Users reporting unexpected access or access denial.

**Phase relevance:** ACL/Security integration phase. The permission model (replacement vs. additive) is an architectural decision that affects the data model.

---

## Moderate Pitfalls

### Pitfall 7: State Machine Explosion in Complex Routing

**What goes wrong:** The workflow instance lifecycle (Dormant, Running, Halted, Failed, Finished) seems simple, but combined with activity states (NotStarted, Active, Completed, Skipped, Failed, Delegated) and work item states (Acquired, Available, Completed, Delegated), the total state space explodes. Edge cases between states are not handled: What happens when a Halted workflow has an activity that was Delegated? What about resuming a Failed workflow where some activities were Completed and one was mid-execution?

**Why it happens:** Developers model the "happy path" state machine first and assume edge cases can be handled later. But the number of valid state combinations grows multiplicatively, and each edge case requires explicit handling.

**Prevention:**
- Document every valid state combination in a state transition table before writing code
- Define illegal state combinations explicitly and add database constraints preventing them
- Use hierarchical state machines: workflow-level states constrain which activity-level states are valid
- Write property-based tests that generate random state transitions and verify invariants hold
- Map internal engine states to simplified user-facing states (users see 4-5 states, engine tracks 15+)

**Detection:** Bug reports describing "weird" behavior -- items appearing and disappearing from inboxes, workflows showing contradictory statuses. Production instances in unexpected state combinations.

**Phase relevance:** Core engine and state machine phase. The state transition table should be the first design artifact.

---

### Pitfall 8: Visual Designer to Engine Schema Mismatch

**What goes wrong:** The visual workflow designer (drag-and-drop frontend) stores workflow definitions in a format (JSON graph of nodes/edges) that does not cleanly map to what the execution engine needs. The designer allows constructs the engine cannot execute, or the engine supports features the designer cannot express.

**Why it happens:** The designer and engine are built by different efforts (frontend vs. backend) with different mental models. The designer thinks in terms of boxes and arrows; the engine thinks in terms of activities, flows, conditions, and performers. Without a shared schema, a translation layer accumulates bugs.

**Prevention:**
- Define a single canonical workflow schema (JSON/YAML) that BOTH the designer and engine use directly
- The designer is a visual editor for this schema, not a separate format
- Validate the schema on save in the designer (run the same validation the engine would run)
- Start with a minimal schema and extend it -- do not try to support every Documentum feature in the designer on day one
- Build the engine first with API/JSON-based workflow creation; add the visual designer second, consuming the same API

**Detection:** Workflows that render correctly in the designer but fail to start. Workflows that run successfully but display incorrectly in the designer. Diverging field names between frontend and backend models.

**Phase relevance:** Architecture phase. Define the shared schema before building either the designer or the engine. Build the engine first, designer second.

---

### Pitfall 9: Naive Timer/Timeout Implementation

**What goes wrong:** SLA deadlines, activity timeouts, and escalation timers are implemented using in-memory schedulers (e.g., Python's `sched` module, `asyncio.sleep`, or Celery countdown tasks). When the server restarts, all pending timers are lost. Activities that should have timed out continue waiting forever.

**Why it happens:** In-memory timers are the easiest to implement. Developers plan to "make them durable later" but the complexity of restoring timer state after restart is significant enough that it keeps getting deferred.

**Prevention:**
- Store all timer/deadline information in the database: (instance_id, activity_id, timer_type, fires_at)
- Run a periodic "timer poller" (every 30-60 seconds) that queries for overdue timers and fires them
- Never rely on in-memory timer state -- the database is the source of truth
- For Celery ETA/countdown tasks: treat them as optimistic optimization only, with the database poller as the fallback
- Design the timer system before implementing SLA or escalation features

**Detection:** After server restart, check if pending escalations still fire on time. Monitor for activities that have exceeded their timeout without escalation.

**Phase relevance:** Process Engine phase. Timer architecture must be durable from the start.

---

### Pitfall 10: Document Version Confusion in Workflow Packages

**What goes wrong:** A document attached to a workflow package is edited during the workflow, creating new versions. The workflow engine references "document X" without specifying which version. Different activities in the same workflow see different document versions. The final approval may be approving a version that is not the latest, or the archived version is not the one that was actually reviewed.

**Why it happens:** Document IDs and document version IDs are conflated. The package attachment stores a document ID (mutable, always points to latest) instead of a version ID (immutable, specific snapshot). This works fine in sequential workflows but breaks in parallel ones.

**Prevention:**
- Distinguish between document identity (persistent ID across versions) and document version (immutable snapshot)
- Workflow packages should reference both: "document X, currently at version 3"
- When a parallel branch starts, snapshot the document version for that branch
- When branches merge, detect and handle version conflicts explicitly (similar to git merge conflicts)
- Audit trail entries must reference the specific document version, not just the document ID

**Detection:** Compare the document version referenced in the approval audit record with the document version stored in the archive. Any mismatch indicates the bug is present.

**Phase relevance:** Document management and packages phase. The dual-ID model (document + version) must be in the database schema from the start.

---

## Minor Pitfalls

### Pitfall 11: Work Queue Starvation

**What goes wrong:** Work queues (shared task pools) allow any qualified user to claim tasks. But one fast user claims everything, or tasks sit unclaimed because the queue notification mechanism is pull-only (users must check their queue) rather than push.

**Prevention:**
- Implement fair-distribution policies (round-robin assignment, max-claims-per-user limits)
- Add queue monitoring to the BAM dashboard: unclaimed items aging beyond threshold
- Support both pull (user checks queue) and push (notification/email when items arrive) models

**Phase relevance:** Work queues phase. Can be refined after initial implementation.

---

### Pitfall 12: Delegation Cycles

**What goes wrong:** User A delegates to User B. User B is also unavailable and delegates to User C. User C delegates back to User A. Tasks enter an infinite delegation loop and never reach anyone.

**Prevention:**
- Detect delegation cycles before applying delegation (walk the delegation chain, reject if cycle found)
- Set a maximum delegation depth (e.g., 3 hops)
- Log delegation chains in the audit trail for debugging

**Phase relevance:** Delegation feature phase. Simple cycle detection at delegation setup time.

---

### Pitfall 13: Process Variable Type Safety

**What goes wrong:** Process variables are stored as untyped key-value pairs (all strings, or Python dicts). A routing condition checks `if amount > 10000` but `amount` is a string "5000" which compares lexicographically, not numerically. The condition evaluates incorrectly, routing the workflow down the wrong path.

**Prevention:**
- Define process variable types in the workflow template schema (string, integer, float, boolean, date)
- Validate and coerce variable types when they are set
- Evaluate routing conditions with type-aware comparison operators
- Write tests specifically for boundary conditions in routing expressions

**Phase relevance:** Process variables and conditional routing phase.

---

### Pitfall 14: Ignoring Workflow Cancellation and Cleanup

**What goes wrong:** Building the "happy path" (start to finish) but not implementing cancellation. When an admin halts or cancels a running workflow: work items remain in user inboxes, documents retain workflow-specific permissions, timers continue firing, and auto activities that were in-flight complete and try to advance a cancelled workflow.

**Prevention:**
- Design cancellation as a first-class operation from the start
- Cancellation must: remove all pending work items, restore document permissions to pre-workflow state, cancel all pending timers, mark in-flight auto activities as cancelled (and handle their completion gracefully)
- Test cancellation at every possible point in the workflow lifecycle

**Phase relevance:** Core engine phase, but commonly deferred. Must be addressed before the system is used with real documents.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Database schema design | Versioning not built into template-instance relationship (Pitfall 3) | Immutable versioned templates from the first migration |
| Core engine / state machine | AND-join deadlocks (Pitfall 1), race conditions (Pitfall 2) | Token-based execution model, optimistic locking, atomic join evaluation |
| Background processing | Task loss on worker crash (Pitfall 4) | `acks_late=True`, reject on worker lost, database as source of truth |
| Flow routing | State explosion (Pitfall 7), variable type errors (Pitfall 13) | State transition tables, typed variables |
| Document management | Version confusion in packages (Pitfall 10) | Dual document-ID + version-ID model |
| ACL / Security | Permission drift (Pitfall 6) | Replacement-based permissions, pre-workflow permission snapshots |
| Visual designer | Designer-engine schema mismatch (Pitfall 8) | Single canonical schema, build engine first |
| Timers / SLA | Lost timers on restart (Pitfall 9) | Database-stored timers, periodic poller |
| Audit trail | Incomplete audit data (Pitfall 5) | Cross-cutting audit from day one, event sourcing consideration |
| Delegation | Delegation cycles (Pitfall 12) | Cycle detection, max depth |
| Work queues | Starvation / unfair distribution (Pitfall 11) | Fair distribution policies, queue aging monitoring |
| Cancellation | Incomplete cleanup (Pitfall 14) | First-class cancellation operation with full cleanup |

## Sources

- [Temporal: Designing a Workflow Engine from First Principles](https://temporal.io/blog/workflow-engine-principles)
- [Building a Distributed Workflow Engine from Scratch](https://dev.to/acoh3n/building-a-distributed-workflow-engine-from-scratch-22kl)
- [WorkflowEngine.io: Workflow Engine vs. State Machine](https://workflowengine.io/blog/workflow-engine-vs-state-machine/)
- [WorkflowEngine.io: Why Developers Never Use State Machines](https://workflowengine.io/blog/why-developers-never-use-state-machines/)
- [Hatchet: Problems with Celery](https://hatchet.run/blog/problems-with-celery)
- [Parallel Gateway Synchronization](https://humanscalebusiness.org/lessons/parallel-gateway-synchronization/)
- [Red Gate: Database Design for Audit Logging](https://www.red-gate.com/blog/database-design-for-audit-logging/)
- [Camunda: Versioning Process Definitions](https://docs.camunda.io/docs/components/best-practices/operations/versioning-process-definitions/)
- [WorkflowEngine.io: Schema Versioning](https://workflowengine.io/documentation/execution/scheme-update/)
- [Flowable Forum: Stuck Process Instances](https://forum.flowable.org/t/stuck-process-instances-how-to-find-them/9579)
- [5 Common Pitfalls in Enterprise BPM Implementation](https://www.flyingdog.de/portal/en/blog/bpm-implementation-mistakes-avoid-enterprise/)
- [7 BPM Challenges Enterprises Face](https://kissflow.com/workflow/bpm/business-process-management-challlenges/)
- [WorkflowEngine.io: Rules and Security Integration](https://workflowengine.io/documentation/scheme/rules/)
- [Building a Visual Flow Designer for Telecom Order Management](https://medium.com/turkcell/building-a-visual-flow-designer-for-telecom-order-management-a-deep-dive-into-msp-flow-238ce2d789e0)
- [WorkflowBuilder.io: Version Control in Workflows](https://www.workflowbuilder.io/blog/how-to-implement-version-control-and-change-tracking-in-workflows)
