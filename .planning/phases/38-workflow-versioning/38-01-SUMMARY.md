---
phase: 38-workflow-versioning
plan: 01
subsystem: api
tags: [sqlalchemy, alembic, fastapi, workflow-versioning, template-family]

# Dependency graph
requires:
  - phase: 37-workflow-error-handling-compensation
    provides: error handler columns on activity_templates (phase37_001 migration)
provides:
  - template_family_id column on process_templates with migration and backfill
  - Family-based install logic preserving old versions with running instances
  - Latest-version resolution in start_workflow by family
  - Template version history endpoint GET /templates/{id}/versions
  - template_version field on admin workflow list API
affects: [38-workflow-versioning-plan-02, workflow-designer-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns: [template-family-based versioning, running-instance-aware deprecation]

key-files:
  created:
    - alembic/versions/phase38_001_template_family.py
  modified:
    - src/app/models/workflow.py
    - src/app/schemas/template.py
    - src/app/schemas/workflow.py
    - src/app/services/template_service.py
    - src/app/services/engine_service.py
    - src/app/services/workflow_mgmt_service.py
    - src/app/routers/templates.py

key-decisions:
  - "Family-based deprecation checks for running instances (RUNNING, HALTED, DORMANT) before uninstalling old version"
  - "start_workflow resolves to latest installed version in family when requested template is not installed"

patterns-established:
  - "Template family pattern: new templates self-reference as family root, versions inherit family id"

requirements-completed: [WFVER-01, WFVER-02, WFVER-03]

# Metrics
duration: 3min
completed: 2026-04-15
---

# Phase 38 Plan 01: Workflow Template Versioning Summary

**template_family_id column with concurrent versioning: family-based install keeps old versions for running instances, start_workflow resolves latest installed by family**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-15T05:53:00Z
- **Completed:** 2026-04-15T05:56:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Added template_family_id to ProcessTemplate with migration, backfill, and composite index
- Updated install_template to use family-based deprecation that preserves old versions with active instances
- Updated start_workflow to resolve to latest installed version by template family
- Added GET /templates/{id}/versions endpoint for version history
- Surfaced template_version on admin workflow list API

## Task Commits

Each task was committed atomically:

1. **Task 1: DB migration + model update for template_family_id** - `0ba9993` (feat)
2. **Task 2: Update services for family-based versioning + version info on admin API** - `7f79097` (feat)

## Files Created/Modified
- `alembic/versions/phase38_001_template_family.py` - Migration adding template_family_id with backfill and index
- `src/app/models/workflow.py` - ProcessTemplate.template_family_id field
- `src/app/schemas/template.py` - ProcessTemplateResponse.template_family_id field
- `src/app/schemas/workflow.py` - WorkflowAdminListResponse.template_version field
- `src/app/services/template_service.py` - Family-based install, create_template sets family root, create_new_version copies family, list_template_versions
- `src/app/services/engine_service.py` - start_workflow resolves latest installed by family
- `src/app/services/workflow_mgmt_service.py` - list_workflows_filtered includes template_version
- `src/app/routers/templates.py` - GET /templates/{id}/versions endpoint, template_family_id in detail response

## Decisions Made
- Family-based deprecation checks for running instances (RUNNING, HALTED, DORMANT) before uninstalling old version -- ensures in-flight workflows are not disrupted
- start_workflow resolves to latest installed version in family when requested template is not installed -- enables transparent version upgrades for new instances

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Template versioning backend complete, ready for Plan 02 (frontend/UI integration)
- All five must_have truths satisfied: concurrent versions, latest-version resolution, immutable references, admin version display, version history endpoint

---
*Phase: 38-workflow-versioning*
*Completed: 2026-04-15*
