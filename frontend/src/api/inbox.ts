/** Inbox API client — consumes /api/v1/inbox endpoints. */
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

export interface ActivitySummary {
  name: string;
  activity_type: string;
  instructions: string | null;
}

export interface WorkflowSummary {
  id: string;
  template_name: string;
  state: string;
}

export interface DocumentSummary {
  document_id: string | null;
  package_name: string | null;
  title: string | null;
  filename: string | null;
}

export interface CommentResponse {
  id: string;
  user_id: string;
  content: string;
  created_at: string;
}

export interface InboxItemResponse {
  id: string;
  state: string;
  priority: number;
  due_date: string | null;
  instructions: string | null;
  performer_id: string | null;
  created_at: string;
  completed_at: string | null;
  activity: ActivitySummary;
  workflow: WorkflowSummary;
  documents: DocumentSummary[];
  comment_count: number;
}

export interface InboxItemDetailResponse extends InboxItemResponse {
  comments: CommentResponse[];
}

export interface AcquireResponse {
  id: string;
  state: string;
  performer_id: string | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export interface PaginatedInboxResponse {
  data: InboxItemResponse[];
  meta: PaginationMeta;
}

export interface InboxListParams {
  skip?: number;
  limit?: number;
  state?: string;
  priority?: number;
  template_name?: string;
  sort_by?: string;
  sort_order?: string;
}

// --- API functions ---

export async function fetchInboxItems(
  params: InboxListParams,
): Promise<PaginatedInboxResponse> {
  const url = buildUrl("/api/v1/inbox", params as Record<string, string | number | undefined | null>);
  return apiFetch<PaginatedInboxResponse>(url);
}

export async function fetchInboxItem(
  id: string,
): Promise<InboxItemDetailResponse> {
  const res = await apiFetch<{ data: InboxItemDetailResponse }>(
    `/api/v1/inbox/${id}`,
  );
  return res.data;
}

export async function acquireWorkItem(id: string): Promise<AcquireResponse> {
  const res = await apiMutate<{ data: AcquireResponse }>(
    `/api/v1/inbox/${id}/acquire`,
    "POST",
  );
  return res.data;
}

export async function completeWorkItem(
  id: string,
  body: {
    output_variables?: Record<string, unknown>;
    selected_path?: string | null;
    next_performer_id?: string | null;
  },
): Promise<AcquireResponse> {
  const res = await apiMutate<{ data: AcquireResponse }>(
    `/api/v1/inbox/${id}/complete`,
    "POST",
    body,
  );
  return res.data;
}

export async function rejectWorkItem(
  id: string,
  reason: string,
): Promise<AcquireResponse> {
  const res = await apiMutate<{ data: AcquireResponse }>(
    `/api/v1/inbox/${id}/reject`,
    "POST",
    { reason },
  );
  return res.data;
}

export async function fetchComments(
  workItemId: string,
): Promise<CommentResponse[]> {
  const res = await apiFetch<{ data: CommentResponse[] }>(
    `/api/v1/inbox/${workItemId}/comments`,
  );
  return res.data;
}

export async function addComment(
  workItemId: string,
  content: string,
): Promise<CommentResponse> {
  const res = await apiMutate<{ data: CommentResponse }>(
    `/api/v1/inbox/${workItemId}/comments`,
    "POST",
    { content },
  );
  return res.data;
}
