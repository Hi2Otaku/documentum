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

function decodeJwt(token: string): { sub: string; username: string; exp?: number } {
  const payload = JSON.parse(atob(token.split(".")[1]));
  return { sub: payload.sub, username: payload.username, exp: payload.exp };
}

function isTokenExpired(token: string): boolean {
  try {
    const { exp } = decodeJwt(token);
    if (!exp) return false;
    return Date.now() >= exp * 1000;
  } catch {
    return true;
  }
}

// Initialize from localStorage if token exists and is not expired
let storedToken = localStorage.getItem("token");
let initialUserId: string | null = null;
let initialUsername: string | null = null;

if (storedToken) {
  if (isTokenExpired(storedToken)) {
    localStorage.removeItem("token");
    storedToken = null;
  } else {
    try {
      const decoded = decodeJwt(storedToken);
      initialUserId = decoded.sub;
      initialUsername = decoded.username;
    } catch {
      localStorage.removeItem("token");
      storedToken = null;
    }
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
