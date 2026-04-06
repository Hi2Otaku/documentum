/** Virtual Document API client — consumes /api/v1/virtual-documents endpoints. */
import { handle401 } from "./handle401";

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
  if (res.status === 401) handle401();
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

async function apiMutate<T>(
  url: string,
  method: "POST" | "PUT" | "PATCH" | "DELETE",
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

export interface VirtualDocumentChildResponse {
  id: string;
  virtual_document_id: string;
  child_document_id: string;
  order_index: number;
  child_title: string | null;
  child_filename: string | null;
  created_at: string;
}

export interface VirtualDocumentResponse {
  id: string;
  document_id: string;
  description: string | null;
  document_title: string | null;
  created_at: string;
  updated_at: string;
  children: VirtualDocumentChildResponse[];
}

export interface PaginatedVirtualDocumentsResponse {
  data: VirtualDocumentResponse[];
  meta: { page: number; page_size: number; total_count: number; total_pages: number };
}

// --- API functions ---

export async function createVirtualDocument(
  title: string,
  description?: string,
): Promise<VirtualDocumentResponse> {
  return apiMutate<VirtualDocumentResponse>(
    "/api/v1/virtual-documents/",
    "POST",
    { title, description },
  );
}

export async function fetchVirtualDocuments(params: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedVirtualDocumentsResponse> {
  const url = buildUrl(
    "/api/v1/virtual-documents/",
    params as Record<string, string | number | undefined | null>,
  );
  return apiFetch<PaginatedVirtualDocumentsResponse>(url);
}

export async function fetchVirtualDocument(
  id: string,
): Promise<VirtualDocumentResponse> {
  return apiFetch<VirtualDocumentResponse>(`/api/v1/virtual-documents/${id}`);
}

export async function addChild(
  virtualDocId: string,
  childDocumentId: string,
): Promise<VirtualDocumentChildResponse> {
  return apiMutate<VirtualDocumentChildResponse>(
    `/api/v1/virtual-documents/${virtualDocId}/children`,
    "POST",
    { child_document_id: childDocumentId },
  );
}

export async function removeChild(
  virtualDocId: string,
  childId: string,
): Promise<{ message: string }> {
  return apiMutate<{ message: string }>(
    `/api/v1/virtual-documents/${virtualDocId}/children/${childId}`,
    "DELETE",
  );
}

export async function reorderChildren(
  virtualDocId: string,
  childIds: string[],
): Promise<VirtualDocumentChildResponse[]> {
  return apiMutate<VirtualDocumentChildResponse[]>(
    `/api/v1/virtual-documents/${virtualDocId}/children/reorder`,
    "PUT",
    { child_ids: childIds },
  );
}

export function mergePdfUrl(virtualDocId: string): string {
  return `/api/v1/virtual-documents/${virtualDocId}/merge-pdf`;
}

export async function downloadMergedPdf(virtualDocId: string): Promise<void> {
  const url = mergePdfUrl(virtualDocId);
  const res = await fetch(url, {
    method: "POST",
    headers: authHeaders(),
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = `virtual-document-${virtualDocId}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(blobUrl);
}
