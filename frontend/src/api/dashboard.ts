import type { ProcessTemplate } from '../types/workflow';

const BASE = '/api/v1';

/** Get auth header from stored token */
function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// --- Types ---

export interface KpiMetrics {
  running: number;
  halted: number;
  finished: number;
  failed: number;
  avg_completion_hours: number;
}

export interface BottleneckActivity {
  activity_name: string;
  avg_duration_hours: number;
  template_name: string | null;
}

export interface UserWorkload {
  user_id: string;
  username: string;
  assigned: number;
  completed: number;
  pending: number;
}

export interface SlaCompliance {
  activity_name: string;
  on_time: number;
  overdue: number;
  compliance_percent: number;
}

export interface DashboardMetrics {
  kpi: KpiMetrics;
  bottleneck_activities: BottleneckActivity[];
  workload: UserWorkload[];
  sla_compliance: SlaCompliance[];
}

interface ApiResponse<T> {
  data: T;
}

// --- API Functions ---

/** Fetch dashboard metrics, optionally filtered by template */
export async function fetchDashboardMetrics(
  templateId?: string,
): Promise<DashboardMetrics> {
  const params = templateId ? `?template_id=${templateId}` : '';
  const res = await apiFetch<ApiResponse<DashboardMetrics>>(
    `${BASE}/dashboard/metrics${params}`,
  );
  return res.data;
}

/** List templates for the filter dropdown */
export async function listTemplatesForFilter(): Promise<ProcessTemplate[]> {
  const res = await apiFetch<ApiResponse<ProcessTemplate[]>>(
    `${BASE}/templates/`,
  );
  return res.data;
}
