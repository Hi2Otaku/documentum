/** Workflow API client — consumes /api/v1/workflows endpoints. */

// --- Auth helpers (mirrors documents.ts pattern) ---

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

export interface WorkflowInstanceResponse {
  id: string;
  process_template_id: string;
  state: string;
  started_at: string | null;
  completed_at: string | null;
  supervisor_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowAdminListResponse extends WorkflowInstanceResponse {
  template_name: string | null;
  started_by_username: string | null;
  active_activity_name: string | null;
}

export interface ActivityInstanceResponse {
  id: string;
  workflow_instance_id: string;
  activity_template_id: string;
  state: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ProcessVariableResponse {
  id: string;
  name: string;
  variable_type: string;
  string_value: string | null;
  int_value: number | null;
  bool_value: boolean | null;
  date_value: string | null;
}

export interface WorkItemResponse {
  id: string;
  activity_instance_id: string;
  performer_id: string | null;
  state: string;
  instructions: string | null;
  due_date: string | null;
  priority: number;
  completed_at: string | null;
  created_at: string;
}

export interface WorkflowDetailResponse extends WorkflowInstanceResponse {
  activity_instances: ActivityInstanceResponse[];
  work_items: WorkItemResponse[];
  process_variables: ProcessVariableResponse[];
}

export interface WorkflowActionResponse {
  id: string;
  state: string;
  message: string;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export type PaginatedWorkflowsResponse = {
  data: WorkflowInstanceResponse[];
  meta: PaginationMeta;
};

export type PaginatedAdminWorkflowsResponse = {
  data: WorkflowAdminListResponse[];
  meta: PaginationMeta;
};

export interface WorkflowStartPayload {
  template_id: string;
  document_ids: string[];
  initial_variables: Record<string, unknown>;
}

// --- API functions ---

export async function fetchWorkflows(params: {
  skip: number;
  limit: number;
}): Promise<PaginatedWorkflowsResponse> {
  const url = buildUrl("/api/v1/workflows", {
    skip: params.skip,
    limit: params.limit,
  });
  return apiFetch<PaginatedWorkflowsResponse>(url);
}

export async function fetchWorkflowsAdmin(params: {
  skip: number;
  limit: number;
  state?: string;
  template_id?: string;
  date_from?: string;
  date_to?: string;
}): Promise<PaginatedAdminWorkflowsResponse> {
  const url = buildUrl("/api/v1/workflows/admin/list", {
    skip: params.skip,
    limit: params.limit,
    state: params.state,
    template_id: params.template_id,
    date_from: params.date_from,
    date_to: params.date_to,
  });
  return apiFetch<PaginatedAdminWorkflowsResponse>(url);
}

export async function fetchWorkflowDetail(
  id: string,
): Promise<WorkflowDetailResponse> {
  const res = await apiFetch<{ data: WorkflowDetailResponse }>(
    `/api/v1/workflows/${id}`,
  );
  return res.data;
}

export async function startWorkflow(
  payload: WorkflowStartPayload,
): Promise<WorkflowInstanceResponse> {
  const res = await apiMutate<{ data: WorkflowInstanceResponse }>(
    "/api/v1/workflows",
    "POST",
    payload,
  );
  return res.data;
}

export async function haltWorkflow(
  id: string,
): Promise<WorkflowActionResponse> {
  const res = await apiMutate<{ data: WorkflowActionResponse }>(
    `/api/v1/workflows/${id}/halt`,
    "POST",
  );
  return res.data;
}

export async function resumeWorkflow(
  id: string,
): Promise<WorkflowActionResponse> {
  const res = await apiMutate<{ data: WorkflowActionResponse }>(
    `/api/v1/workflows/${id}/resume`,
    "POST",
  );
  return res.data;
}

export async function terminateWorkflow(
  id: string,
): Promise<WorkflowActionResponse> {
  const res = await apiMutate<{ data: WorkflowActionResponse }>(
    `/api/v1/workflows/${id}/abort`,
    "POST",
  );
  return res.data;
}
