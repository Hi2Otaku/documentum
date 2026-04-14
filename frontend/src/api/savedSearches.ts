/** Saved Searches API client — consumes /api/v1/saved-searches endpoints. */
import { handle401 } from "./handle401";
import type { SearchFilterValues } from "../components/search/SearchFilters";

// --- Auth helpers (mirrors search.ts pattern) ---

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// --- Response types ---

export interface SavedSearch {
  id: string;
  name: string;
  query: string;
  filters: SearchFilterValues;
  is_smart_folder: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface SavedSearchCreate {
  name: string;
  query: string;
  filters: SearchFilterValues;
  is_smart_folder?: boolean;
  display_order?: number;
}

export interface SavedSearchUpdate {
  name?: string;
  query?: string;
  filters?: SearchFilterValues;
  is_smart_folder?: boolean;
  display_order?: number;
}

// --- Query key factory ---

export const savedSearchKeys = {
  all: ["saved-searches"] as const,
  list: () => [...savedSearchKeys.all, "list"] as const,
  smartFolders: () => [...savedSearchKeys.all, "smart-folders"] as const,
};

// --- API functions ---

export async function fetchSavedSearches(): Promise<SavedSearch[]> {
  const res = await fetch("/api/v1/saved-searches/", {
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
  const json = await res.json();
  return json.data as SavedSearch[];
}

export async function fetchSmartFolders(): Promise<SavedSearch[]> {
  const res = await fetch("/api/v1/saved-searches/?smart_folders_only=true", {
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
  const json = await res.json();
  return json.data as SavedSearch[];
}

export async function createSavedSearch(
  data: SavedSearchCreate,
): Promise<SavedSearch> {
  const res = await fetch("/api/v1/saved-searches/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(data),
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  const json = await res.json();
  return json.data as SavedSearch;
}

export async function updateSavedSearch(
  id: string,
  data: SavedSearchUpdate,
): Promise<SavedSearch> {
  const res = await fetch(`/api/v1/saved-searches/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(data),
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  const json = await res.json();
  return json.data as SavedSearch;
}

export async function deleteSavedSearch(id: string): Promise<void> {
  const res = await fetch(`/api/v1/saved-searches/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
}
