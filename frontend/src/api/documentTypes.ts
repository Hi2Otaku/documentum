/** Document Types API client — consumes /api/v1/document-types/ endpoints. */
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

// --- Response types ---

export interface DocumentTypeResponse {
  id: string;
  name: string;
  description: string | null;
  metadata_schema: Record<string, unknown>;
  parent_type_id: string | null;
  parent_type_name: string | null;
  field_count: number;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentTypeCreate {
  name: string;
  description?: string | null;
  metadata_schema: Record<string, unknown>;
  parent_type_id?: string | null;
}

export interface DocumentTypeUpdate {
  name?: string;
  description?: string | null;
  metadata_schema?: Record<string, unknown>;
  parent_type_id?: string | null;
}

// --- API functions ---

export async function fetchDocumentTypes(): Promise<DocumentTypeResponse[]> {
  const res = await apiFetch<{ data: DocumentTypeResponse[] }>(
    "/api/v1/document-types/",
  );
  return res.data;
}

export async function fetchDocumentType(
  id: string,
): Promise<DocumentTypeResponse> {
  const res = await apiFetch<{ data: DocumentTypeResponse }>(
    `/api/v1/document-types/${id}`,
  );
  return res.data;
}

export async function createDocumentType(
  data: DocumentTypeCreate,
): Promise<DocumentTypeResponse> {
  const res = await apiMutate<{ data: DocumentTypeResponse }>(
    "/api/v1/document-types/",
    "POST",
    data,
  );
  return res.data;
}

export async function updateDocumentType(
  id: string,
  data: DocumentTypeUpdate,
): Promise<DocumentTypeResponse> {
  const res = await apiMutate<{ data: DocumentTypeResponse }>(
    `/api/v1/document-types/${id}`,
    "PUT",
    data,
  );
  return res.data;
}

export async function deleteDocumentType(id: string): Promise<void> {
  const res = await fetch(`/api/v1/document-types/${id}`, {
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
