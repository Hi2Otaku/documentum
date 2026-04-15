/** Bulk operations API client — consumes /api/v1/bulk endpoints. */
import { handle401 } from "./handle401";

const API = "/api/v1/bulk";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// --- Response types ---

export interface BulkJobResult {
  document_id: string;
  status: string;
  error?: string;
}

export interface BulkJobResponse {
  id: string;
  job_type: string;
  status: string;
  total_count: number;
  success_count: number;
  failure_count: number;
  results: BulkJobResult[] | null;
  created_by: string;
  created_at: string;
  completed_at: string | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface BulkJobsListResponse {
  data: BulkJobResponse[];
  meta: PaginationMeta;
}

// --- Query key factory ---

export const bulkKeys = {
  all: ["bulk-jobs"] as const,
  list: (page: number) => [...bulkKeys.all, "list", page] as const,
  detail: (id: string) => [...bulkKeys.all, "detail", id] as const,
};

// --- Helpers ---

async function apiPost<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(body),
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
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
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// --- API functions ---

export async function bulkUpdate(
  documentIds: string[],
  metadata: Record<string, unknown>,
): Promise<BulkJobResponse> {
  const res = await apiPost<{ data: BulkJobResponse }>(`${API}/update`, {
    document_ids: documentIds,
    metadata,
  });
  return res.data;
}

export async function bulkDelete(
  documentIds: string[],
): Promise<BulkJobResponse> {
  const res = await apiPost<{ data: BulkJobResponse }>(`${API}/delete`, {
    document_ids: documentIds,
  });
  return res.data;
}

export async function bulkLifecycle(
  documentIds: string[],
  targetState: string,
): Promise<BulkJobResponse> {
  const res = await apiPost<{ data: BulkJobResponse }>(`${API}/lifecycle`, {
    document_ids: documentIds,
    target_state: targetState,
  });
  return res.data;
}

export async function fetchBulkJobs(
  page = 1,
  pageSize = 20,
): Promise<BulkJobsListResponse> {
  return apiFetch<BulkJobsListResponse>(
    `${API}/jobs?page=${page}&page_size=${pageSize}`,
  );
}

export async function fetchBulkJob(
  jobId: string,
): Promise<BulkJobResponse> {
  const res = await apiFetch<{ data: BulkJobResponse }>(`${API}/jobs/${jobId}`);
  return res.data;
}
