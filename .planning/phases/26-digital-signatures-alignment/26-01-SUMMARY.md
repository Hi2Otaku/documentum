---
phase: 26-digital-signatures-alignment
plan: 01
subsystem: digital-signatures
tags: [testing, api-alignment, bug-fix]
dependency_graph:
  requires: []
  provides: [corrected-signature-tests]
  affects: [tests/test_signatures.py]
tech_stack:
  added: []
  patterns: []
key_files:
  modified:
    - tests/test_signatures.py
decisions:
  - "Use non-empty string assertion for algorithm field rather than comparing to specific value, since algorithm string depends on signing implementation"
metrics:
  duration: 1m
  completed: "2026-04-07T03:06:05Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 26 Plan 01: Fix Signature Test Endpoints Summary

Fix all test endpoint paths, HTTP methods, and field assertions in test_signatures.py to match actual router and schema definitions -- correcting draft API contract divergence.

## What Was Done

### Task 1: Fix sign endpoint path and field assertions
- Changed `_sign_version` helper path from `/versions/{version_id}/sign` to `/versions/{version_id}/signatures`
- Applied same fix in `test_sign_with_invalid_key_or_cert`
- Changed `data["document_version_id"]` to `data["version_id"]` (matching SignatureResponse schema)
- Changed `data["digest_algorithm"] == "sha256"` to `assert data["algorithm"]` (non-empty check, matching schema field name)
- Commit: `20e43dd`

### Task 2: Fix verify endpoint path and HTTP method
- Changed `client.post` to `client.get` for both verify tests (matching router GET definition)
- Changed flat path `/documents/signatures/{sig_id}/verify` to nested `/documents/{doc_id}/versions/{version_id}/signatures/{sig_id}/verify`
- Added document upload + version fetch in `test_verify_nonexistent_signature` so valid doc_id/version_id are available for full path
- Commit: `5c28cb1`

## Verification Results

- All 12 tests collected by pytest without errors
- No test references `/sign` endpoint (old path removed)
- No test references `/documents/signatures/{id}/verify` (old flat path removed)
- No test asserts `document_version_id` or `digest_algorithm` (old field names removed)
- All verify tests use GET method (not POST)
- All endpoint paths match `src/app/routers/signatures.py` definitions

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- no stubs introduced or present in modified file.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | `20e43dd` | fix(26-01): correct sign endpoint paths and field assertions in tests |
| 2 | `5c28cb1` | fix(26-01): correct verify endpoint to use GET with full nested path |
