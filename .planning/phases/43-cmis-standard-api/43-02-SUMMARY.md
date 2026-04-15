---
phase: 43-cmis-standard-api
plan: "02"
subsystem: cmis-query
tags: [cmis, query, cmis-ql, parser, api]
dependency_graph:
  requires: [43-01]
  provides: [cmis-query-endpoint, cmis-ql-parser]
  affects: [cmis-router]
tech_stack:
  added: []
  patterns: [regex-tokenizer, dataclass-ast, cmis-ql-subset]
key_files:
  created:
    - src/app/services/cmis_query_service.py
    - src/tests/test_cmis_query.py
  modified:
    - src/app/routers/cmis.py
decisions:
  - Regex-based tokenizer for CMIS-QL (no parser library dependency)
  - Dataclass-based AST (ParsedQuery, WhereClause, OrderSpec)
  - ilike for LIKE operator (case-insensitive matching)
metrics:
  duration: 4min
  completed: "2026-04-15T07:45:42Z"
  tasks_completed: 2
  tasks_total: 2
  test_count: 31
  files_changed: 3
---

# Phase 43 Plan 02: CMIS-QL Query Support and E2E Smoke Test Summary

Regex-based CMIS-QL parser with SELECT/FROM/WHERE/ORDER BY/LIKE/IN supporting cmis:document and cmis:folder queries, plus comprehensive e2e smoke test validating full CMIS client workflow.

## What Was Built

### CMIS-QL Parser (`cmis_query_service.py`)
- `parse_cmis_query()` tokenizes CMIS-QL into `ParsedQuery` dataclass with select fields, from type, where clauses, and order-by specs
- Supports operators: `=`, `!=`, `<`, `>`, `<=`, `>=`, `LIKE`, `IN`
- Handles AND-joined conditions, string literals, numeric values, and IN lists
- Property mapping from CMIS names (cmis:name, cmis:createdBy, etc.) to SQLAlchemy model columns

### CMIS-QL Executor
- `execute_cmis_query()` builds SQLAlchemy queries from parsed CMIS-QL
- Supports both cmis:document and cmis:folder types
- Field projection (SELECT specific fields filters succinctProperties)
- Pagination via maxItems/skipCount with hasMoreItems tracking
- Results returned in standard CMIS Browser Binding format

### Router Integration
- POST `/api/v1/cmis/browser/root` with `cmisaction=query` and `statement` form param
- GET `/api/v1/cmis/browser` with `cmisselector=query` and `q` query param
- ValueError from parser returns 400 with CMIS `invalidArgument` exception format

### Test Coverage (31 tests)
- 12 parser unit tests (no DB): SELECT, FROM, WHERE, LIKE, IN, ORDER BY, AND, invalid query
- 13 integration tests: execute_cmis_query against SQLite with seeded data
- 5 HTTP endpoint tests: POST query, GET query, WHERE filter, invalid query 400, auth required
- 1 comprehensive e2e test: repo info -> create folder -> create doc -> get object -> get children -> query -> checkOut -> checkIn -> delete

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Regex tokenizer over parser library**: Simple regex-based parsing sufficient for the CMIS-QL subset needed; avoids adding a dependency like pyparsing or lark
2. **Dataclass AST**: ParsedQuery/WhereClause/OrderSpec dataclasses provide clean separation between parsing and execution
3. **Case-insensitive LIKE**: Used `ilike()` for LIKE operator matching CMIS convention of case-insensitive name matching

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `7caa824` | CMIS-QL query parser and executor with TDD tests |
| 2 | `76e1c6c` | Wire CMIS-QL query endpoint and add e2e smoke test |

## Known Stubs

None - all functionality is fully wired and tested.

## Self-Check: PASSED
