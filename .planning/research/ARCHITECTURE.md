# Architecture Patterns

**Domain:** Workflow Engine / BPM System (Documentum Clone)
**Researched:** 2026-03-30

## Recommended Architecture

The system follows a **layered monolith with background workers** pattern -- not microservices. For a single-user/internal tool, microservices add orchestration complexity without benefit. The monolith shares a single database, with the Process Engine and Workflow Agent running as separate background processes (Celery workers) against that same database.

### High-Level Architecture

```
+------------------------------------------------------------------+
|                        WEB UI (Browser)                           |
|  +----------------+  +-----------+  +----------+  +----------+   |
|  | Workflow        |  | User      |  | Document |  | BAM      |   |
|  | Designer        |  | Inbox     |  | Manager  |  | Dashboard|   |
|  | (React Flow)    |  |           |  |          |  |          |   |
|  +-------+--------+  +-----+-----+  +----+-----+  +----+-----+   |
+----------|-----------------|-------------|-------------|----------+
           |                 |             |             |
           v                 v             v             v
+------------------------------------------------------------------+
|                     REST API LAYER (Django)                        |
|  +-------------+  +-----------+  +----------+  +----------+      |
|  | Process     |  | Inbox     |  | Document |  | BAM      |      |
|  | Definition  |  | & Work    |  | & Version|  | Metrics  |      |
|  | API         |  | Item API  |  | API      |  | API      |      |
|  +------+------+  +-----+----+  +----+-----+  +----+-----+      |
+---------|----------------|-----------|-------------|-------------+
          |                |           |             |
          v                v           v             v
+------------------------------------------------------------------+
|                     DOMAIN / SERVICE LAYER                        |
|  +----------------+  +------------+  +-------------+             |
|  | Process        |  | Routing    |  | Document    |             |
|  | Definition     |  | Engine     |  | Service     |             |
|  | Service        |  | (flows,    |  | (versioning,|             |
|  | (templates,    |  |  joins,    |  |  packages)  |             |
|  |  validation)   |  |  splits)   |  +-------------+             |
|  +----------------+  +------------+                              |
|  +----------------+  +------------+  +-------------+             |
|  | Work Item      |  | Security   |  | Audit       |             |
|  | Service        |  | Service    |  | Service     |             |
|  | (inbox,        |  | (ACL,      |  | (trail,     |             |
|  |  delegation,   |  |  perms)    |  |  events)    |             |
|  |  work queues)  |  +------------+  +-------------+             |
|  +----------------+                                              |
+------------------------------------------------------------------+
          |                |           |
          v                v           v
+------------------------------------------------------------------+
|                    DATA / PERSISTENCE LAYER                       |
|  +----------------------------+  +-----------------------------+ |
|  | PostgreSQL                  |  | File Storage               | |
|  | - Process definitions       |  | - Document files           | |
|  | - Workflow instances        |  | - Version content          | |
|  | - Activity instances        |  | (local filesystem or S3)   | |
|  | - Work items                |  +-----------------------------+ |
|  | - Packages & documents      |                                 |
|  | - Audit log                 |                                 |
|  | - Users, groups, ACLs       |                                 |
|  +----------------------------+                                  |
+------------------------------------------------------------------+
          ^                ^
          |                |
+------------------------------------------------------------------+
|              BACKGROUND WORKERS (Celery + Redis)                  |
|  +--------------------+  +---------------------+                 |
|  | Process Engine      |  | Workflow Agent       |                |
|  | - Advances workflow  |  | - Polls for auto     |                |
|  |   state machine      |  |   activities          |                |
|  | - Evaluates triggers |  | - Executes methods   |                |
|  | - Creates work items |  | - Handles timers     |                |
|  | - Evaluates          |  | - Retries on failure |                |
|  |   conditions         |  +---------------------+                |
|  +--------------------+                                           |
|  +--------------------+                                           |
|  | Event/Notification  |                                          |
|  | Worker              |                                          |
|  | - Emails             |                                         |
|  | - WebSocket pushes   |                                         |
|  +--------------------+                                           |
+------------------------------------------------------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | Communication Method |
|-----------|---------------|-------------------|---------------------|
| **Workflow Designer UI** | Visual drag-and-drop process template creation | Process Definition API | REST (save/load templates) |
| **User Inbox UI** | Display work items, accept user actions | Inbox API, WebSocket | REST + WebSocket (real-time) |
| **Document Manager UI** | Upload, browse, version documents | Document API | REST + multipart upload |
| **BAM Dashboard UI** | Real-time process metrics and SLA monitoring | BAM API, WebSocket | REST + WebSocket (live updates) |
| **Process Definition Service** | CRUD for dm_process, dm_activity, flows; template validation | Database | Direct ORM |
| **Routing Engine** | Evaluate flow conditions, AND/OR joins, splits, performer resolution | Database, Process Engine | Internal function calls |
| **Process Engine** | State machine runtime: advance workflows, create work items, evaluate triggers | Database, Routing Engine, Audit Service | Celery tasks + direct DB |
| **Workflow Agent** | Background daemon for auto activities: execute methods, handle timers | Database, Process Engine | Celery beat + tasks |
| **Work Item Service** | Inbox management, delegation, work queues, task claiming | Database, Security Service | Direct ORM |
| **Document Service** | File storage, versioning, package management | Database, File Storage | Direct ORM + filesystem |
| **Security Service** | ACL evaluation, permission changes at workflow steps | Database | Direct ORM |
| **Audit Service** | Immutable event log of all state changes and user actions | Database (append-only) | Direct ORM |

### Data Flow

#### 1. Process Template Creation (Design Time)

```
Designer UI
  |-- [POST /api/processes] --> Process Definition API
  |                               |-- Validate template graph (no orphan nodes, valid flows)
  |                               |-- Store dm_process + dm_activity + flow records
  |                               |-- Return process ID
  |<- [200 OK + process_id] ------+
```

#### 2. Workflow Instance Launch (Runtime)

```
User/API triggers "Start Workflow"
  |-- [POST /api/workflows] --> Workflow API
  |                               |-- Create dm_workflow instance (state=DORMANT)
  |                               |-- Attach packages (documents)
  |                               |-- Set state to RUNNING
  |                               |-- Dispatch to Process Engine (Celery task)
  |                               |      |
  |                               |      v
  |                               |  Process Engine:
  |                               |    1. Find START activity
  |                               |    2. Evaluate outgoing flows
  |                               |    3. For manual activity:
  |                               |       - Resolve performer (user/group/alias)
  |                               |       - Create dmi_workitem (state=ACQUIRED)
  |                               |       - Work item appears in user inbox
  |                               |    4. For auto activity:
  |                               |       - Queue for Workflow Agent
  |                               |    5. Log to audit trail
  |<- [200 OK + workflow_id] -----+
```

#### 3. User Completes a Work Item

```
User clicks "Complete" in Inbox
  |-- [POST /api/workitems/:id/complete] --> Work Item API
  |                                            |-- Validate user has permission
  |                                            |-- Record decision + any form data
  |                                            |-- Mark work item COMPLETE
  |                                            |-- Dispatch to Process Engine (Celery task)
  |                                            |      |
  |                                            |      v
  |                                            |  Process Engine:
  |                                            |    1. Check trigger conditions on downstream activities
  |                                            |    2. AND-join: all predecessors done? If not, wait
  |                                            |    3. OR-join: at least one done? Proceed
  |                                            |    4. Evaluate conditional flows (route selection)
  |                                            |    5. Create next work items or queue auto activities
  |                                            |    6. If no more activities: set workflow FINISHED
  |                                            |    7. Update ACLs if configured for this step
  |                                            |    8. Transition document lifecycle if configured
  |                                            |    9. Log to audit trail
  |<- [200 OK] --------------------------------+
```

#### 4. Workflow Agent Executes Auto Activity

```
Celery Beat (periodic schedule, e.g., every 5 seconds)
  |-- Workflow Agent task:
  |     1. Query for queued auto activities
  |     2. For each:
  |        a. Load the dm_method (Python callable)
  |        b. Execute with timeout
  |        c. On success: mark activity COMPLETE, trigger Process Engine advance
  |        d. On failure: retry up to N times, then mark workflow FAILED
  |        e. Log execution to audit trail
```

#### 5. Real-Time Updates (WebSocket)

```
Process Engine completes a state transition
  |-- Publish event to Redis channel
  |     |
  |     v
  |  WebSocket consumers (Django Channels):
  |    - Inbox consumer: push new/updated work items to connected users
  |    - Dashboard consumer: push updated metrics to BAM dashboard viewers
```

## Core Data Model

The data model mirrors Documentum's five core object types plus supporting entities.

### Template Layer (Design Time)

| Entity | Documentum Equivalent | Key Fields |
|--------|----------------------|------------|
| **Process** | dm_process | id, name, description, version, state (DRAFT/VALIDATED/ACTIVE), created_by |
| **ActivityDefinition** | dm_activity | id, process_id (FK), name, type (START/MANUAL/AUTO/END), performer_type, performer_id, method_id, position_x, position_y |
| **FlowDefinition** | (flow link) | id, process_id (FK), source_activity_id, target_activity_id, condition_expression, is_reject_flow |
| **AliasSet** | dm_alias_set | id, name; entries: alias_name -> user/group mapping |

### Instance Layer (Runtime)

| Entity | Documentum Equivalent | Key Fields |
|--------|----------------------|------------|
| **Workflow** | dm_workflow | id, process_id (FK), state (DORMANT/RUNNING/HALTED/FAILED/FINISHED), started_by, started_at, finished_at |
| **ActivityInstance** | (runtime activity) | id, workflow_id (FK), activity_def_id (FK), state (NOT_STARTED/RUNNING/PAUSED/COMPLETE/ERROR), started_at, completed_at |
| **WorkItem** | dmi_workitem | id, activity_instance_id (FK), assigned_to (FK user), state (ACQUIRED/DELEGATED/COMPLETE), due_date, completed_at, decision |
| **Package** | dmi_package | id, workflow_id (FK), document_id (FK), name, notes |
| **ProcessVariable** | (runtime data) | id, workflow_id (FK), name, value_type, value_json |

### Supporting Entities

| Entity | Purpose | Key Fields |
|--------|---------|------------|
| **Document** | File with version history | id, name, current_version_id, content_type, lifecycle_state |
| **DocumentVersion** | Immutable version snapshot | id, document_id (FK), version_number, file_path, checksum, created_by, created_at |
| **AuditEvent** | Append-only event log | id, timestamp, event_type, workflow_id, activity_id, user_id, details_json |
| **User** | System user | id, username, email, is_available, delegate_to (FK self) |
| **Group** | User group | id, name; members: M2M to User |
| **ACLEntry** | Permission record | id, target_type, target_id, user_or_group_id, permission_level |
| **WorkQueue** | Shared task pool | id, name, group_id (FK); items: claimed work items |
| **Method** | Auto-activity callable | id, name, module_path, function_name, timeout_seconds |

## Patterns to Follow

### Pattern 1: State Machine for Workflow Lifecycle

**What:** Each workflow instance is a finite state machine with well-defined transitions. The Process Engine is the ONLY component that mutates workflow/activity state.

**When:** Always -- this is the core pattern.

**Why:** Centralizing state transitions prevents race conditions and ensures audit trail completeness. No other component (API, UI, agent) directly changes workflow state.

```python
class WorkflowState(str, Enum):
    DORMANT = "dormant"
    RUNNING = "running"
    HALTED = "halted"
    FAILED = "failed"
    FINISHED = "finished"

VALID_TRANSITIONS = {
    WorkflowState.DORMANT: [WorkflowState.RUNNING],
    WorkflowState.RUNNING: [WorkflowState.HALTED, WorkflowState.FAILED, WorkflowState.FINISHED],
    WorkflowState.HALTED: [WorkflowState.RUNNING, WorkflowState.FAILED],
    WorkflowState.FAILED: [WorkflowState.RUNNING],  # retry
    WorkflowState.FINISHED: [],  # terminal
}

def transition_workflow(workflow, new_state):
    if new_state not in VALID_TRANSITIONS[workflow.state]:
        raise InvalidTransition(f"Cannot go from {workflow.state} to {new_state}")
    old_state = workflow.state
    workflow.state = new_state
    workflow.save()
    AuditEvent.objects.create(
        event_type="workflow_state_change",
        workflow_id=workflow.id,
        details_json={"from": old_state, "to": new_state},
    )
```

### Pattern 2: Transactional Outbox for Work Item Creation

**What:** When the Process Engine advances a workflow, work item creation and state changes happen in a single database transaction. Events for WebSocket notification are written to an outbox table in the same transaction, then delivered asynchronously.

**When:** Every time the engine creates or completes work items.

**Why:** Prevents the scenario where work items are created but inbox notifications are lost (or vice versa). This is the key reliability pattern from Temporal's architecture adapted to our simpler context.

```python
from django.db import transaction

def advance_workflow(workflow_id, completed_activity_id):
    with transaction.atomic():
        # 1. Mark current activity complete
        # 2. Evaluate next flows and trigger conditions
        # 3. Create new work items or queue auto activities
        # 4. Write outbox events for notifications
        OutboxEvent.objects.create(
            event_type="workitem_created",
            payload={"workitem_id": new_item.id, "user_id": assignee.id},
        )
    # After commit, a signal or Celery task picks up outbox events
```

### Pattern 3: Performer Resolution Chain

**What:** Activity definitions specify performer_type (SPECIFIC_USER, GROUP, ALIAS, SUPERVISOR, RUNTIME_SELECT). At runtime, the engine resolves the actual user(s) through a chain of resolution.

**When:** Creating work items for manual activities.

**Why:** Documentum supports 6+ performer assignment modes. A resolution chain keeps this logic centralized and extensible.

```python
def resolve_performers(activity_def, workflow, context):
    match activity_def.performer_type:
        case "SPECIFIC_USER":
            return [activity_def.performer_user]
        case "GROUP":
            return list(activity_def.performer_group.members.filter(is_available=True))
        case "ALIAS":
            alias_entry = workflow.alias_set.resolve(activity_def.alias_name)
            return resolve_performers(alias_entry, workflow, context)  # recursive
        case "SUPERVISOR":
            return [context.previous_performer.supervisor]
        case "RUNTIME_SELECT":
            return []  # will be resolved by user at runtime
        case "WORK_QUEUE":
            return []  # goes to shared pool, any member can claim
```

### Pattern 4: Condition Expression Evaluation

**What:** Flow conditions and gateway expressions are stored as simple expression strings evaluated against process variables using a restricted evaluator (not raw `eval()`).

**When:** Conditional routing, exclusive/inclusive gateways.

```python
import ast
import operator

SAFE_OPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.Gt: operator.gt,
    ast.LtE: operator.le, ast.GtE: operator.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
}

def evaluate_condition(expression: str, variables: dict) -> bool:
    """Safely evaluate a condition like 'amount > 10000 and department == "legal"'"""
    # Use AST-based safe evaluator -- never raw eval()
    ...
```

### Pattern 5: Graph Validation at Design Time

**What:** When a process template is saved/validated, run graph analysis: reachability (all activities reachable from START), termination (all paths reach END), no orphan nodes, conditional flows cover all cases.

**When:** Before marking a process template as VALIDATED/ACTIVE.

**Why:** Catching structural errors at design time prevents runtime failures. This is where the visual designer adds significant value -- it can highlight unreachable nodes visually.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Direct State Mutation from API Layer

**What:** API endpoints directly changing workflow or activity states in the database.

**Why bad:** Bypasses the Process Engine's transition logic, skips audit logging, can create inconsistent states (e.g., activity marked complete but next activities not created).

**Instead:** API endpoints should dispatch actions to the Process Engine via Celery tasks. The Process Engine owns all state transitions.

### Anti-Pattern 2: Polling for Inbox Updates

**What:** Frontend polling the inbox API every N seconds to check for new work items.

**Why bad:** Wasteful, introduces latency, doesn't scale with many users.

**Instead:** Use WebSocket (Django Channels) with Redis pub/sub. Process Engine publishes events; connected clients receive instant updates.

### Anti-Pattern 3: Storing Workflow Graph in Application Code

**What:** Hardcoding process definitions (activities, flows, conditions) in Python code rather than the database.

**Why bad:** Defeats the purpose of a workflow engine. Users cannot create or modify processes without developer involvement.

**Instead:** All process definitions live in the database, created through the visual designer. The engine interprets them at runtime.

### Anti-Pattern 4: Single-Threaded Workflow Agent

**What:** Running auto activities sequentially in one thread/process.

**Why bad:** One slow or stuck auto activity blocks all others. A failing method with a long timeout can halt the entire system.

**Instead:** Each auto activity executes as a separate Celery task with its own timeout. The Workflow Agent is a Celery beat scheduler that dispatches tasks, not a single-threaded loop.

### Anti-Pattern 5: Mutable Audit Records

**What:** UPDATE or DELETE operations on the audit table.

**Why bad:** Destroys the compliance value of the audit trail.

**Instead:** Audit table is INSERT-only. Use a database constraint or separate write-only connection if extra protection is desired.

## Scalability Considerations

| Concern | At 1-10 users (target) | At 100 users | At 1000 users |
|---------|------------------------|--------------|---------------|
| **Web server** | Single Django process (runserver or gunicorn with 2 workers) | Gunicorn with 4-8 workers behind nginx | Multiple gunicorn instances, load balancer |
| **Background workers** | 1 Celery worker, 1 beat scheduler | 2-4 Celery workers with concurrency | Dedicated worker pool per task type |
| **Database** | Single PostgreSQL instance | Same, add connection pooling (pgbouncer) | Read replicas for dashboards/inbox |
| **WebSocket** | Django Channels with in-memory or Redis | Redis channel layer | Redis cluster channel layer |
| **File storage** | Local filesystem | Local filesystem with backups | S3-compatible object storage |
| **Inbox queries** | Simple queries, no optimization needed | Indexes on (assigned_to, state) | Materialized view for inbox counts |

For this project's scope (internal/personal use), the "1-10 users" column is the target. The architecture supports growth without redesign, but do not over-engineer for scale that will never materialize.

## Suggested Build Order (Dependencies)

The architecture dictates a specific build order because components have hard dependencies on each other.

```
Phase 1: Foundation
  Data models (Process, Activity, Flow, Workflow, WorkItem, Document)
  Basic Django project structure + REST API skeleton
  User/Group/Auth models
  --> Everything else depends on this

Phase 2: Process Definition + Document Management
  Process template CRUD API (no visual designer yet -- API/admin only)
  Document upload + versioning service
  Package attachment to processes
  --> Needed before you can run any workflow

Phase 3: Process Engine Core
  State machine (workflow lifecycle)
  Activity advancement logic
  Manual work item creation
  Basic performer resolution (specific user, group)
  Trigger condition evaluation (AND/OR joins)
  --> This is the heart; must work before adding UI

Phase 4: User-Facing Features
  User inbox API + UI
  Work item completion flow
  Delegation + work queues
  Conditional routing with process variables
  --> Requires working Process Engine

Phase 5: Visual Workflow Designer
  React Flow-based drag-and-drop designer
  Graph validation
  Save/load process templates
  --> Requires Process Definition API from Phase 2

Phase 6: Workflow Agent + Auto Activities
  Method registration and execution
  Celery beat scheduling
  Timeout and retry logic
  --> Requires Process Engine from Phase 3

Phase 7: Advanced Features
  Reject flows
  Alias sets
  Lifecycle integration (document state transitions)
  ACL changes at workflow steps
  --> Requires all core components

Phase 8: BAM Dashboards + Audit
  Audit trail queries and UI
  Real-time metrics (WebSocket)
  SLA monitoring
  Bottleneck detection
  --> Requires running workflows generating data
```

**Build order rationale:** Each phase produces a testable, working subset. Phase 3 (Process Engine) is the riskiest and most complex -- it should be tackled early before building UI on top of it. The visual designer (Phase 5) is high-effort but not a dependency for other components, so it can be developed in parallel with Phases 4-6.

## Technology Mapping to Architecture

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| REST API | Django + Django REST Framework | Mature ORM for complex relational model, admin panel for debugging |
| Background workers | Celery + Redis | Standard Python task queue, supports beat scheduling for Workflow Agent |
| WebSocket | Django Channels + Redis | Native Django integration for real-time inbox/dashboard |
| Database | PostgreSQL | JSONB for process variables, strong transaction support, mature |
| Visual Designer | React + React Flow | Purpose-built for node/edge graph UIs, large ecosystem |
| File Storage | Local filesystem (Django FileField) | Simplest for internal use; abstraction allows future S3 migration |

## Sources

- [Workflow Engine Design Principles - Temporal](https://temporal.io/blog/workflow-engine-principles) -- Core architectural principles for state management and task queues
- [Designing a Workflow Engine Database](https://exceptionnotfound.net/designing-a-workflow-engine-database-part-1-introduction-and-purpose/) -- Database schema patterns for workflow engines
- [Database Design for Workflow Management Systems - GeeksforGeeks](https://www.geeksforgeeks.org/dbms/database-design-for-workflow-management-systems/) -- Entity design patterns
- [SpiffWorkflow - Python BPMN Engine](https://spiffworkflow.readthedocs.io/en/latest/bpmn/index.html) -- Reference Python workflow engine architecture
- [Documentum Workflow Architecture - CrazyApple](https://www.crazyapple.com/content-management-foundations/workflow/) -- Documentum-specific workflow architecture
- [Process Engine details - dm_misc](https://msroth.wordpress.com/tag/process-engine/) -- Process Engine and Workflow Agent interaction patterns
- [Event-Driven Workflow Pattern](https://dev.to/cadienvan/using-the-workflow-pattern-for-efficient-event-driven-workflows-20ce) -- Event-driven architecture for workflow systems
- [Workflow Engine Database Schema](https://budibase.com/blog/data/workflow-management-database-design/) -- Schema design for work items and task management
