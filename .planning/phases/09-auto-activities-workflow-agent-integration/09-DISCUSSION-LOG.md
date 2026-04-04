# Phase 9: Auto Activities, Workflow Agent & Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 09-auto-activities-workflow-agent-integration
**Areas discussed:** Auto activity method registry, Workflow Agent execution model, Admin failure management, External API integration scope

---

## Auto Activity Method Registry

### How should auto activity methods be registered?

| Option | Description | Selected |
|--------|-------------|----------|
| Decorator-based registry | @auto_method('name') decorator, auto-discovered at startup | ✓ |
| Config file mapping | YAML/JSON maps names to import paths | |
| You decide | Claude picks | |

**User's choice:** Decorator-based registry

### Which built-in auto methods should ship?

| Option | Description | Selected |
|--------|-------------|----------|
| send_email | Send notification email | ✓ |
| change_lifecycle_state | Transition document lifecycle | ✓ |
| modify_acl | Add/remove ACL entries | ✓ |
| call_external_api | HTTP request to external URL | ✓ |

**User's choice:** All four methods

---

## Workflow Agent Execution Model

### How should the Workflow Agent poll?

| Option | Description | Selected |
|--------|-------------|----------|
| Celery beat periodic task | Scan every 10s, dispatch as Celery tasks | ✓ |
| Event-driven via Redis pub/sub | Engine publishes event, worker subscribes | |
| You decide | Claude picks | |

**User's choice:** Celery beat periodic task

### What happens on timeout?

| Option | Description | Selected |
|--------|-------------|----------|
| Configurable timeout with auto-retry | 60s default, 3 retries, exponential backoff | ✓ |
| Fail immediately, no retry | Any failure = FAILED instantly | |
| You decide | Claude picks | |

**User's choice:** Configurable timeout with auto-retry

---

## Admin Failure Management

### How should admins manage failed activities?

| Option | Description | Selected |
|--------|-------------|----------|
| API endpoints only | POST retry and skip endpoints, no UI | ✓ |
| API + simple admin page | Endpoints plus a /admin page | |
| You decide | Claude picks | |

**User's choice:** API endpoints only

---

## External API Integration Scope

### What's needed for INTG-01/02/03?

| Option | Description | Selected |
|--------|-------------|----------|
| Document existing + webhook auto method | INTG-02/03 already exist, add call_external_api method | ✓ |
| Add dedicated integration endpoints | New /api/v1/integration/ namespace | |
| You decide | Claude picks | |

**User's choice:** Document existing + add webhook auto method

---

## Claude's Discretion

- Celery task configuration (queues, prefetch, acks_late)
- ActivityContext implementation details
- Email configuration approach
- Execution log table schema
- Auto method module organization
- Duplicate execution prevention

## Deferred Ideas

None — discussion stayed within phase scope.
