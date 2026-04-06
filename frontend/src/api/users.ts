import { handle401 } from "./handle401";

const BASE = "/api/v1/users";

export interface UserProfile {
  id: string;
  username: string;
  email: string | null;
  is_superuser: boolean;
  is_available: boolean;
  delegate_id: string | null;
}

/**
 * Fetch user profile by ID.
 * Returns the unwrapped UserProfile from EnvelopeResponse.
 */
export async function fetchUserProfile(
  token: string,
  userId: string
): Promise<UserProfile> {
  const res = await fetch(`${BASE}/${userId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (res.status === 401) handle401();
  if (!res.ok) {
    throw new Error("Failed to fetch user profile.");
  }

  const json = await res.json();
  return json.data;
}

/**
 * Update the current user's availability status.
 * Returns the unwrapped UserProfile from EnvelopeResponse.
 */
export async function updateAvailability(
  token: string,
  isAvailable: boolean,
  delegateId?: string
): Promise<UserProfile> {
  const res = await fetch(`${BASE}/me/availability`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      is_available: isAvailable,
      delegate_id: delegateId ?? null,
    }),
  });

  if (res.status === 401) handle401();
  if (!res.ok) {
    throw new Error("Failed to update availability.");
  }

  const json = await res.json();
  return json.data;
}
