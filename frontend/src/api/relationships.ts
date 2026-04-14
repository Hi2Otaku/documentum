/** Document Relationships API client — consumes /api/v1/documents/{id}/relationships endpoints. */
import { handle401 } from "./handle401";

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
  method: "POST" | "DELETE",
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

// --- Types ---

export type RelationshipType =
  | "supersedes"
  | "references"
  | "is_part_of"
  | "related_to";

export interface RelationshipResponse {
  id: string;
  source_document_id: string;
  target_document_id: string;
  relationship_type: RelationshipType;
  description: string | null;
  created_at: string;
  created_by: string | null;
  source_document_title: string | null;
  target_document_title: string | null;
}

export interface CreateRelationshipRequest {
  target_document_id: string;
  relationship_type: RelationshipType;
  description?: string;
}

// --- Query keys ---

export const relationshipKeys = {
  all: ["relationships"] as const,
  forDocument: (documentId: string) =>
    ["relationships", documentId] as const,
};

// --- API functions ---

export async function fetchRelationships(
  documentId: string,
): Promise<RelationshipResponse[]> {
  const res = await apiFetch<{ data: RelationshipResponse[] }>(
    `/api/v1/documents/${documentId}/relationships`,
  );
  return res.data;
}

export async function createRelationship(
  documentId: string,
  data: CreateRelationshipRequest,
): Promise<RelationshipResponse> {
  const res = await apiMutate<{ data: RelationshipResponse }>(
    `/api/v1/documents/${documentId}/relationships`,
    "POST",
    data,
  );
  return res.data;
}

export async function deleteRelationship(
  documentId: string,
  relationshipId: string,
): Promise<void> {
  await apiMutate<unknown>(
    `/api/v1/documents/${documentId}/relationships/${relationshipId}`,
    "DELETE",
  );
}

// --- Helpers ---

export const RELATIONSHIP_TYPE_LABELS: Record<RelationshipType, string> = {
  supersedes: "Supersedes",
  references: "References",
  is_part_of: "Is Part Of",
  related_to: "Related To",
};

export const RELATIONSHIP_TYPES: RelationshipType[] = [
  "supersedes",
  "references",
  "is_part_of",
  "related_to",
];
