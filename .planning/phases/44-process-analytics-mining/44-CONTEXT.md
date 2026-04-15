# Phase 44: Process Analytics & Mining - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous YOLO mode)

<domain>
## Phase Boundary

Admin can view process mining dashboard showing actual execution paths from workflow logs. Cycle time analysis per activity and template. Bottleneck identification via frequency and duration analysis. Analytics refresh via background processing.

Requirements: ANLYT-01, ANLYT-02, ANLYT-03, ANLYT-04

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Extract event log from existing AuditLog + ActivityInstance tables (no new data collection needed)
- Build event log in XES-compatible format: case_id (workflow_instance_id), activity (activity_name), timestamp, resource (performer)
- pm4py for process discovery (alpha miner or heuristic miner) — BUT pm4py is heavy (~200MB). Alternative: build lightweight analytics without pm4py using SQL aggregations
- Recommended approach: SQL-based analytics (no new dependency) for cycle time, bottleneck, and frequency analysis. Process path discovery via SQL GROUP BY on activity sequences.
- Celery task refreshes analytics materialized data periodically
- API: GET /api/v1/analytics/paths, GET /api/v1/analytics/cycle-times, GET /api/v1/analytics/bottlenecks
- Frontend: Recharts-based dashboard with path Sankey/flow diagram, cycle time bar charts, bottleneck table
- Use existing Recharts library (already in project)

</decisions>

<code_context>
## Existing Code Insights

- AuditLog model has all workflow events
- ActivityInstance has timestamps, durations, performers
- Recharts already used in BAM dashboard
- Celery Beat for periodic tasks

</code_context>

<specifics>
None.
</specifics>

<deferred>
- pm4py integration (heavy dependency, defer unless SQL approach insufficient)
- Conformance checking (comparing actual vs expected paths)
</deferred>
