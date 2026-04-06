/** Notifications API client -- consumes /api/v1/notifications endpoints. */
import { handle401 } from "./handle401";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

async function apiMutate<T>(
  url: string,
  method: "POST" | "PUT" | "PATCH",
): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// --- Response types ---

export interface NotificationResponse {
  id: string;
  user_id: string;
  title: string;
  message: string | null;
  notification_type: string;
  is_read: boolean;
  entity_type: string | null;
  entity_id: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

// --- API functions ---

export async function fetchNotifications(
  page: number = 1,
  pageSize: number = 20,
  isRead?: boolean,
): Promise<NotificationListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (isRead !== undefined) {
    params.set("is_read", String(isRead));
  }
  return apiFetch<NotificationListResponse>(
    `/api/v1/notifications/?${params}`,
  );
}

export async function fetchUnreadCount(): Promise<UnreadCountResponse> {
  return apiFetch<UnreadCountResponse>(
    "/api/v1/notifications/unread-count",
  );
}

export async function markNotificationRead(
  id: string,
): Promise<{ ok: boolean }> {
  return apiMutate<{ ok: boolean }>(
    `/api/v1/notifications/${id}/read`,
    "PATCH",
  );
}

export async function markAllNotificationsRead(): Promise<{
  ok: boolean;
  updated_count: number;
}> {
  return apiMutate<{ ok: boolean; updated_count: number }>(
    "/api/v1/notifications/read-all",
    "PATCH",
  );
}
