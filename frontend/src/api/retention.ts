/** Retention Policies & Legal Holds API client — consumes /api/v1/ endpoints. */
import { handle401 } from "./handle401";

// --- Auth helpers (mirrors documentTypes.ts pattern) ---

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

async function apiDelete(url: string): Promise<void> {
  const res = await fetch(url, {
    method: "DELETE",
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
}

// --- Response types ---

export interface RetentionPolicyResponse {
  id: string;
  name: string;
  description: string | null;
  retention_period_days: number;
  disposition_action: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface RetentionPolicyCreate {
  name: string;
  description?: string;
  retention_period_days: number;
  disposition_action: "archive" | "delete";
}

export interface RetentionPolicyUpdate {
  name?: string;
  description?: string;
  retention_period_days?: number;
  disposition_action?: "archive" | "delete";
}

export interface LegalHoldResponse {
  id: string;
  document_id: string;
  reason: string;
  placed_by: string;
  placed_at: string;
  released_at: string | null;
  created_at: string;
  created_by: string | null;
}

export interface DocumentRetentionResponse {
  id: string;
  document_id: string;
  policy_id: string;
  applied_at: string;
  expires_at: string;
  created_at: string;
  created_by: string | null;
  policy_name: string | null;
}

export interface RetentionStatusResponse {
  document_id: string;
  is_retained: boolean;
  is_held: boolean;
  is_deletable: boolean;
  deletion_blocked_reason: string | null;
  active_retentions: DocumentRetentionResponse[];
  active_holds: LegalHoldResponse[];
}

// --- Retention Policy CRUD ---

export async function fetchRetentionPolicies(
  page?: number,
  pageSize?: number,
): Promise<RetentionPolicyResponse[]> {
  const params = new URLSearchParams();
  if (page !== undefined) params.set("page", String(page));
  if (pageSize !== undefined) params.set("page_size", String(pageSize));
  const qs = params.toString();
  const url = `/api/v1/retention-policies${qs ? `?${qs}` : ""}`;
  const res = await apiFetch<{ data: RetentionPolicyResponse[] }>(url);
  return res.data;
}

export async function createRetentionPolicy(
  data: RetentionPolicyCreate,
): Promise<RetentionPolicyResponse> {
  const res = await apiMutate<{ data: RetentionPolicyResponse }>(
    "/api/v1/retention-policies",
    "POST",
    data,
  );
  return res.data;
}

export async function updateRetentionPolicy(
  id: string,
  data: RetentionPolicyUpdate,
): Promise<RetentionPolicyResponse> {
  const res = await apiMutate<{ data: RetentionPolicyResponse }>(
    `/api/v1/retention-policies/${id}`,
    "PUT",
    data,
  );
  return res.data;
}

export async function deleteRetentionPolicy(id: string): Promise<void> {
  await apiDelete(`/api/v1/retention-policies/${id}`);
}

// --- Document Retention Assignment ---

export async function fetchRetentionStatus(
  documentId: string,
): Promise<RetentionStatusResponse> {
  const res = await apiFetch<{ data: RetentionStatusResponse }>(
    `/api/v1/documents/${documentId}/retention-status`,
  );
  return res.data;
}

export async function assignRetentionPolicy(
  documentId: string,
  policyId: string,
): Promise<DocumentRetentionResponse> {
  const res = await apiMutate<{ data: DocumentRetentionResponse }>(
    `/api/v1/documents/${documentId}/retention`,
    "POST",
    { policy_id: policyId },
  );
  return res.data;
}

export async function removeRetentionAssignment(
  documentId: string,
  retentionId: string,
): Promise<void> {
  await apiDelete(`/api/v1/documents/${documentId}/retention/${retentionId}`);
}

// --- Legal Holds ---

export async function placeLegalHold(
  documentId: string,
  reason: string,
): Promise<LegalHoldResponse> {
  const res = await apiMutate<{ data: LegalHoldResponse }>(
    `/api/v1/documents/${documentId}/legal-hold`,
    "POST",
    { reason },
  );
  return res.data;
}

export async function releaseLegalHold(
  documentId: string,
  holdId: string,
): Promise<LegalHoldResponse> {
  const res = await fetch(`/api/v1/documents/${documentId}/legal-hold/${holdId}`, {
    method: "DELETE",
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
  const json = await res.json() as { data: LegalHoldResponse };
  return json.data;
}
