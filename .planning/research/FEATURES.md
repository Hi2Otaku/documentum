# Feature Landscape

**Domain:** Documentum Workflow Clone v1.2 -- Advanced Engine & Document Platform
**Researched:** 2026-04-06

## Table Stakes

Features that close the gap with Documentum's specification. Missing = incomplete Documentum clone.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Timer/deadline activities | Documentum has timer events and SLA tracking. Every BPM engine supports deadlines. | Medium | Leverage existing WorkItem.due_date and Celery Beat |
| Escalation on overdue | Documentum auto-escalates overdue tasks. Expected in any workflow engine. | Medium | Reassign, notify, or bump priority when deadline passes |
| Sub-workflow spawning | Documentum dm_process supports sub-processes. Essential for complex workflows. | High | Parent-child lifecycle, variable passing, depth limits |
| Email notifications | Documentum sends email on task assignment. Users expect email alerts. | Medium | Existing SMTP config + send_email auto method as foundation |
| In-app notifications | Modern web apps show notification badges. Users check inbox but expect alerts. | Medium | New model + router + frontend notification bell |

## Differentiators

Features that go beyond basic Documentum replication. Not strictly expected, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Event-driven activities | Activities triggered by document/system events. More flexible than polling. | High | Redis pub/sub event bus, webhook endpoint for external events |
| Document renditions | Auto-generate PDF/thumbnails. Eliminates manual conversion. | Medium | LibreOffice headless + Celery workers. New Docker deps. |
| Virtual/compound documents | Assemble multi-document packages with ordering. | Medium | Metadata-only feature with optional PDF assembly |
| Retention policies | Enforce document preservation and automated disposition. | Medium | Policy engine with legal hold support |
| Digital signatures | Cryptographic non-repudiation on documents and approvals. | High | PKCS7/CMS signing, certificate management, verification |
| Notification preferences | Per-user opt-in/out by type and channel. | Low | Preference model, check before dispatching |
| Webhook-triggered activities | External systems fire workflow events via REST. | Low | Simple authenticated endpoint that emits to event bus |

## Anti-Features

Features to explicitly NOT build in v1.2.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time collaborative editing | Massive complexity (OT/CRDT), out of scope for workflow engine | Document check-in/check-out already prevents conflicts |
| Calendar/scheduling UI for timers | UI complexity with little value -- timers are configured in template designer | Configure timer durations in ActivityTemplate properties panel |
| Full PKI/CA infrastructure | Way beyond scope for internal tool | Self-signed certs stored in DB. Add CA support later if needed. |
| Email-based workflow actions | Replying to email to approve/reject | Web UI is the interaction point. Not worth the parsing complexity. |
| Multi-tenant isolation | Internal/personal use. Adds complexity everywhere. | Single-tenant. Add later if product pivots. |
| Rendition preview editing | Editing rendered PDFs in-browser | View-only. Editing happens on source document. |
| Complex retention schedule builder UI | Retention policies are admin-configured, rarely changed | Simple form for policy creation. No visual schedule builder. |

## Feature Dependencies

```
Event Bus -------> Event-Driven Activities
    |
    +-----------> Notifications (consume events)
    |
    +-----------> Timer Escalation (emit deadline events)

Timer Config ----> Timer Activities (deadlines on work items)
    |
    +-----------> Escalation (triggered when deadline passes)
    |
    +-----------> Notifications (deadline approaching alerts)

Renditions ------> Virtual Document Assembly (merge PDFs)

Stable Document Model --> Digital Signatures (sign specific versions)
                     +--> Retention Policies (hold specific documents)

Sub-Workflows: Independent but benefits from stable engine (validated by timer/event phases)
```

## MVP Recommendation per Feature

### Timer Activities
Prioritize:
1. Deadline configuration on ActivityTemplate (duration-based)
2. Celery Beat polling for overdue work items
3. Priority bump escalation action

Defer: Recurring timers, expression-based deadline calculation, multi-level escalation chains

### Sub-Workflows
Prioritize:
1. Spawn child workflow from SUB_WORKFLOW activity
2. Wait for child completion, then advance parent
3. Input variable mapping (parent -> child)

Defer: Output variable mapping (child -> parent), partial completion (wait for any-of-N children), parallel sub-workflows from single activity

### Event-Driven Activities
Prioritize:
1. Event bus (emit + subscribe)
2. document.uploaded and lifecycle.changed event types
3. EVENT activity type that completes on matching event

Defer: Complex filter expressions on event payloads, event replay, external webhook authentication

### Notifications
Prioritize:
1. In-app notification model + REST API
2. Task assignment notifications
3. Frontend notification bell with unread count

Defer: Email notifications (can use existing send_email auto method initially), notification preferences, push notifications

### Document Renditions
Prioritize:
1. PDF rendition generation via LibreOffice headless
2. Auto-trigger on document upload
3. REST endpoint to download renditions

Defer: Thumbnail generation, rendition for image formats, custom rendition profiles

### Virtual Documents
Prioritize:
1. VirtualDocumentNode model (parent-child relationships)
2. Add/remove/reorder children
3. Resolve tree with cycle detection

Defer: PDF assembly, nested virtual documents (depth > 1), late-bound version resolution

### Retention Policies
Prioritize:
1. RetentionPolicy and RetentionAssignment models
2. Block deletion of documents under retention
3. Legal hold support

Defer: Automated disposition (daily Beat task), retention auto-assignment on lifecycle change, disposition review workflow

### Digital Signatures
Prioritize:
1. Sign a document version (hash + PKCS7 signature)
2. Verify signature endpoint
3. List signatures on a document

Defer: Certificate management UI, sign-on-checkin automation, requires_signature on workflow activities, certificate revocation

## Sources

- OpenText Documentum Workflow Management specification (project reference doc) -- HIGH confidence
- Codebase analysis of existing features and extension points -- HIGH confidence
- BPM/workflow engine feature landscape (Camunda, Flowable, Activiti feature sets) -- MEDIUM confidence
