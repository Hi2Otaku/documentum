---
phase: 16-notifications-event-bus
plan: "03"
subsystem: frontend-notifications
tags: [notifications, sse, popover, real-time, sonner]
dependency_graph:
  requires: [16-02]
  provides: [notification-ui, notification-bell, sse-hook]
  affects: [sidebar, user-experience]
tech_stack:
  added: ["@radix-ui/react-popover"]
  patterns: [sse-hook, popover-component, sonner-toast-integration]
key_files:
  created:
    - frontend/src/components/ui/popover.tsx
    - frontend/src/hooks/useNotificationSSE.ts
    - frontend/src/components/notifications/NotificationBell.tsx
    - frontend/src/components/notifications/NotificationPopover.tsx
    - frontend/src/components/notifications/NotificationItem.tsx
  modified:
    - frontend/src/api/notifications.ts
    - frontend/src/components/layout/SidebarUserMenu.tsx
    - frontend/src/components/layout/Sidebar.tsx
  deleted:
    - frontend/src/components/layout/NotificationBell.tsx
decisions:
  - "Replaced DropdownMenu-based NotificationBell with Popover-based version for richer content layout"
  - "SSE hook follows same EventSource pattern as useDashboardSSE for consistency"
  - "Fixed API client HTTP methods from PUT to PATCH to match backend endpoints"
metrics:
  duration: 3m
  completed: "2026-04-06"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 9
requirements: [NOTIF-05, NOTIF-06]
---

# Phase 16 Plan 03: Notification UI (Bell, Popover, SSE, Toast) Summary

Popover-based notification bell with SSE real-time updates and Sonner toast integration in the sidebar user menu area.

## What Was Done

### Task 1: Popover, API Client, SSE Hook, and Notification Components (e129d0e)

- Installed `@radix-ui/react-popover` and created `popover.tsx` UI component following the project's shadcn pattern
- Created `useNotificationSSE` hook mirroring the `useDashboardSSE` pattern: EventSource connection, `unread_count` and `new_notification` event listeners, reconnection handling with 30s disconnect timer
- Created `NotificationItem` component: shows title, truncated message, relative time, blue dot for unread, click-to-mark-read
- Created `NotificationPopover` component: Popover with scrollable notification list (max 20), "Mark all read" button, empty state, TanStack Query integration
- Created `NotificationBell` component: Bell icon with destructive-colored unread badge, wraps popover, fires Sonner toast on new notifications via SSE, deduplicates toasts using ref tracking
- Fixed API client to use `PATCH` method (matching backend `@router.patch`) instead of `PUT`, and corrected endpoint paths to match backend routes

### Task 2: Integrate NotificationBell into SidebarUserMenu (0b10220)

- Added `NotificationBell` import from new `notifications/` directory into `SidebarUserMenu`
- Placed bell before the user dropdown menu, hidden when sidebar is collapsed (`!isCollapsed` guard)
- Added `gap-2` to flex container for proper spacing
- Updated `Sidebar.tsx` to import `NotificationBell` from `notifications/` instead of `layout/`
- Removed old `layout/NotificationBell.tsx` (dead code after migration to `notifications/` directory)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed API client HTTP methods**
- **Found during:** Task 1
- **Issue:** Existing `api/notifications.ts` used `PUT` for mark-read endpoints but backend uses `PATCH`
- **Fix:** Changed both `markNotificationRead` and `markAllNotificationsRead` to use `PATCH` method
- **Files modified:** `frontend/src/api/notifications.ts`
- **Commit:** e129d0e

**2. [Rule 2 - Missing functionality] Removed dead code**
- **Found during:** Task 2
- **Issue:** Old `layout/NotificationBell.tsx` became unused after new `notifications/NotificationBell.tsx` replaced it
- **Fix:** Removed the file and updated `Sidebar.tsx` import to point to new location
- **Files modified:** `frontend/src/components/layout/Sidebar.tsx`, deleted `frontend/src/components/layout/NotificationBell.tsx`
- **Commit:** 0b10220

## Verification

- TypeScript compiles cleanly (`npx tsc --noEmit` passes with no errors)
- All acceptance criteria met for both tasks
- All required exports present in created files

## Known Stubs

None -- all components are fully wired to real API endpoints and SSE stream.

## Self-Check: PASSED

- All 7 created/modified files verified on disk
- Both commit hashes (e129d0e, 0b10220) found in git log
