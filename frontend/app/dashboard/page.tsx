"use client";

import { useAuthStore } from "@/lib/auth-store";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentProjects } from "@/components/dashboard/recent-projects";
import { RecentTasks } from "@/components/dashboard/recent-tasks";

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

      {/* Stats Cards */}
      <div className="mb-8">
        <StatsCards />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Recent Projects */}
        <RecentProjects />

        {/* Recent Tasks */}
        <RecentTasks />
      </div>

      {/* Quick Actions */}
      <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8">
        <h2 className="text-2xl font-bold text-white mb-6">Quick Actions</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <button
            onClick={() => {
              window.location.href = "/projects/new";
            }}
            className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200 text-left group"
          >
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-2xl flex-shrink-0">
              ➕
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white font-semibold group-hover:text-purple-400 transition-colors">
                New Project
              </div>
              <div className="text-white/60 text-sm">Start a new project</div>
            </div>
          </button>

          <button
            onClick={() => {
              window.location.href = "/chat";
            }}
            className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200 text-left group"
          >
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-2xl flex-shrink-0">
              ✨
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white font-semibold group-hover:text-purple-400 transition-colors">
                AI Research
              </div>
              <div className="text-white/60 text-sm">
                Start research workflow
              </div>
            </div>
          </button>

          <button
            onClick={() => {
              window.location.href = "/chat";
            }}
            className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200 text-left group"
          >
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-2xl flex-shrink-0">
              💬
            </div>
            <div className="flex-1 min-w-0">
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
    </div>
  );
}
