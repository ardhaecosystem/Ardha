"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useProject } from "@/lib/hooks/use-projects";

type Tab = "overview" | "tasks" | "activity" | "settings";

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params.slug as string;
  const { data: project, isLoading } = useProject(slug);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="h-32 rounded-2xl bg-white/5 border border-white/10 animate-pulse mb-8" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-32 rounded-2xl bg-white/5 border border-white/10 animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="text-center py-20">
          <div className="text-7xl mb-6">❌</div>
          <h2 className="text-2xl font-bold text-white mb-2">
            Project Not Found
          </h2>
          <p className="text-white/60 mb-8">
            The project you're looking for doesn't exist or you don't have
            access to it.
          </p>
          <button
            onClick={() => router.push("/projects")}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-200"
          >
            ← Back to Projects
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8 mb-8">
        <div className="flex items-start justify-between mb-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-4xl font-bold text-white">{project.name}</h1>
              {project.is_private && (
                <span className="px-3 py-1 rounded-lg bg-white/10 text-white/60 text-sm">
                  Private
                </span>
              )}
            </div>
            <p className="text-white/60 text-lg">
              {project.description || "No description provided"}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 ml-6">
            <button className="p-2 rounded-lg bg-white/5 border border-white/10 text-white/60 hover:text-white hover:bg-white/10 transition-all duration-200">
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
            </button>
            <button className="p-2 rounded-lg bg-white/5 border border-white/10 text-white/60 hover:text-white hover:bg-white/10 transition-all duration-200">
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2 border-t border-white/10 pt-6">
          {(["overview", "tasks", "activity", "settings"] as Tab[]).map(
            (tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-lg font-medium capitalize transition-all duration-200 ${
                  activeTab === tab
                    ? "bg-purple-500/20 text-purple-400"
                    : "text-white/60 hover:text-white hover:bg-white/10"
                }`}
              >
                {tab}
              </button>
            ),
          )}
        </div>
      </div>

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <>
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {[
              { label: "Total Tasks", value: 0, icon: "✅" },
              { label: "Active Members", value: 1, icon: "👥" },
              { label: "Recent Activity", value: 0, icon: "⚡" },
            ].map((stat) => (
              <div key={stat.label} className="relative group">
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                <div className="relative backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-6">
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
          <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8">
            <h2 className="text-2xl font-bold text-white mb-6">
              Quick Actions
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200 text-left group">
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-2xl flex-shrink-0">
                  ✅
                </div>
                <div>
                  <div className="text-white font-semibold group-hover:text-purple-400 transition-colors">
                    Create Task
                  </div>
                  <div className="text-white/60 text-sm">Add a new task</div>
                </div>
              </button>

              <button className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200 text-left group">
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-2xl flex-shrink-0">
                  👥
                </div>
                <div>
                  <div className="text-white font-semibold group-hover:text-purple-400 transition-colors">
                    Add Member
                  </div>
                  <div className="text-white/60 text-sm">
                    Invite collaborators
                  </div>
                </div>
              </button>

              <button className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200 text-left group">
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-2xl flex-shrink-0">
                  💬
                </div>
                <div>
                  <div className="text-white font-semibold group-hover:text-purple-400 transition-colors">
                    AI Chat
                  </div>
                  <div className="text-white/60 text-sm">
                    Start AI conversation
                  </div>
                </div>
              </button>
            </div>
          </div>
        </>
      )}

      {/* Other Tabs - Placeholder */}
      {activeTab !== "overview" && (
        <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-12 text-center">
          <div className="text-6xl mb-4">🚧</div>
          <h3 className="text-xl font-bold text-white mb-2 capitalize">
            {activeTab} Coming Soon
          </h3>
          <p className="text-white/60">
            This section will be implemented in the next update.
          </p>
        </div>
      )}
    </div>
  );
}
