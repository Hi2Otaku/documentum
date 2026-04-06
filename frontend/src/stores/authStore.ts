import { create } from "zustand";
import { fetchUserProfile, updateAvailability } from "../api/users";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  userId: string | null;
  username: string | null;
  isSuperuser: boolean;
  isAvailable: boolean;
  setToken: (token: string) => void;
  loadProfile: () => Promise<void>;
  setAvailability: (available: boolean) => void;
  logout: () => void;
}

function decodeJwt(token: string): { sub: string; username: string } {
  const payload = JSON.parse(atob(token.split(".")[1]));
  return { sub: payload.sub, username: payload.username };
}

// Initialize from localStorage if token exists
const storedToken = localStorage.getItem("token");
let initialUserId: string | null = null;
let initialUsername: string | null = null;

if (storedToken) {
  try {
    const decoded = decodeJwt(storedToken);
    initialUserId = decoded.sub;
    initialUsername = decoded.username;
  } catch {
    // Invalid token in storage; will be cleared on next action
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: storedToken,
  isAuthenticated: !!storedToken,
  userId: initialUserId,
  username: initialUsername,
  isSuperuser: false,
  isAvailable: true,

  setToken: (token: string) => {
    localStorage.setItem("token", token);
    const decoded = decodeJwt(token);
    set({
      token,
      isAuthenticated: true,
      userId: decoded.sub,
      username: decoded.username,
    });
  },

  loadProfile: async () => {
    const { token, userId } = get();
    if (!token || !userId) return;
    const profile = await fetchUserProfile(token, userId);
    set({
      isSuperuser: profile.is_superuser,
      isAvailable: profile.is_available,
    });
  },

  setAvailability: (available: boolean) => {
    const prev = get().isAvailable;
    set({ isAvailable: available });

    const { token } = get();
    if (!token) return;

    updateAvailability(token, available).catch(() => {
      // Revert on failure
      set({ isAvailable: prev });
    });
  },

  logout: () => {
    localStorage.removeItem("token");
    set({
      token: null,
      isAuthenticated: false,
      userId: null,
      username: null,
      isSuperuser: false,
      isAvailable: true,
    });
  },
}));
