/** Document API client — consumes /api/v1/documents endpoints. */
import { handle401 } from "./handle401";

// --- Auth helpers (mirrors inbox.ts pattern) ---

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

export interface DocumentResponse {
  id: string;
  title: string;
  author: string | null;
  filename: string;
  content_type: string;
  custom_properties: Record<string, unknown>;
  locked_by: string | null;
  locked_at: string | null;
  current_major_version: number;
  current_minor_version: number;
  current_version: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  is_deleted: boolean;
  lifecycle_state: string | null;
}

export interface DocumentVersionResponse {
  id: string;
  document_id: string;
  major_version: number;
  minor_version: number;
  content_hash: string;
  content_size: number;
  filename: string;
  content_type: string;
  comment: string | null;
  created_at: string;
  created_by: string | null;
  version_label: string;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export interface PaginatedDocumentsResponse {
  data: DocumentResponse[];
  meta: PaginationMeta;
}

export interface DocumentListParams {
  page?: number;
  page_size?: number;
  title?: string;
  author?: string;
}

export interface LifecycleTransitionResponse {
  id: string;
  lifecycle_state: string | null;
  title: string;
  updated_at: string;
}

// --- API functions ---

export async function fetchDocuments(
  params: DocumentListParams,
): Promise<PaginatedDocumentsResponse> {
  const url = buildUrl(
    "/api/v1/documents/",
    params as Record<string, string | number | undefined | null>,
  );
  return apiFetch<PaginatedDocumentsResponse>(url);
}

export async function fetchDocument(
  id: string,
): Promise<DocumentResponse> {
  const res = await apiFetch<{ data: DocumentResponse }>(
    `/api/v1/documents/${id}`,
  );
  return res.data;
}

export async function fetchVersions(
  documentId: string,
): Promise<DocumentVersionResponse[]> {
  const res = await apiFetch<{ data: DocumentVersionResponse[] }>(
    `/api/v1/documents/${documentId}/versions`,
  );
  return res.data;
}

export async function uploadDocument(
  file: File,
  title: string,
  author: string,
): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("title", title);
  formData.append("author", author);

  const res = await fetch("/api/v1/documents/", {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  const json = (await res.json()) as { data: DocumentResponse };
  return json.data;
}

export async function checkoutDocument(
  id: string,
): Promise<DocumentResponse> {
  const res = await apiMutate<{ data: DocumentResponse }>(
    `/api/v1/documents/${id}/checkout`,
    "POST",
  );
  return res.data;
}

export async function checkinDocument(
  id: string,
  file: File,
  comment?: string,
): Promise<DocumentVersionResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (comment) {
    formData.append("comment", comment);
  }

  const res = await fetch(`/api/v1/documents/${id}/checkin`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  const json = (await res.json()) as { data: DocumentVersionResponse };
  return json.data;
}

export async function cancelCheckout(
  id: string,
): Promise<DocumentResponse> {
  const res = await apiMutate<{ data: DocumentResponse }>(
    `/api/v1/documents/${id}/unlock`,
    "POST",
  );
  return res.data;
}

export async function transitionLifecycle(
  id: string,
  targetState: string,
): Promise<LifecycleTransitionResponse> {
  const res = await apiMutate<{ data: LifecycleTransitionResponse }>(
    `/api/v1/documents/${id}/lifecycle/transition`,
    "POST",
    { target_state: targetState },
  );
  return res.data;
}

export function downloadVersionUrl(
  documentId: string,
  versionId: string,
): string {
  return `/api/v1/documents/${documentId}/versions/${versionId}/download`;
}
