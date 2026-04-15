# Phase 43: CMIS Standard API - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous YOLO mode)

<domain>
## Phase Boundary

Implement OASIS CMIS 1.1 Browser Binding endpoints as a translation layer over existing document/folder services. Support document CRUD, folder/navigation operations, CMIS-QL queries mapped to existing search. Respect ACL enforcement and auth. Verify with CMIS Workbench or LibreOffice.

Requirements: CMIS-01, CMIS-02, CMIS-03, CMIS-04, CMIS-05

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- CMIS Browser Binding is JSON over HTTP — maps well to FastAPI
- Translation layer: cmis_mapper.py maps CMIS property names to internal model fields
- CMIS object types: cmis:document, cmis:folder map to Document, Folder models
- Key CMIS services to implement:
  - Repository service: getRepositoryInfo, getTypeDefinition
  - Navigation: getChildren, getDescendants, getFolderTree, getObjectParents
  - Object: createDocument, getObject, updateProperties, deleteObject, moveObject
  - Versioning: checkOut, checkIn, cancelCheckOut, getAllVersions
  - Discovery: query (CMIS-QL → PostgreSQL FTS/SQL)
- CMIS-QL parser: simple subset — SELECT, FROM, WHERE, ORDER BY, LIKE, IN, AND/OR
- Mount CMIS at /api/cmis/browser (standard CMIS Browser Binding URL pattern)
- Auth: reuse existing auth backend (local JWT, SSO, service tokens)
- No new npm dependencies — CMIS is backend-only

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- src/app/services/document_service.py — document CRUD
- src/app/services/folder_service.py — folder navigation
- src/app/services/search_service.py — full-text search
- src/app/core/auth_backend.py — pluggable auth from Phase 36

</code_context>

<specifics>
None.
</specifics>

<deferred>
- CMIS AtomPub binding (legacy)
- CMIS SOAP binding (legacy)
- Full CMIS TCK compliance (targeting practical subset)
</deferred>
