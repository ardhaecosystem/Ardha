"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useOAuth } from "@/hooks/use-oauth";
import Link from "next/link";

function GoogleCallbackContent() {
  const searchParams = useSearchParams();
  const { handleOAuthCallback } = useOAuth();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const processCallback = async () => {
      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const errorParam = searchParams.get("error");

      // Check for OAuth provider error
      if (errorParam) {
        setError(
          `Google authorization failed: ${errorParam === "access_denied" ? "You denied access" : errorParam}`,
        );
        setIsProcessing(false);
        return;
      }

      // Validate required parameters
      if (!code || !state) {
        setError("Missing authorization code or state parameter");
        setIsProcessing(false);
        return;
      }

      // Process OAuth callback
      const result = await handleOAuthCallback("google", code, state);

      if (!result.success) {
        setError(result.error || "Google authentication failed");
        setIsProcessing(false);
      }
      // If successful, handleOAuthCallback will redirect to dashboard
    };

    processCallback();
  }, [searchParams, handleOAuthCallback]);

  return (
    <div className="min-h-screen w-full relative bg-black flex items-center justify-center p-4">
      {/* Aurora Background */}
      <div
        className="absolute inset-0 z-0"
        style={{
          background: `
            radial-gradient(ellipse 120% 80% at 70% 20%, rgba(255, 20, 147, 0.15), transparent 50%),
            radial-gradient(ellipse 100% 60% at 30% 10%, rgba(0, 255, 255, 0.12), transparent 60%),
            radial-gradient(ellipse 90% 70% at 50% 0%, rgba(138, 43, 226, 0.18), transparent 65%),
            radial-gradient(ellipse 110% 50% at 80% 30%, rgba(255, 215, 0, 0.08), transparent 40%),
            #000000
          `,
        }}
      />

      {/* Content */}
      <div className="relative z-10 w-full max-w-md">
        {/* Glowing Border Effect */}
        <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-pink-500/20 via-purple-500/20 to-cyan-500/20 blur-xl" />

        {/* Main Card */}
        <div className="relative backdrop-blur-xl bg-white/10 rounded-3xl border border-white/20 shadow-2xl p-12 text-center">
          {error ? (
            <>
              {/* Error State */}
              <div className="text-6xl mb-4">❌</div>
              <h1 className="text-2xl font-bold text-white mb-4">
                Authentication Failed
              </h1>
              <p className="text-white/70 mb-8 text-sm leading-relaxed">
                {error}
              </p>
              <Link
                href="/login"
                className="inline-block px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:from-purple-700 hover:to-pink-700 focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition-all duration-200 shadow-lg shadow-purple-500/25"
              >
                Back to Login
              </Link>
            </>
          ) : isProcessing ? (
            <>
              {/* Loading State */}
              <div className="flex justify-center mb-6">
                <div className="relative w-16 h-16">
                  {/* Outer spinning ring */}
                  <div className="absolute inset-0 border-4 border-purple-500/30 rounded-full animate-spin border-t-purple-500"></div>
                  {/* Inner pulsing circle */}
                  <div className="absolute inset-2 bg-purple-500/20 rounded-full animate-pulse"></div>
                </div>
              </div>
              <h1 className="text-2xl font-bold text-white mb-2">
                Authenticating with Google
              </h1>
              <p className="text-white/60 text-sm">
                Please wait while we verify your account...
              </p>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen w-full bg-black flex items-center justify-center">
          <div className="animate-spin w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full"></div>
        </div>
      }
    >
      <GoogleCallbackContent />
    </Suspense>
  );
}
