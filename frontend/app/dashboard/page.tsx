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
      {/* Welcome Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2 text-glow">
            Welcome back,{" "}
            <span className="text-primary">
              {user?.full_name?.split(" ")[0] || "User"}
            </span>
            ! 👋
          </h1>
          <p className="text-white/60 text-lg">
            Here's what's happening with your projects today.
          </p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors text-sm font-medium">
            View Reports
          </button>
          <button className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 transition-colors text-sm font-medium shadow-[0_0_15px_rgba(124,58,237,0.3)]">
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

      {/* Quick Actions */}
      <Card
        className="p-8 animate-fade-in-up"
        style={{ animationDelay: "0.3s" }}
      >
        <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
          <span className="text-primary">⚡</span> Quick Actions
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <button
            onClick={() => {
              window.location.href = "/projects/new";
            }}
            className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-primary/50 hover:shadow-[0_0_20px_rgba(124,58,237,0.15)] transition-all duration-300 text-left group"
          >
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center text-2xl flex-shrink-0 shadow-lg group-hover:scale-110 transition-transform">
              ➕
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white font-semibold group-hover:text-primary transition-colors">
                New Project
              </div>
              <div className="text-white/60 text-sm">Start a new project</div>
            </div>
          </button>

          <button
            onClick={() => {
              window.location.href = "/chat";
            }}
            className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-primary/50 hover:shadow-[0_0_20px_rgba(124,58,237,0.15)] transition-all duration-300 text-left group"
          >
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-2xl flex-shrink-0 shadow-lg group-hover:scale-110 transition-transform">
              ✨
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white font-semibold group-hover:text-blue-400 transition-colors">
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
            className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-primary/50 hover:shadow-[0_0_20px_rgba(124,58,237,0.15)] transition-all duration-300 text-left group"
          >
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-pink-500 to-rose-500 flex items-center justify-center text-2xl flex-shrink-0 shadow-lg group-hover:scale-110 transition-transform">
              💬
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white font-semibold group-hover:text-pink-400 transition-colors">
                New Chat
              </div>
              <div className="text-white/60 text-sm">
                Chat with AI assistant
              </div>
            </div>
          </button>
        </div>
      </Card>
    </div>
  );
}
