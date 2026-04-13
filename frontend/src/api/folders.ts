/** Folder API client — consumes /api/v1/folders/ endpoints. */
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

// --- Response types ---

export interface FolderTreeNode {
  id: string;
  name: string;
  is_cabinet: boolean;
  document_count: number;
  children: FolderTreeNode[];
}

export interface FolderPathSegment {
  id: string;
  name: string;
}

export interface FolderResponse {
  id: string;
  name: string;
  description: string | null;
  parent_id: string | null;
  is_cabinet: boolean;
  document_count: number;
  path: FolderPathSegment[];
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

// --- Query key factory ---

export const folderKeys = {
  all: ["folders"] as const,
  tree: () => [...folderKeys.all, "tree"] as const,
  detail: (id: string) => [...folderKeys.all, id] as const,
  documents: (id: string) => [...folderKeys.all, id, "documents"] as const,
};

// --- API functions ---

export async function fetchFolderTree(): Promise<FolderTreeNode[]> {
  const res = await apiFetch<{ data: FolderTreeNode[] }>("/api/v1/folders/tree");
  return res.data;
}

export async function fetchFolder(id: string): Promise<FolderResponse> {
  const res = await apiFetch<{ data: FolderResponse }>(`/api/v1/folders/${id}`);
  return res.data;
}

export async function createCabinet(
  name: string,
  description?: string,
): Promise<FolderResponse> {
  const res = await apiMutate<{ data: FolderResponse }>(
    "/api/v1/folders/",
    "POST",
    { name, description },
  );
  return res.data;
}

export async function createFolder(
  parentId: string,
  name: string,
  description?: string,
): Promise<FolderResponse> {
  const res = await apiMutate<{ data: FolderResponse }>(
    `/api/v1/folders/${parentId}/children`,
    "POST",
    { name, description },
  );
  return res.data;
}

export async function renameFolder(
  id: string,
  name: string,
): Promise<FolderResponse> {
  const res = await apiMutate<{ data: FolderResponse }>(
    `/api/v1/folders/${id}`,
    "PUT",
    { name },
  );
  return res.data;
}

export async function moveFolder(
  id: string,
  parentId: string,
): Promise<FolderResponse> {
  const res = await apiMutate<{ data: FolderResponse }>(
    `/api/v1/folders/${id}`,
    "PUT",
    { parent_id: parentId },
  );
  return res.data;
}

export async function copyFolder(
  id: string,
  destParentId?: string,
): Promise<FolderResponse> {
  const res = await apiMutate<{ data: FolderResponse }>(
    `/api/v1/folders/${id}/copy`,
    "POST",
    destParentId ? { destination_parent_id: destParentId } : {},
  );
  return res.data;
}

export async function deleteFolder(id: string): Promise<void> {
  const res = await fetch(`/api/v1/folders/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
}

export async function fileDocument(
  folderId: string,
  documentId: string,
): Promise<void> {
  await apiMutate<unknown>(
    `/api/v1/folders/${folderId}/documents`,
    "POST",
    { document_id: documentId },
  );
}

export async function unfileDocument(
  folderId: string,
  documentId: string,
): Promise<void> {
  const res = await fetch(
    `/api/v1/folders/${folderId}/documents/${documentId}`,
    {
      method: "DELETE",
      headers: authHeaders(),
    },
  );
  if (res.status === 401) handle401();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
}

export async function fetchFolderDocuments(
  folderId: string,
  page?: number,
): Promise<{ data: unknown[]; meta: unknown }> {
  const url = page
    ? `/api/v1/folders/${folderId}/documents?page=${page}`
    : `/api/v1/folders/${folderId}/documents`;
  return apiFetch<{ data: unknown[]; meta: unknown }>(url);
}
