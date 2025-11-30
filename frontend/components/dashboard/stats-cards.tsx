"use client";

import { useProjectStats } from "@/hooks/use-projects";
import { useTaskStats } from "@/hooks/use-tasks";

export function StatsCards() {
  const { data: projectStats, isLoading: projectsLoading } = useProjectStats();
  const { data: taskStats, isLoading: tasksLoading } = useTaskStats();

  const stats = [
    {
      label: "Active Projects",
      value: projectStats?.total || 0,
      icon: "📁",
      loading: projectsLoading,
    },
    {
      label: "Tasks This Week",
      value: taskStats?.thisWeek || 0,
      icon: "✅",
      loading: tasksLoading,
    },
    {
      label: "AI Conversations",
      value: 0, // TODO: Add chat count endpoint
      icon: "💬",
      loading: false,
    },
    {
      label: "Code Commits",
      value: 0, // TODO: Add commit count endpoint
      icon: "🔨",
      loading: false,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat) => (
        <div key={stat.label} className="relative group">
          {/* Glow Effect */}
          <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

          {/* Card */}
          <div className="relative backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-6 hover:bg-white/10 transition-all duration-300">
            <div className="text-3xl mb-2">{stat.icon}</div>

            {stat.loading ? (
              <div className="h-10 flex items-center">
                <div className="w-12 h-8 bg-white/10 rounded animate-pulse"></div>
              </div>
            ) : (
              <div className="text-3xl font-bold text-white mb-1">
                {stat.value}
              </div>
            )}

            <div className="text-white/60 text-sm">{stat.label}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
