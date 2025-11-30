"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log error to console
    console.error("Error:", error);
  }, [error]);

  return (
    <div className="min-h-screen w-full bg-black flex items-center justify-center px-6">
      {/* Aurora Background */}
      <div
        className="fixed inset-0 z-0"
        style={{
          background: `
            radial-gradient(ellipse 120% 80% at 70% 20%, rgba(255, 20, 147, 0.08), transparent 50%),
            radial-gradient(ellipse 100% 60% at 30% 10%, rgba(0, 255, 255, 0.06), transparent 60%),
            radial-gradient(ellipse 90% 70% at 50% 0%, rgba(138, 43, 226, 0.10), transparent 65%),
            #000000
          `,
        }}
      />

      {/* Content */}
      <div className="relative z-10 max-w-2xl w-full text-center">
        {/* Glow Effect */}
        <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-red-500/20 to-orange-500/20 blur-3xl" />

        {/* Card */}
        <div className="relative backdrop-blur-xl bg-white/5 rounded-3xl border border-white/10 p-12">
          {/* 500 Number */}
          <div className="text-8xl font-bold mb-6 bg-gradient-to-r from-red-400 to-orange-400 bg-clip-text text-transparent">
            500
          </div>

          {/* Icon */}
          <div className="text-7xl mb-6">⚠️</div>

          {/* Heading */}
          <h1 className="text-4xl font-bold text-white mb-4">
            Something Went Wrong
          </h1>

          {/* Message */}
          <p className="text-white/60 text-lg mb-8 max-w-md mx-auto">
            We're sorry, but something unexpected happened. Our team has been
            notified and is working on it.
          </p>

          {/* Error ID */}
          {error.digest && (
            <div className="mb-8 p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="text-white/40 text-xs mb-1">
                Error ID (for support):
              </div>
              <code className="text-white/80 text-sm font-mono">
                {error.digest}
              </code>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={reset}
              className="w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-200 shadow-lg shadow-purple-500/25"
            >
              Try Again
            </button>
            <Link
              href="/dashboard"
              className="w-full sm:w-auto px-8 py-4 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 text-white font-semibold hover:bg-white/20 transition-all duration-200"
            >
              Go to Dashboard
            </Link>
          </div>

          {/* Support */}
          <div className="mt-12 pt-8 border-t border-white/10">
            <p className="text-white/40 text-sm mb-4">
              Need help? Contact our support team:
            </p>
            <a
              href="mailto:support@ardha.example.com"
              className="text-purple-400 hover:text-purple-300 transition-colors"
            >
              support@ardha.example.com
            </a>
          </div>

          {/* Details Toggle (Development) */}
          {process.env.NODE_ENV === "development" && (
            <details className="mt-8 text-left">
              <summary className="text-white/60 text-sm cursor-pointer hover:text-white transition-colors">
                Show Error Details (Development Only)
              </summary>
              <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                <pre className="text-red-400 text-xs overflow-x-auto">
                  {error.message}
                </pre>
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
