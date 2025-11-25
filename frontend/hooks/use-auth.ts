"use client";

import { useAuthStore, User } from "@/lib/auth-store";
import { useRouter } from "next/navigation";

// API base URL from environment
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name: string;
}

export interface AuthError {
  message: string;
  field?: string;
}

export function useAuth() {
  const router = useRouter();
  const {
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    isLoading,
    setUser,
    setTokens,
    logout: clearAuth,
    setLoading,
  } = useAuthStore();

  // Login function
  const login = async (
    credentials: LoginCredentials,
  ): Promise<{ success: boolean; error?: AuthError }> => {
    try {
      setLoading(true);

      // Call login API (using form data format)
      const formData = new URLSearchParams();
      formData.append("username", credentials.email); // Backend expects "username" but it's actually email
      formData.append("password", credentials.password);

      const response = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData.toString(),
      });

      if (!response.ok) {
        const error = await response.json();
        setLoading(false);
        return {
          success: false,
          error: {
            message:
              error.detail || "Login failed. Please check your credentials.",
          },
        };
      }

      const tokens = await response.json();

      // Store tokens
      setTokens(tokens.access_token, tokens.refresh_token);

      // Fetch user profile
      const userResponse = await fetch(`${API_URL}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${tokens.access_token}`,
        },
      });

      if (!userResponse.ok) {
        throw new Error("Failed to fetch user profile");
      }

      const userData = await userResponse.json();
      setUser(userData);
      setLoading(false);

      // Redirect to dashboard
      router.push("/dashboard");

      return { success: true };
    } catch (error) {
      setLoading(false);
      return {
        success: false,
        error: {
          message:
            error instanceof Error
              ? error.message
              : "An unexpected error occurred",
        },
      };
    }
  };

  // Register function
  const register = async (
    data: RegisterData,
  ): Promise<{ success: boolean; error?: AuthError }> => {
    try {
      setLoading(true);

      // Call register API
      const response = await fetch(`${API_URL}/api/v1/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const error = await response.json();
        setLoading(false);

        // Parse validation errors
        let errorMessage = "Registration failed. Please try again.";
        if (error.detail) {
          if (typeof error.detail === "string") {
            errorMessage = error.detail;
          } else if (Array.isArray(error.detail)) {
            // Pydantic validation errors
            errorMessage = error.detail.map((e: any) => e.msg).join(", ");
          }
        }

        return {
          success: false,
          error: {
            message: errorMessage,
          },
        };
      }

      // Registration successful - now login
      const loginResult = await login({
        email: data.email,
        password: data.password,
      });

      return loginResult;
    } catch (error) {
      setLoading(false);
      return {
        success: false,
        error: {
          message:
            error instanceof Error
              ? error.message
              : "An unexpected error occurred",
        },
      };
    }
  };

  // Logout function
  const logout = async () => {
    clearAuth();
    router.push("/login");
  };

  // Refresh access token (called automatically when token expires)
  const refreshAccessToken = async (): Promise<boolean> => {
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      });

      if (!response.ok) {
        // Refresh token expired, logout
        clearAuth();
        router.push("/login");
        return false;
      }

      const tokens = await response.json();
      setTokens(tokens.access_token, refreshToken); // Keep same refresh token
      return true;
    } catch (error) {
      clearAuth();
      router.push("/login");
      return false;
    }
  };

  return {
    user,
    accessToken,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    refreshAccessToken,
  };
}
