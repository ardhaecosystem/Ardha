"use client";

import { useState } from "react";
import Link from "next/link";
import { useProjects } from "@/lib/hooks/use-projects";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

type ViewMode = "grid" | "list";

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);

  const filteredProjects =
    projects?.filter(
      (project) =>
        project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        project.description?.toLowerCase().includes(searchQuery.toLowerCase()),
    ) || [];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header - Compact */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Projects</h1>
          <p className="text-white/60 text-sm">
            Manage your AI-powered projects and workflows
          </p>
        </div>
        <Button
          onClick={() => setShowCreateModal(true)}
          className="h-10 shadow-lg shadow-purple-500/30 hover:shadow-purple-500/50 transition-all duration-200"
        >
          <span className="mr-1.5 text-base">➕</span> New Project
        </Button>
      </div>

      {/* Toolbar */}
      <div
        className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 animate-fade-in-up"
        style={{ animationDelay: "0.1s" }}
      >
        <div className="relative w-full md:w-96">
          <Input
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-white/5 border-white/10 focus:border-primary/50"
          />
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        <div className="flex items-center gap-1 bg-white/5 p-1 rounded-lg border border-white/10">
          <button
            onClick={() => setViewMode("grid")}
            className={`p-1.5 rounded-md transition-all duration-200 ${
              viewMode === "grid"
                ? "bg-primary/20 text-primary shadow-sm shadow-purple-500/30"
                : "text-white/60 hover:text-white hover:bg-white/10"
            }`}
          >
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
                d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
              />
            </svg>
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={`p-1.5 rounded-md transition-all duration-200 ${
              viewMode === "list"
                ? "bg-primary/20 text-primary shadow-sm shadow-purple-500/30"
                : "text-white/60 hover:text-white hover:bg-white/10"
            }`}
          >
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
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
        {isLoading ? (
          <div
            className={`grid gap-6 ${viewMode === "grid" ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3" : "grid-cols-1"}`}
          >
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="h-48 rounded-2xl bg-white/5 border border-white/10 animate-pulse"
              />
            ))}
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="text-center py-16 glass-panel rounded-2xl border-dashed border-white/20">
            <div className="text-6xl mb-4 animate-float-slow">📁</div>
            <h2 className="text-xl font-bold text-white mb-2">
              {searchQuery ? "No projects found" : "No projects yet"}
            </h2>
            <p className="text-white/60 text-sm mb-6 max-w-md mx-auto">
              {searchQuery
                ? "Try adjusting your search query"
                : "Create your first project to start building with AI"}
            </p>
            {!searchQuery && (
              <Button
                onClick={() => setShowCreateModal(true)}
                className="h-10 shadow-lg shadow-purple-500/30"
              >
                Create Your First Project
              </Button>
            )}
          </div>
        ) : viewMode === "grid" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProjects.map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.slug}`}
                className="group"
              >
                <Card className="h-full p-6 hover:border-primary/50 transition-all duration-300 hover:-translate-y-1 relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                  <div className="relative z-10 flex flex-col h-full">
                    <div className="flex justify-between items-start mb-4">
                      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform duration-300 border border-primary/20">
                        🚀
                      </div>
                      {project.is_private && (
                        <span className="px-2 py-1 rounded-md bg-black/40 border border-white/10 text-white/60 text-xs font-medium backdrop-blur-sm">
                          Private
                        </span>
                      )}
                    </div>

                    <h3 className="text-xl font-bold text-white mb-2 group-hover:text-primary transition-colors line-clamp-1">
                      {project.name}
                    </h3>
                    <p className="text-white/60 text-sm line-clamp-2 mb-6 flex-1">
                      {project.description || "No description provided."}
                    </p>

                    <div className="flex items-center justify-between pt-4 border-t border-white/10 text-xs text-white/40">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <svg
                            className="w-3 h-3"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                            />
                          </svg>
                          0 tasks
                        </span>
                        <span className="flex items-center gap-1">
                          <svg
                            className="w-3 h-3"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                            />
                          </svg>
                          1 member
                        </span>
                      </div>
                      <span>
                        {new Date(project.updated_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredProjects.map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.slug}`}
                className="block group"
              >
                <div className="glass-panel rounded-lg p-3 hover:bg-white/5 hover:border-primary/30 transition-all duration-200 flex items-center gap-4">
                  <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center text-lg border border-primary/20">
                    🚀
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <h3 className="text-base font-semibold text-white group-hover:text-primary transition-colors truncate">
                        {project.name}
                      </h3>
                      {project.is_private && (
                        <span className="px-1.5 py-0.5 rounded bg-black/40 border border-white/10 text-white/50 text-xs font-medium">
                          PRIVATE
                        </span>
                      )}
                    </div>
                    <p className="text-white/50 text-xs truncate">
                      {project.description || "No description"}
                    </p>
                  </div>

                  <div className="flex items-center gap-6 text-xs text-white/40">
                    <div className="flex items-center gap-2">
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
                          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                        />
                      </svg>
                      0 tasks
                    </div>
                    <div className="flex items-center gap-2">
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
                          d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                        />
                      </svg>
                      1 member
                    </div>
                    <div className="w-24 text-right">
                      {new Date(project.updated_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Create Project Modal - Compact */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/80 backdrop-blur-sm animate-fade-in"
            onClick={() => setShowCreateModal(false)}
          />
          <Card className="relative z-10 w-full max-w-lg p-6 bg-black/90 border-white/20 shadow-2xl shadow-purple-500/20 animate-scale-in">
            <h2 className="text-xl font-bold text-white mb-3">
              Create New Project
            </h2>
            <p className="text-white/60 text-sm mb-6">
              Project creation form coming in next update. For now, create
              projects via API.
            </p>
            <div className="flex justify-end">
              <Button
                onClick={() => setShowCreateModal(false)}
                variant="outline"
                className="h-10"
              >
                Close
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
