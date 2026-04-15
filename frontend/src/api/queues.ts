/** Queues API client — consumes /api/v1/queues endpoints. */
import { handle401 } from "./handle401";

// --- Auth helpers (mirrors query.ts pattern) ---

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

function buildUrl(
  base: string,
  params: Record<string, string | number | undefined | null>,
): string {
  const url = new URL(base, window.location.origin);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return url.pathname + url.search;
}

// --- Response types ---

export interface WorkQueueResponse {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface QueueMemberResponse {
  id: string;
  username: string;
  email: string | null;
}

export interface WorkQueueDetailResponse extends WorkQueueResponse {
  members: QueueMemberResponse[];
}

// --- Mutation helpers ---

async function apiMutate<T>(
  url: string,
  method: "POST" | "PUT" | "PATCH",
  body?: unknown,
): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function apiDelete(url: string): Promise<void> {
  const res = await fetch(url, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
  });
  if (res.status === 401) handle401();
  if (!res.ok && res.status !== 204) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
}

// --- Create / Update types ---

export interface WorkQueueCreate {
  name: string;
  description?: string;
  is_active?: boolean;
}

export interface WorkQueueUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
}

// --- API functions ---

export async function fetchQueues(
  params?: { skip?: number; limit?: number },
): Promise<{ data: WorkQueueResponse[] }> {
  const url = buildUrl("/api/v1/queues", params ?? {});
  return apiFetch<{ data: WorkQueueResponse[] }>(url);
}

export async function fetchQueueDetail(
  id: string,
): Promise<WorkQueueDetailResponse> {
  const res = await apiFetch<{ data: WorkQueueDetailResponse }>(
    `/api/v1/queues/${id}`,
  );
  return res.data;
}

export async function createQueue(
  data: WorkQueueCreate,
): Promise<WorkQueueResponse> {
  const res = await apiMutate<{ data: WorkQueueResponse }>(
    "/api/v1/queues",
    "POST",
    data,
  );
  return res.data;
}

export async function updateQueue(
  id: string,
  data: WorkQueueUpdate,
): Promise<WorkQueueResponse> {
  const res = await apiMutate<{ data: WorkQueueResponse }>(
    `/api/v1/queues/${id}`,
    "PUT",
    data,
  );
  return res.data;
}

export async function deleteQueue(id: string): Promise<void> {
  await apiDelete(`/api/v1/queues/${id}`);
}

export async function addQueueMember(
  queueId: string,
  userId: string,
): Promise<void> {
  await apiMutate<unknown>(`/api/v1/queues/${queueId}/members`, "POST", {
    user_id: userId,
  });
}

export async function removeQueueMember(
  queueId: string,
  userId: string,
): Promise<void> {
  await apiDelete(`/api/v1/queues/${queueId}/members/${userId}`);
}
