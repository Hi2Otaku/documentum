# Phase 42: System Monitoring & Health - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous YOLO mode)

<domain>
## Phase Boundary

Admin health dashboard showing DB, Redis, Celery, MinIO status. Queue depths, task counts, worker utilization. Prometheus /metrics endpoint. Alerting when health checks fail.

Requirements: MON-01, MON-02, MON-03, MON-04

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Use psutil for system metrics, prometheus-client for /metrics endpoint
- Health check service: ping PostgreSQL, Redis, MinIO, inspect Celery workers
- Celery inspection API for queue depths, active tasks, worker status
- Prometheus metrics: request latency histogram, active workflows gauge, document count, queue depth
- Admin dashboard page with status cards (green/yellow/red), metrics charts
- Alert model: threshold rules (e.g., queue_depth > 100), check via Celery Beat, create in-app notification
- GET /api/v1/monitoring/health, GET /api/v1/monitoring/metrics, GET /metrics (Prometheus)

</decisions>

<code_context>
## Existing Code Insights

- Existing dashboard_service.py for BAM metrics
- SSE notifications already working
- Celery Beat for periodic tasks

</code_context>

<specifics>
None.
</specifics>

<deferred>
None.
</deferred>
