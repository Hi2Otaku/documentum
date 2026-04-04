import type {
  ApiResponse,
  ProcessTemplate,
  ProcessTemplateDetail,
  ValidationResult,
  ActivityTemplate,
  FlowTemplate,
  ProcessVariable,
} from '../types/workflow';

const BASE = '/api/v1/templates';

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

/** List all templates */
export async function listTemplates(): Promise<ProcessTemplate[]> {
  const res = await apiFetch<ApiResponse<ProcessTemplate[]>>(BASE);
  return res.data;
}

/** Get template detail with activities, flows, variables */
export async function getTemplateDetail(
  id: string,
): Promise<ProcessTemplateDetail> {
  const res = await apiFetch<ApiResponse<ProcessTemplateDetail>>(
    `${BASE}/${id}`,
  );
  return res.data;
}

/** Create a new template */
export async function createTemplate(data: {
  name: string;
  description?: string;
}): Promise<ProcessTemplate> {
  const res = await apiFetch<ApiResponse<ProcessTemplate>>(BASE, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return res.data;
}

/** Add activity to template */
export async function addActivity(
  templateId: string,
  data: {
    name: string;
    activity_type: string;
    description?: string;
    performer_type?: string | null;
    performer_id?: string | null;
    trigger_type?: string;
    method_name?: string | null;
    position_x?: number | null;
    position_y?: number | null;
    routing_type?: string | null;
    performer_list?: string[] | null;
  },
): Promise<ActivityTemplate> {
  const res = await apiFetch<ApiResponse<ActivityTemplate>>(
    `${BASE}/${templateId}/activities`,
    { method: 'POST', body: JSON.stringify(data) },
  );
  return res.data;
}

/** Update an activity */
export async function updateActivity(
  templateId: string,
  activityId: string,
  data: {
    name?: string;
    description?: string;
    performer_type?: string | null;
    performer_id?: string | null;
    trigger_type?: string;
    method_name?: string | null;
    position_x?: number | null;
    position_y?: number | null;
    routing_type?: string | null;
    performer_list?: string[] | null;
  },
): Promise<ActivityTemplate> {
  const res = await apiFetch<ApiResponse<ActivityTemplate>>(
    `${BASE}/${templateId}/activities/${activityId}`,
    { method: 'PUT', body: JSON.stringify(data) },
  );
  return res.data;
}

/** Delete an activity */
export async function deleteActivity(
  templateId: string,
  activityId: string,
): Promise<void> {
  await apiFetch(`${BASE}/${templateId}/activities/${activityId}`, {
    method: 'DELETE',
  });
}

/** Add flow to template */
export async function addFlow(
  templateId: string,
  data: {
    source_activity_id: string;
    target_activity_id: string;
    flow_type?: string;
    condition_expression?: string | null;
    display_label?: string | null;
  },
): Promise<FlowTemplate> {
  const res = await apiFetch<ApiResponse<FlowTemplate>>(
    `${BASE}/${templateId}/flows`,
    { method: 'POST', body: JSON.stringify(data) },
  );
  return res.data;
}

/** Delete a flow */
export async function deleteFlow(
  templateId: string,
  flowId: string,
): Promise<void> {
  await apiFetch(`${BASE}/${templateId}/flows/${flowId}`, {
    method: 'DELETE',
  });
}

/** Validate template */
export async function validateTemplate(
  id: string,
): Promise<ValidationResult> {
  const res = await apiFetch<ApiResponse<ValidationResult>>(
    `${BASE}/${id}/validate`,
    { method: 'POST' },
  );
  return res.data;
}

/** Delete a template */
export async function deleteTemplate(id: string): Promise<void> {
  await apiFetch(`${BASE}/${id}`, { method: 'DELETE' });
}

/** Update template metadata */
export async function updateTemplate(
  id: string,
  data: { name?: string; description?: string | null },
): Promise<ProcessTemplate> {
  const res = await apiFetch<ApiResponse<ProcessTemplate>>(`${BASE}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
  return res.data;
}

/** Update a flow */
export async function updateFlow(
  templateId: string,
  flowId: string,
  data: {
    source_activity_id?: string;
    target_activity_id?: string;
    flow_type?: string;
    condition_expression?: string | null;
    display_label?: string | null;
  },
): Promise<FlowTemplate> {
  const res = await apiFetch<ApiResponse<FlowTemplate>>(
    `${BASE}/${templateId}/flows/${flowId}`,
    { method: 'PUT', body: JSON.stringify(data) },
  );
  return res.data;
}

/** Create a variable */
export async function createVariable(
  templateId: string,
  data: {
    name: string;
    variable_type: string;
    string_value?: string | null;
    int_value?: number | null;
    bool_value?: boolean | null;
    date_value?: string | null;
  },
): Promise<ProcessVariable> {
  const res = await apiFetch<ApiResponse<ProcessVariable>>(
    `${BASE}/${templateId}/variables`,
    { method: 'POST', body: JSON.stringify(data) },
  );
  return res.data;
}

/** Update a variable */
export async function updateVariable(
  templateId: string,
  variableId: string,
  data: {
    name?: string;
    variable_type?: string;
    string_value?: string | null;
    int_value?: number | null;
    bool_value?: boolean | null;
    date_value?: string | null;
  },
): Promise<ProcessVariable> {
  const res = await apiFetch<ApiResponse<ProcessVariable>>(
    `${BASE}/${templateId}/variables/${variableId}`,
    { method: 'PUT', body: JSON.stringify(data) },
  );
  return res.data;
}

/** Delete a variable */
export async function deleteVariable(
  templateId: string,
  variableId: string,
): Promise<void> {
  await apiFetch(`${BASE}/${templateId}/variables/${variableId}`, {
    method: 'DELETE',
  });
}

/** Install template */
export async function installTemplate(id: string): Promise<ProcessTemplate> {
  const res = await apiFetch<ApiResponse<ProcessTemplate>>(
    `${BASE}/${id}/install`,
    { method: 'POST' },
  );
  return res.data;
}
