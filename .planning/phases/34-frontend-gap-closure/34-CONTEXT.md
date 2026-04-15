# Phase 34: Frontend Gap Closure - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous YOLO mode)

<domain>
## Phase Boundary

Wire 6 existing backend features to the web UI and fix the lifecycle state filter bug. All backend APIs already exist and are tested — this phase is purely frontend work connecting React components to existing endpoints.

Features:
1. Digital signatures UI — sign documents, verify signatures, view certificate details
2. Retention & legal hold UI — create/edit/delete policies, assign to documents, place/release holds
3. Document-level ACL UI — add/remove user and group permissions on individual documents
4. Queue administration UI — CRUD for work queues, manage queue membership
5. Document lifecycle state filter fix — pass stateFilter to API call in DocumentsPage
6. Notification preferences UI — configure which event types trigger notifications

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — autonomous mode. Use ROADMAP phase goal, success criteria, and existing codebase conventions to guide decisions. Follow established patterns from existing UI components (shadcn/ui, TanStack Query, React Router).

Key guidance from research:
- All 6 features have working backend APIs — no backend changes needed
- Follow existing component patterns (DocumentDetailPanel, FolderTree, etc.)
- Use shadcn/ui Dialog, Form, Table components consistently
- Use TanStack Query for all API state management
- Digital signatures backend uses RSA/PKCS1v15 with X.509 certificates
- Retention backend has RetentionPolicy CRUD + LegalHold place/release
- ACL backend supports document-level entries alongside folder inheritance
- Queue backend has full CRUD + member management endpoints
- Notification backend has notification type preferences

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- shadcn/ui components (Dialog, Form, Table, Select, Badge, etc.)
- TanStack Query hooks pattern from existing API modules
- Existing API client modules in frontend/src/api/
- DocumentDetailPanel pattern for adding new tabs/sections

### Established Patterns
- API modules: typed fetch functions in frontend/src/api/*.ts
- Query hooks: useQuery/useMutation with TanStack Query
- Forms: shadcn/ui Form + react-hook-form + zod validation
- Admin pages: table + dialog pattern (see DocumentTypesPage, FoldersPage)

### Integration Points
- DocumentDetailPanel — add signature and retention tabs
- DocumentsPage — fix stateFilter parameter in fetchDocuments call
- Admin section — add Queue Management and Notification Preferences pages
- ACL panel — add document-level ACL to document detail view

</code_context>

<specifics>
## Specific Ideas

- Fix the stateFilter bug first — it's literally a 1-line fix (pass lifecycle_state param to API)
- Digital signature UI should show sign button, verification status badge, and certificate details
- Retention UI should be an admin page similar to Document Types admin
- Queue admin should allow creating queues, adding/removing members

</specifics>

<deferred>
## Deferred Ideas

None — all 6 features are in scope for this phase.

</deferred>
