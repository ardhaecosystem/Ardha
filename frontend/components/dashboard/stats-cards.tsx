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
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, index) => (
        <div
          key={stat.label}
          className="relative group animate-in fade-in slide-in-from-bottom-2"
          style={{ animationDelay: `${index * 0.1}s` }}
        >
          {/* Glow Effect */}
          <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

          {/* Card - Compact */}
          <div className="relative glass-panel rounded-xl border border-white/10 p-4 hover:bg-white/10 transition-all duration-300">
            <div className="text-2xl mb-2">{stat.icon}</div>

            {stat.loading ? (
              <div className="h-8 flex items-center">
                <div className="w-10 h-6 bg-white/10 rounded animate-pulse"></div>
              </div>
            ) : (
              <div className="text-2xl font-bold text-white mb-0.5">
                {stat.value}
              </div>
            )}

            <div className="text-white/60 text-xs">{stat.label}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
