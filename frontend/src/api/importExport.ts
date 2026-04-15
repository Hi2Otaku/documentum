/** Import/Export API client -- consumes /api/v1/import-export endpoints. */
import { handle401 } from "./handle401";

const API = "/api/v1/import-export";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// --- Response types ---

export interface ImportExportJobResult {
  document_id: string;
  status: string;
  error?: string;
}

export interface ImportExportJobResponse {
  id: string;
  job_type: "export" | "import";
  status: "pending" | "running" | "completed" | "failed";
  total_count: number;
  success_count: number;
  failure_count: number;
  results: ImportExportJobResult[] | null;
  created_by: string;
  created_at: string;
  completed_at: string | null;
  download_ready: boolean;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ImportExportJobsListResponse {
  data: ImportExportJobResponse[];
  meta: PaginationMeta;
}

// --- Query key factory ---

export const importExportKeys = {
  all: ["import-export-jobs"] as const,
  list: (page: number) => [...importExportKeys.all, "list", page] as const,
  detail: (id: string) => [...importExportKeys.all, "detail", id] as const,
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

export interface ExportParams {
  document_ids?: string[];
  folder_ids?: string[];
  include_acls?: boolean;
  include_relationships?: boolean;
}

export async function exportDocuments(
  params: ExportParams,
): Promise<ImportExportJobResponse> {
  const res = await apiPost<{ data: ImportExportJobResponse }>(
    `${API}/export`,
    params,
  );
  return res.data;
}

export async function importPackage(
  file: File,
  targetFolderId?: string,
  conflictStrategy: string = "skip",
): Promise<ImportExportJobResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (targetFolderId) {
    formData.append("target_folder_id", targetFolderId);
  }
  formData.append("conflict_strategy", conflictStrategy);

  // Do NOT set Content-Type -- let browser set multipart boundary
  const res = await fetch(`${API}/import`, {
    method: "POST",
    headers: {
      ...authHeaders(),
    },
    body: formData,
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  const json = (await res.json()) as { data: ImportExportJobResponse };
  return json.data;
}

export async function fetchImportExportJobs(
  page = 1,
  pageSize = 20,
): Promise<ImportExportJobsListResponse> {
  return apiFetch<ImportExportJobsListResponse>(
    `${API}/jobs?page=${page}&page_size=${pageSize}`,
  );
}

export async function fetchImportExportJob(
  jobId: string,
): Promise<ImportExportJobResponse> {
  const res = await apiFetch<{ data: ImportExportJobResponse }>(
    `${API}/jobs/${jobId}`,
  );
  return res.data;
}

export function getExportDownloadUrl(jobId: string): string {
  return `${API}/download/${jobId}`;
}

export async function downloadExport(jobId: string): Promise<void> {
  const res = await fetch(`${API}/download/${jobId}`, {
    headers: {
      ...authHeaders(),
    },
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `export-${jobId}.zip`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
