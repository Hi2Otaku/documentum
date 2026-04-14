/** Search API client — consumes /api/v1/search endpoint. */
import { handle401 } from "./handle401";

// --- Auth helpers (mirrors documents.ts pattern) ---

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
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

export interface SearchResult {
  id: string;
  title: string;
  author: string | null;
  filename: string;
  content_type: string;
  lifecycle_state: string | null;
  extraction_status: string;
  document_type_name: string | null;
  headline: string | null;
  rank: number;
}

export interface SearchParams {
  q: string;
  folder_id?: string;
  document_type_id?: string;
  lifecycle_state?: string;
  page?: number;
  page_size?: number;
}

export interface SearchResponse {
  data: SearchResult[];
  meta: {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
  };
}

// --- API functions ---

export async function searchDocuments(
  params: SearchParams,
): Promise<SearchResponse> {
  const url = buildUrl(
    "/api/v1/search/",
    params as Record<string, string | number | undefined | null>,
  );
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
  return res.json() as Promise<SearchResponse>;
}
