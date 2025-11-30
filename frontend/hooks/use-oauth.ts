"use client";

import { useAuthStore } from "@/lib/auth-store";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// OAuth provider configurations
const GITHUB_CLIENT_ID = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || "";
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

export function useOAuth() {
  const router = useRouter();
  const { setUser, setTokens, setLoading } = useAuthStore();

  /**
   * Generate a secure random state parameter for CSRF protection
   */
  const generateState = (): string => {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, (byte) => byte.toString(16).padStart(2, "0")).join(
      "",
    );
  };

  /**
   * Initiate GitHub OAuth login flow
   */
  const loginWithGitHub = () => {
    try {
      // Generate state for CSRF protection
      const state = generateState();
      sessionStorage.setItem("oauth_state", state);
      sessionStorage.setItem("oauth_provider", "github");

      // Build GitHub authorization URL
      const redirectUri = `${window.location.origin}/auth/callback/github`;
      const scope = "read:user user:email";

      const params = new URLSearchParams({
        client_id: GITHUB_CLIENT_ID,
        redirect_uri: redirectUri,
        scope: scope,
        state: state,
      });

      const authUrl = `https://github.com/login/oauth/authorize?${params.toString()}`;

      // Redirect to GitHub
      window.location.href = authUrl;
    } catch (error) {
      console.error("Failed to initiate GitHub OAuth:", error);
    }
  };

  /**
   * Initiate Google OAuth login flow
   */
  const loginWithGoogle = () => {
    try {
      // Generate state for CSRF protection
      const state = generateState();
      sessionStorage.setItem("oauth_state", state);
      sessionStorage.setItem("oauth_provider", "google");

      // Build Google authorization URL
      const redirectUri = `${window.location.origin}/auth/callback/google`;
      const scope = "openid email profile";

      const params = new URLSearchParams({
        client_id: GOOGLE_CLIENT_ID,
        redirect_uri: redirectUri,
        response_type: "code",
        scope: scope,
        state: state,
        access_type: "offline",
        prompt: "consent",
      });

      const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;

      // Redirect to Google
      window.location.href = authUrl;
    } catch (error) {
      console.error("Failed to initiate Google OAuth:", error);
    }
  };

  /**
   * Handle OAuth callback from GitHub or Google
   */
  const handleOAuthCallback = async (
    provider: "github" | "google",
    code: string,
    state: string,
  ): Promise<{ success: boolean; error?: string }> => {
    try {
      setLoading(true);

      // Verify state parameter for CSRF protection
      const savedState = sessionStorage.getItem("oauth_state");
      const savedProvider = sessionStorage.getItem("oauth_provider");

      if (!savedState || state !== savedState) {
        throw new Error("Invalid state parameter - possible CSRF attack");
      }

      if (savedProvider !== provider) {
        throw new Error("Provider mismatch - possible security issue");
      }

      // Exchange code for tokens via backend
      const response = await fetch(`${API_URL}/api/v1/auth/oauth/${provider}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ code }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `${provider} OAuth failed`);
      }

      const data = await response.json();

      // Store tokens and user
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);

      // Clean up session storage
      sessionStorage.removeItem("oauth_state");
      sessionStorage.removeItem("oauth_provider");

      setLoading(false);

      // Redirect to dashboard
      router.push("/dashboard");

      return { success: true };
    } catch (error) {
      setLoading(false);

      // Clean up on error
      sessionStorage.removeItem("oauth_state");
      sessionStorage.removeItem("oauth_provider");

      return {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "OAuth authentication failed",
      };
    }
  };

  return {
    loginWithGitHub,
    loginWithGoogle,
    handleOAuthCallback,
  };
}
