"use client";

import Link from "next/link";
import { useProjects } from "@/hooks/use-projects";

export function RecentProjects() {
  const { data: projects, isLoading } = useProjects();

  const recentProjects = projects?.slice(0, 5) || [];

  if (isLoading) {
    return (
      <div className="glass-panel rounded-xl border border-white/10 p-6">
        <h2 className="text-xl font-bold text-white mb-4">Recent Projects</h2>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 bg-white/5 rounded-lg animate-pulse"
            ></div>
          ))}
        </div>
      </div>
    );
  }

  if (recentProjects.length === 0) {
    return (
      <div className="glass-panel rounded-xl border border-white/10 p-6">
        <h2 className="text-xl font-bold text-white mb-4">Recent Projects</h2>
        <div className="text-center py-12">
          <div className="text-5xl mb-3 animate-float-slow">📁</div>
          <h3 className="text-white text-base font-semibold mb-1">
            No projects yet
          </h3>
          <p className="text-white/60 text-sm mb-4">
            Create your first project to get started
          </p>
          <Link
            href="/projects/new"
            className="inline-flex items-center gap-2 px-4 py-2 h-10 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 text-white text-sm font-semibold hover:shadow-lg hover:shadow-purple-500/50 transition-all duration-200"
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
    <div className="glass-panel rounded-xl border border-white/10 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-white">Recent Projects</h2>
        <Link
          href="/projects"
          className="text-purple-400 hover:text-purple-300 text-xs font-medium transition-colors"
        >
          View all →
        </Link>
      </div>

      <div className="space-y-2">
        {recentProjects.map((project) => (
          <Link
            key={project.id}
            href={`/projects/${project.slug}`}
            className="block p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200 group"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h3 className="text-white text-sm font-semibold mb-0.5 group-hover:text-purple-400 transition-colors">
                  {project.name}
                </h3>
                <p className="text-white/60 text-xs line-clamp-1">
                  {project.description || "No description"}
                </p>
              </div>

              <div className="flex items-center gap-2 ml-3">
                {project.is_private && (
                  <span className="px-2 py-0.5 rounded bg-white/10 text-white/60 text-xs">
                    Private
                  </span>
                )}
                <svg
                  className="w-4 h-4 text-white/40 group-hover:text-purple-400 transition-colors"
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

            <div className="mt-2 text-white/40 text-xs">
              Updated {new Date(project.updated_at).toLocaleDateString()}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
