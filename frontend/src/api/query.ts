/** Query API client — consumes /api/v1/query endpoints from Plan 02. */

// --- Response types ---

export interface WorkflowQueryResponse {
  id: string;
  template_name: string;
  template_version: number;
  state: string;
  started_by: string | null;
  started_at: string | null;
  completed_at: string | null;
  active_activity: string | null;
}

export interface WorkItemQueryResponse {
  id: string;
  activity_name: string;
  workflow_name: string;
  workflow_id: string;
  assignee: string | null;
  state: string;
  priority: number;
  created_at: string;
}

export interface DocumentQueryResponse {
  id: string;
  title: string;
  lifecycle_state: string | null;
  current_version: string;
  author: string | null;
  created_by: string | null;
  updated_at: string;
  content_type: string;
}

export interface PaginationMeta {
  total: number;
  skip: number;
  limit: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

// --- Auth helpers (mirrors templates.ts) ---

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
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// --- Param builder ---

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

// --- Query functions ---

export interface WorkflowQueryParams {
  template_id?: string;
  state?: string;
  date_from?: string;
  date_to?: string;
  started_by?: string;
  skip?: number;
  limit?: number;
}

export async function queryWorkflows(
  params: WorkflowQueryParams,
): Promise<PaginatedResponse<WorkflowQueryResponse>> {
  const url = buildUrl("/api/v1/query/workflows", params);
  return apiFetch<PaginatedResponse<WorkflowQueryResponse>>(url);
}

export interface WorkItemQueryParams {
  assignee_id?: string;
  state?: string;
  workflow_id?: string;
  priority?: number;
  skip?: number;
  limit?: number;
}

export async function queryWorkItems(
  params: WorkItemQueryParams,
): Promise<PaginatedResponse<WorkItemQueryResponse>> {
  const url = buildUrl("/api/v1/query/work-items", {
    ...params,
    priority: params.priority,
  });
  return apiFetch<PaginatedResponse<WorkItemQueryResponse>>(url);
}

export interface DocumentQueryParams {
  lifecycle_state?: string;
  metadata_key?: string;
  metadata_value?: string;
  version?: string;
  skip?: number;
  limit?: number;
}

export async function queryDocuments(
  params: DocumentQueryParams,
): Promise<PaginatedResponse<DocumentQueryResponse>> {
  const url = buildUrl("/api/v1/query/documents", params);
  return apiFetch<PaginatedResponse<DocumentQueryResponse>>(url);
}

// --- Utility: fetch templates and users for filter dropdowns ---

export interface TemplateSummary {
  id: string;
  name: string;
}

export interface UserSummary {
  id: string;
  username: string;
}

export async function fetchTemplatesForFilter(): Promise<TemplateSummary[]> {
  const res = await apiFetch<{ data: TemplateSummary[] }>("/api/v1/templates/");
  return res.data;
}

export async function fetchUsersForFilter(): Promise<UserSummary[]> {
  const res = await apiFetch<{ data: UserSummary[] }>("/api/v1/users/");
  return res.data;
}

// --- Badge color helper ---

export function getStateBadgeClass(state: string): string {
  const map: Record<string, string> = {
    running: "bg-green-100 text-green-700",
    halted: "bg-amber-100 text-amber-700",
    finished: "bg-blue-100 text-blue-700",
    failed: "bg-red-100 text-red-700",
    dormant: "bg-secondary text-secondary-foreground",
    available: "bg-green-100 text-green-700",
    acquired: "bg-blue-100 text-blue-700",
    complete: "bg-gray-100 text-gray-700",
    completed: "bg-gray-100 text-gray-700",
    rejected: "bg-red-100 text-red-700",
    suspended: "bg-amber-100 text-amber-700",
    draft: "bg-gray-100 text-gray-700",
    review: "bg-amber-100 text-amber-700",
    approved: "bg-green-100 text-green-700",
    archived: "bg-blue-100 text-blue-700",
  };
  return map[state.toLowerCase()] || "bg-secondary text-secondary-foreground";
}
