/** Retention & Legal Hold API client. */

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

async function apiMutate<T>(
  url: string,
  method: "POST" | "PUT" | "DELETE",
  body?: unknown,
): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// --- Types ---

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

export interface RetentionStatusResponse {
  document_id: string;
  is_retained: boolean;
  is_held: boolean;
  is_deletable: boolean;
  deletion_blocked_reason: string | null;
  active_retentions: DocumentRetentionResponse[];
  active_holds: LegalHoldResponse[];
}

// --- API Functions ---

export async function fetchRetentionStatus(
  documentId: string,
): Promise<RetentionStatusResponse> {
  const res = await apiFetch<{ data: RetentionStatusResponse }>(
    `/api/v1/documents/${documentId}/retention-status`,
  );
  return res.data;
}

export async function fetchRetentionPolicies(): Promise<
  RetentionPolicyResponse[]
> {
  const res = await apiFetch<{ data: RetentionPolicyResponse[] }>(
    `/api/v1/retention-policies`,
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
  await apiMutate<unknown>(
    `/api/v1/documents/${documentId}/retention/${retentionId}`,
    "DELETE",
  );
}

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
  const res = await apiMutate<{ data: LegalHoldResponse }>(
    `/api/v1/documents/${documentId}/legal-hold/${holdId}`,
    "DELETE",
  );
  return res.data;
}
