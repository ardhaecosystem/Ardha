"use client";

import { useAuthStore } from "@/lib/auth-store";

export default function DashboardPage() {
  const { user } = useAuthStore();

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Welcome Section */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-2">
          Welcome back, {user?.full_name?.split(" ")[0] || "User"}! 👋
        </h1>
        <p className="text-white/60 text-lg">
          Here's what's happening with your projects today.
        </p>
      </div>

      {/* Stats Grid (Placeholder for Task #5) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {[
          { label: "Active Projects", value: "0", icon: "📁" },
          { label: "Tasks This Week", value: "0", icon: "✅" },
          { label: "AI Conversations", value: "0", icon: "💬" },
          { label: "Code Commits", value: "0", icon: "🔨" },
        ].map((stat) => (
          <div key={stat.label} className="relative group">
            {/* Glow Effect */}
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

            {/* Card */}
            <div className="relative backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-6 hover:bg-white/10 transition-all duration-300">
              <div className="text-3xl mb-2">{stat.icon}</div>
              <div className="text-3xl font-bold text-white mb-1">
                {stat.value}
              </div>
              <div className="text-white/60 text-sm">{stat.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8 mb-8">
        <h2 className="text-2xl font-bold text-white mb-6">Quick Actions</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <button className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200 text-left group">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-2xl">
              ➕
            </div>
            <div>
              <div className="text-white font-semibold group-hover:text-purple-400 transition-colors">
                New Project
              </div>
              <div className="text-white/60 text-sm">Start a new project</div>
            </div>
          </button>

          <button className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200 text-left group">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-2xl">
              ✨
            </div>
            <div>
              <div className="text-white font-semibold group-hover:text-purple-400 transition-colors">
                AI Research
              </div>
              <div className="text-white/60 text-sm">
                Start research workflow
              </div>
            </div>
          </button>

          <button className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200 text-left group">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-2xl">
              💬
            </div>
            <div>
              <div className="text-white font-semibold group-hover:text-purple-400 transition-colors">
                New Chat
              </div>
              <div className="text-white/60 text-sm">
                Chat with AI assistant
              </div>
            </div>
          </button>
        </div>
      </div>

      {/* Coming Soon Notice */}
      <div className="backdrop-blur-xl bg-purple-500/10 rounded-2xl border border-purple-500/20 p-6">
        <div className="flex items-start gap-4">
          <div className="text-3xl">🚀</div>
          <div>
            <h3 className="text-white font-semibold mb-2">
              Dashboard Coming Soon!
            </h3>
            <p className="text-white/80 text-sm">
              The full dashboard with real stats, recent projects, and activity
              timeline will be available in Task #5. For now, use the navigation
              above to explore the app!
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
