"use client";

import { useAuthStore } from "@/lib/auth-store";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentProjects } from "@/components/dashboard/recent-projects";
import { RecentTasks } from "@/components/dashboard/recent-tasks";
import { Card } from "@/components/ui/card";

export default function DashboardPage() {
  const { user } = useAuthStore();

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Welcome Section - Compact */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">
            Welcome back, {user?.full_name?.split(" ")[0] || "User"}! 👋
          </h1>
          <p className="text-white/60 text-sm">
            Here's what's happening with your projects today.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 h-10 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors text-sm font-medium">
            View Reports
          </button>
          <button className="px-4 py-2 h-10 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 transition-all shadow-lg shadow-purple-500/30 text-sm font-semibold">
            + New Project
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="animate-fade-in-up" style={{ animationDelay: "0.1s" }}>
        <StatsCards />
      </div>

      {/* Two Column Layout */}
      <div
        className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in-up"
        style={{ animationDelay: "0.2s" }}
      >
        {/* Recent Projects */}
        <RecentProjects />

        {/* Recent Tasks */}
        <RecentTasks />
      </div>

      {/* Quick Actions - Enhanced Glass */}
      <div
        className="glass-panel rounded-xl border border-white/10 p-6 animate-fade-in-up"
        style={{ animationDelay: "0.3s" }}
      >
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xl">⚡</span>
          <h2 className="text-lg font-semibold text-white">Quick Actions</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            onClick={() => {
              window.location.href = "/projects/new";
            }}
            className="group relative p-4 rounded-xl glass-panel border border-white/10 hover:bg-white/5 transition-all duration-300 text-left"
          >
            {/* Glow effect */}
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 opacity-0 group-hover:opacity-10 blur-xl transition-opacity duration-300" />

            {/* Content */}
            <div className="relative flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                <span className="text-xl">➕</span>
              </div>
              <div className="flex-1">
                <div className="text-white font-semibold text-sm mb-0.5">
                  New Project
                </div>
                <div className="text-white/60 text-xs">Start a new project</div>
              </div>
              <svg
                className="w-4 h-4 text-white/40 group-hover:text-white/80 group-hover:translate-x-1 transition-all duration-300"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>
          </button>

          <button
            onClick={() => {
              window.location.href = "/chat?mode=research";
            }}
            className="group relative p-4 rounded-xl glass-panel border border-white/10 hover:bg-white/5 transition-all duration-300 text-left"
          >
            {/* Glow effect */}
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 opacity-0 group-hover:opacity-10 blur-xl transition-opacity duration-300" />

            {/* Content */}
            <div className="relative flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                <span className="text-xl">🔬</span>
              </div>
              <div className="flex-1">
                <div className="text-white font-semibold text-sm mb-0.5">
                  AI Research
                </div>
                <div className="text-white/60 text-xs">
                  Start research workflow
                </div>
              </div>
              <svg
                className="w-4 h-4 text-white/40 group-hover:text-white/80 group-hover:translate-x-1 transition-all duration-300"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>
          </button>

          <button
            onClick={() => {
              window.location.href = "/chat";
            }}
            className="group relative p-4 rounded-xl glass-panel border border-white/10 hover:bg-white/5 transition-all duration-300 text-left"
          >
            {/* Glow effect */}
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-pink-500 to-pink-600 opacity-0 group-hover:opacity-10 blur-xl transition-opacity duration-300" />

            {/* Content */}
            <div className="relative flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-pink-500 to-pink-600 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                <span className="text-xl">💬</span>
              </div>
              <div className="flex-1">
                <div className="text-white font-semibold text-sm mb-0.5">
                  New Chat
                </div>
                <div className="text-white/60 text-xs">
                  Chat with AI assistant
                </div>
              </div>
              <svg
                className="w-4 h-4 text-white/40 group-hover:text-white/80 group-hover:translate-x-1 transition-all duration-300"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
