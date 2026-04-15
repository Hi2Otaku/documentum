/** Monitoring API client — consumes /api/v1/monitoring endpoints. */
import { handle401 } from "./handle401";

const API = "/api/v1/monitoring";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// --- Response types ---

export interface ComponentHealth {
  name: string;
  status: "healthy" | "degraded" | "unhealthy";
  latency_ms: number | null;
  details: string | null;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  components: ComponentHealth[];
  checked_at: string;
}

export interface WorkerInfo {
  hostname: string;
  status: string;
  active_tasks: number;
  processed: number;
  pid: number | null;
}

export interface QueueMetrics {
  queue_name: string;
  depth: number;
}

export interface SystemMetrics {
  workers: WorkerInfo[];
  queues: QueueMetrics[];
  total_active_tasks: number;
  total_scheduled_tasks: number;
}

export interface AlertRule {
  id: string;
  name: string;
  metric_name: string;
  operator: string;
  threshold: number;
  enabled: boolean;
  notification_message: string | null;
  created_at: string;
}

export interface AlertRuleCreate {
  name: string;
  metric_name: string;
  operator: string;
  threshold: number;
  enabled?: boolean;
  notification_message?: string;
}

// --- Query key factory ---

export const monitoringKeys = {
  health: ["monitoring", "health"] as const,
  metrics: ["monitoring", "metrics"] as const,
  alerts: ["monitoring", "alerts"] as const,
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

async function apiPut<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "PUT",
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

async function apiDelete(url: string): Promise<void> {
  const res = await fetch(url, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (res.status === 401) handle401();
  if (!res.ok && res.status !== 204) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
}

// --- API functions ---

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await apiFetch<{ data: HealthResponse }>(`${API}/health`);
  return res.data;
}

export async function fetchMetrics(): Promise<SystemMetrics> {
  const res = await apiFetch<{ data: SystemMetrics }>(`${API}/metrics`);
  return res.data;
}

export async function fetchAlertRules(): Promise<AlertRule[]> {
  const res = await apiFetch<{ data: AlertRule[] }>(`${API}/alerts`);
  return res.data;
}

export async function createAlertRule(
  data: AlertRuleCreate,
): Promise<AlertRule> {
  const res = await apiPost<{ data: AlertRule }>(`${API}/alerts`, data);
  return res.data;
}

export async function updateAlertRule(
  id: string,
  data: Partial<AlertRuleCreate>,
): Promise<AlertRule> {
  const res = await apiPut<{ data: AlertRule }>(`${API}/alerts/${id}`, data);
  return res.data;
}

export async function deleteAlertRule(id: string): Promise<void> {
  await apiDelete(`${API}/alerts/${id}`);
}
