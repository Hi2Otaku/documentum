/** Identity Provider API client -- consumes /api/v1/identity endpoints. */
import { handle401 } from "./handle401";

// --- Auth helpers ---

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(url: string, authenticated = true): Promise<T> {
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(authenticated ? authHeaders() : {}),
    },
  });
  if (res.status === 401 && authenticated) handle401();
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

async function apiDelete(url: string): Promise<void> {
  const res = await fetch(url, {
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

// --- Types ---

export interface IdentityProvider {
  id: string;
  name: string;
  provider_type: "ldap" | "saml" | "oidc";
  config: Record<string, unknown>;
  is_enabled: boolean;
  created_at: string;
}

export interface IdentityProviderPublic {
  id: string;
  name: string;
  provider_type: "ldap" | "saml" | "oidc";
}

export interface IdentityProviderCreate {
  name: string;
  provider_type: "ldap" | "saml" | "oidc";
  config: Record<string, unknown>;
  is_enabled?: boolean;
}

export interface IdentityProviderUpdate {
  name?: string;
  config?: Record<string, unknown>;
  is_enabled?: boolean;
}

export interface SSOLoginResponse {
  redirect_url: string;
  state?: string;
  code_verifier?: string;
}

// --- Provider CRUD (admin, authenticated) ---

const BASE = "/api/v1/identity";

export async function fetchProviders(): Promise<IdentityProvider[]> {
  const res = await apiFetch<{ data: IdentityProvider[] }>(`${BASE}/providers`);
  return res.data;
}

export async function fetchProvider(id: string): Promise<IdentityProvider> {
  const res = await apiFetch<{ data: IdentityProvider }>(`${BASE}/providers/${id}`);
  return res.data;
}

export async function createProvider(
  data: IdentityProviderCreate,
): Promise<IdentityProvider> {
  const res = await apiMutate<{ data: IdentityProvider }>(
    `${BASE}/providers`,
    "POST",
    data,
  );
  return res.data;
}

export async function updateProvider(
  id: string,
  data: IdentityProviderUpdate,
): Promise<IdentityProvider> {
  const res = await apiMutate<{ data: IdentityProvider }>(
    `${BASE}/providers/${id}`,
    "PUT",
    data,
  );
  return res.data;
}

export async function deleteProvider(id: string): Promise<void> {
  await apiDelete(`${BASE}/providers/${id}`);
}

// --- LDAP-specific (admin) ---

export async function testLdapConnection(
  id: string,
): Promise<{ success: boolean; message: string }> {
  const res = await apiMutate<{ data: { success: boolean; message: string } }>(
    `${BASE}/providers/${id}/ldap/test`,
    "POST",
  );
  return res.data;
}

export async function syncLdap(
  id: string,
): Promise<{ users_synced: number; groups_synced: number; message: string }> {
  const res = await apiMutate<{
    data: { users_synced: number; groups_synced: number; message: string };
  }>(`${BASE}/providers/${id}/ldap/sync`, "POST");
  return res.data;
}

// --- Public (no auth -- for login page) ---

export async function fetchEnabledProviders(): Promise<IdentityProviderPublic[]> {
  const res = await apiFetch<{ data: IdentityProviderPublic[] }>(
    `${BASE}/providers/public`,
    false,
  );
  return res.data;
}

// --- SSO login initiation (public) ---

export async function initiateSSOLogin(id: string): Promise<SSOLoginResponse> {
  const res = await apiFetch<{ data: SSOLoginResponse }>(
    `${BASE}/sso/${id}/login`,
    false,
  );
  return res.data;
}
