---
phase: 34-frontend-gap-closure
plan: "03"
title: "Digital Signatures & Retention UI"
subsystem: frontend-documents
tags: [signatures, retention, legal-hold, document-detail]
dependency_graph:
  requires: ["34-01"]
  provides: ["signature-ui", "retention-status-ui", "legal-hold-ui"]
  affects: ["DocumentDetailPanel"]
tech_stack:
  added: []
  patterns: ["TanStack Query mutations for signature/retention ops", "Dialog-based PEM input for signing"]
key_files:
  created:
    - frontend/src/components/documents/SignaturePanel.tsx
    - frontend/src/components/documents/RetentionStatusPanel.tsx
    - frontend/src/api/retention.ts
  modified:
    - frontend/src/api/documents.ts
    - frontend/src/components/documents/DocumentDetailPanel.tsx
decisions:
  - "Created separate retention.ts API module (Rule 2 - missing API client for retention endpoints)"
  - "Added Sections 10-11 after Relationships (Section 8) since Document ACL section not yet present"
metrics:
  duration: "3min"
  completed: "2026-04-15T04:49:42Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
---

# Phase 34 Plan 03: Digital Signatures & Retention UI Summary

SignaturePanel and RetentionStatusPanel wired into DocumentDetailPanel, connecting existing backend signature/retention/legal-hold APIs to the web UI.

## What Was Done

### Task 1: Signature API functions and SignaturePanel component
- **Commit:** `99f5764`
- Added SignatureResponse, SignatureVerifyResponse, SignDocumentRequest types to documents.ts
- Added fetchSignatures, signDocumentVersion, verifySignature API functions
- Created SignaturePanel with: signature list (signer CN, timestamp, algorithm, validity badge), verify button with inline result display, sign dialog with PEM certificate/key textareas and optional reason

### Task 2: RetentionStatusPanel and DocumentDetailPanel wiring
- **Commit:** `3e622a8`
- Created frontend/src/api/retention.ts with full API client (fetchRetentionStatus, fetchRetentionPolicies, assignRetentionPolicy, removeRetentionAssignment, placeLegalHold, releaseLegalHold)
- Created RetentionStatusPanel with: retained/held status badges, active retentions list with remove, active legal holds list with release, assign policy dialog with policy dropdown, place legal hold dialog with reason textarea
- Wired both panels into DocumentDetailPanel as Sections 10 (Digital Signatures) and 11 (Retention & Legal Holds)
- Added versions query to DocumentDetailPanel to provide latestVersionId to SignaturePanel

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Created retention API module**
- **Found during:** Task 2
- **Issue:** Plan referenced `frontend/src/api/retention.ts` but the file did not exist
- **Fix:** Created full retention API client with all needed functions matching backend endpoints
- **Files created:** frontend/src/api/retention.ts
- **Commit:** `3e622a8`

**2. [Rule 3 - Blocking issue] Document ACL section not present**
- **Found during:** Task 2
- **Issue:** Plan referenced adding after "Document ACL section (Section 9)" but that section does not exist yet (likely from another plan)
- **Fix:** Added Sections 10-11 after Relationships (Section 8) and before FolderPickerDialog
- **Commit:** `3e622a8`

## Verification

- TypeScript compilation passes with no errors
- SignaturePanel displays signature list with signer_cn, signed_at, algorithm, validity badge
- SignaturePanel supports signing with PEM certificate/key via dialog
- SignaturePanel supports signature verification with inline result
- RetentionStatusPanel shows retention status badges and deletion blocked reason
- RetentionStatusPanel supports assigning/removing retention policies
- RetentionStatusPanel supports placing/releasing legal holds

## Self-Check: PASSED
