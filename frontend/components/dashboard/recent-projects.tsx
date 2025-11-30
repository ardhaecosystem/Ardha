"use client";

import Link from "next/link";
import { useProjects } from "@/hooks/use-projects";

export function RecentProjects() {
  const { data: projects, isLoading } = useProjects();

  const recentProjects = projects?.slice(0, 5) || [];

  if (isLoading) {
    return (
      <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8">
        <h2 className="text-2xl font-bold text-white mb-6">Recent Projects</h2>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 bg-white/5 rounded-xl animate-pulse"
            ></div>
          ))}
        </div>
      </div>
    );
  }

  if (recentProjects.length === 0) {
    return (
      <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8">
        <h2 className="text-2xl font-bold text-white mb-6">Recent Projects</h2>
        <div className="text-center py-12">
          <div className="text-6xl mb-4">📁</div>
          <h3 className="text-white font-semibold mb-2">No projects yet</h3>
          <p className="text-white/60 text-sm mb-6">
            Create your first project to get started
          </p>
          <Link
            href="/projects/new"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-200"
          >
            <span>Create Project</span>
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Recent Projects</h2>
        <Link
          href="/projects"
          className="text-purple-400 hover:text-purple-300 text-sm font-medium transition-colors"
        >
          View all →
        </Link>
      </div>

      <div className="space-y-3">
        {recentProjects.map((project) => (
          <Link
            key={project.id}
            href={`/projects/${project.slug}`}
            className="block p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200 group"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h3 className="text-white font-semibold mb-1 group-hover:text-purple-400 transition-colors">
                  {project.name}
                </h3>
                <p className="text-white/60 text-sm line-clamp-2">
                  {project.description || "No description"}
                </p>
              </div>

              <div className="flex items-center gap-2 ml-4">
                {project.is_private && (
                  <span className="px-2 py-1 rounded-lg bg-white/10 text-white/60 text-xs">
                    Private
                  </span>
                )}
                <svg
                  className="w-5 h-5 text-white/40 group-hover:text-purple-400 transition-colors"
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
            </div>

            <div className="mt-3 text-white/40 text-xs">
              Updated {new Date(project.updated_at).toLocaleDateString()}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
