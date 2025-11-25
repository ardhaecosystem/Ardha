import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// User type (matches backend UserResponse)
export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  avatar_url?: string;
  github_id?: string;
  google_id?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

// Auth state interface
interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  setUser: (user: User) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

// Create Zustand store with localStorage persistence
export const useAuthStore = create<AuthState>()(
  persist(
    (set: (state: Partial<AuthState>) => void) => ({
      // Initial state
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      // Set user data
      setUser: (user: User) =>
        set({
          user,
          isAuthenticated: true,
        }),

      // Set authentication tokens
      setTokens: (accessToken: string, refreshToken: string) =>
        set({
          accessToken,
          refreshToken,
        }),

      // Logout and clear all state
      logout: () =>
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        }),

      // Set loading state
      setLoading: (loading: boolean) =>
        set({
          isLoading: loading,
        }),
    }),
    {
      name: "ardha-auth-storage", // localStorage key
      storage: createJSONStorage(() => localStorage),
      // Only persist tokens and user, not loading state
      partialize: (state: AuthState) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
