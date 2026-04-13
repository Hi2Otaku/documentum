# Milestones

## v1.2 Advanced Engine & Document Platform (Shipped: 2026-04-13)

**Phases:** 16–26 (11 phases) | **Plans:** 26 | **Tasks:** 45
**Python:** ~17,400 LOC | **TypeScript:** ~13,800 LOC
**Timeline:** 2026-03-30 → 2026-04-13

**Key accomplishments:**

1. Domain event bus (Redis pub/sub + persistent `events` table) wiring all advanced features together
2. In-app and email notification framework with unread badge, notification list, and mark-read
3. Timer activities with Celery Beat deadline enforcement and configurable escalation actions
4. Sub-workflow spawning — parent pauses, child runs, variables map, depth limit prevents recursion
5. Event-driven activities that auto-complete when domain events match their subscription filter
6. Document renditions — auto PDF and thumbnail generation via LibreOffice headless Celery worker
7. Virtual documents — child assembly, drag-and-drop reordering, cycle detection, merged PDF export
8. Retention policies and legal holds blocking premature deletion of governed documents
9. Digital signatures (PKCS7/CMS) with post-signing version immutability and verification
10. Infrastructure wiring (phases 24–26): linearized Alembic migration chain, all 10 routers mounted, all event handlers registered, all tests passing

**Requirements:** 36/36 satisfied | **Audit:** passed

---
