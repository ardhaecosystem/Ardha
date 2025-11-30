"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

export default function NotFound() {
  const router = useRouter();

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
        <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 blur-3xl" />

        {/* Card */}
        <div className="relative backdrop-blur-xl bg-white/5 rounded-3xl border border-white/10 p-12">
          {/* 404 Number */}
          <div className="text-8xl font-bold mb-6 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            404
          </div>

          {/* Icon */}
          <div className="text-7xl mb-6 animate-bounce">🔍</div>

          {/* Heading */}
          <h1 className="text-4xl font-bold text-white mb-4">Page Not Found</h1>

          {/* Message */}
          <p className="text-white/60 text-lg mb-8 max-w-md mx-auto">
            The page you're looking for doesn't exist or has been moved to a new
            location.
          </p>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => router.back()}
              className="w-full sm:w-auto px-8 py-4 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 text-white font-semibold hover:bg-white/20 transition-all duration-200"
            >
              ← Go Back
            </button>
            <Link
              href="/dashboard"
              className="w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-200 shadow-lg shadow-purple-500/25"
            >
              Go to Dashboard →
            </Link>
          </div>

          {/* Helpful Links */}
          <div className="mt-12 pt-8 border-t border-white/10">
            <p className="text-white/40 text-sm mb-4">Helpful Links:</p>
            <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
              <Link
                href="/projects"
                className="text-purple-400 hover:text-purple-300 transition-colors"
              >
                Projects
              </Link>
              <span className="text-white/20">•</span>
              <Link
                href="/tasks"
                className="text-purple-400 hover:text-purple-300 transition-colors"
              >
                Tasks
              </Link>
              <span className="text-white/20">•</span>
              <Link
                href="/chat"
                className="text-purple-400 hover:text-purple-300 transition-colors"
              >
                Chat
              </Link>
              <span className="text-white/20">•</span>
              <Link
                href="/settings"
                className="text-purple-400 hover:text-purple-300 transition-colors"
              >
                Settings
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
