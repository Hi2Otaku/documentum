/** Analytics API client — consumes /api/v1/analytics endpoints. */
import { handle401 } from "./handle401";

const API = "/api/v1/analytics";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// --- Response types ---

export interface ExecutionPath {
  path: string[];
  frequency: number;
  avg_total_duration_seconds: number | null;
}

export interface CycleTimeStats {
  activity_name: string | null;
  template_name: string | null;
  template_id: string | null;
  avg_seconds: number;
  median_seconds: number;
  min_seconds: number;
  max_seconds: number;
  sample_count: number;
}

export interface BottleneckActivity {
  activity_name: string;
  template_name: string;
  avg_duration_seconds: number;
  total_executions: number;
  pct_of_total_time: number;
}

export interface AnalyticsSummary {
  total_instances: number;
  completed_instances: number;
  avg_completion_seconds: number | null;
  paths_discovered: number;
  last_refreshed: string | null;
}

// --- Query key factory ---

export const analyticsKeys = {
  summary: ["analytics", "summary"] as const,
  paths: (templateId?: string) =>
    ["analytics", "paths", templateId ?? "all"] as const,
  cycleTimes: (templateId?: string, groupBy?: string) =>
    ["analytics", "cycleTimes", templateId ?? "all", groupBy ?? "activity"] as const,
  bottlenecks: (templateId?: string) =>
    ["analytics", "bottlenecks", templateId ?? "all"] as const,
};

// --- Helpers ---

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

async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) handle401();
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// --- API functions ---

export async function fetchSummary(): Promise<AnalyticsSummary> {
  const res = await apiFetch<{ data: AnalyticsSummary }>(`${API}/summary`);
  return res.data;
}

export async function fetchPaths(
  templateId?: string,
  limit?: number,
): Promise<ExecutionPath[]> {
  const params = new URLSearchParams();
  if (templateId) params.set("template_id", templateId);
  if (limit != null) params.set("limit", String(limit));
  const qs = params.toString();
  const res = await apiFetch<{ data: ExecutionPath[] }>(
    `${API}/paths${qs ? `?${qs}` : ""}`,
  );
  return res.data;
}

export async function fetchCycleTimes(
  templateId?: string,
  groupBy?: "activity" | "template",
): Promise<CycleTimeStats[]> {
  const params = new URLSearchParams();
  if (templateId) params.set("template_id", templateId);
  if (groupBy) params.set("group_by", groupBy);
  const qs = params.toString();
  const res = await apiFetch<{ data: CycleTimeStats[] }>(
    `${API}/cycle-times${qs ? `?${qs}` : ""}`,
  );
  return res.data;
}

export async function fetchBottlenecks(
  templateId?: string,
  limit?: number,
): Promise<BottleneckActivity[]> {
  const params = new URLSearchParams();
  if (templateId) params.set("template_id", templateId);
  if (limit != null) params.set("limit", String(limit));
  const qs = params.toString();
  const res = await apiFetch<{ data: BottleneckActivity[] }>(
    `${API}/bottlenecks${qs ? `?${qs}` : ""}`,
  );
  return res.data;
}

export async function triggerRefresh(): Promise<void> {
  await apiPost<{ data: unknown }>(`${API}/refresh`);
}
