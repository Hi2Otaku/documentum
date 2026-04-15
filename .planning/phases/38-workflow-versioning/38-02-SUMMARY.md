---
phase: 38-workflow-versioning
plan: 02
subsystem: frontend
tags: [react, typescript, workflow-versioning, template-version-ui]

# Dependency graph
requires:
  - phase: 38-workflow-versioning
    plan: 01
    provides: template_version field in admin API response, /versions endpoint
provides:
  - Version column in workflow operations table
  - Version badge in designer toolbar
  - Version badge on template list cards
affects:
  - frontend/src/components/workflows/WorkflowTable.tsx
  - frontend/src/pages/DesignerPage.tsx
  - frontend/src/components/designer/Toolbar.tsx
  - frontend/src/pages/TemplateListPage.tsx

# Tech stack
added: []
patterns:
  - tanstack-react-table column accessor for version display
  - shadcn Badge variant="outline" for version indicators

# Key files
created: []
modified:
  - frontend/src/types/workflow.ts
  - frontend/src/api/workflows.ts
  - frontend/src/api/templates.ts
  - frontend/src/components/workflows/WorkflowTable.tsx
  - frontend/src/pages/DesignerPage.tsx
  - frontend/src/components/designer/Toolbar.tsx
  - frontend/src/pages/TemplateListPage.tsx

# Decisions
decisions:
  - Version badge placed in Toolbar component (passed as prop from DesignerPage) for consistent visibility
  - Version column uses narrow 70px width to minimize table space impact

# Metrics
duration: 1.3min
completed: "2026-04-15T05:58:30Z"
tasks_completed: 2
tasks_total: 2
files_modified: 7
---

# Phase 38 Plan 02: Frontend Version Display Summary

Surface template version information across the frontend UI so admins can see which version each workflow uses.

## One-liner

Template version badges and columns added to workflow table, designer toolbar, and template list cards.

## What was done

### Task 1: Add version types and API calls (cfa2311)

- Added `template_family_id: string | null` to `ProcessTemplate` interface in `workflow.ts`
- Added `template_version: number | null` to `WorkflowAdminListResponse` interface in `workflows.ts`
- Added `fetchTemplateVersions()` API function in `templates.ts` for the `/api/templates/{id}/versions` endpoint

### Task 2: Show version info in workflow table, designer, and template list (548f630)

- Added "Version" column to the workflow operations tanstack table, displaying `v{N}` for admin rows
- Passed `templateVersion` prop to Toolbar component and added a version badge (`v{N}`) next to the template name in the designer toolbar
- Added `Badge variant="outline"` showing `v{N}` on each template card in the template list page

## Deviations from Plan

None - plan executed exactly as written.

## Verification

1. WorkflowTable renders a "Version" column showing template_version -- confirmed via grep
2. DesignerPage passes template.version to Toolbar which displays version badge -- confirmed via grep
3. TemplateListPage cards show Badge with version number -- confirmed via grep
4. Types are consistent with backend response shapes from 38-01 -- verified field names match

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | cfa2311 | feat(38-02): add version types and API calls for template versioning |
| 2 | 548f630 | feat(38-02): show version info in workflow table, designer, and template list |

## Self-Check: PASSED

All 7 modified files exist. Both commit hashes (cfa2311, 548f630) verified in git log.
