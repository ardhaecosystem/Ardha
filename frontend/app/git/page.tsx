"use client";

import { useState } from "react";
import { useRepository, useCommits, useBranches } from "@/hooks/use-git";

export default function GitPage() {
  const [selectedProjectId] = useState<number | null>(1); // TODO: Get from projects
  const [selectedBranch, setSelectedBranch] = useState<string>("main");

  const { data: repository, isLoading: repoLoading } =
    useRepository(selectedProjectId);
  const { data: commits = [], isLoading: commitsLoading } = useCommits(
    selectedProjectId,
    selectedBranch,
  );
  const { data: branches = [], isLoading: branchesLoading } =
    useBranches(selectedProjectId);

  const handleCopyUrl = () => {
    if (repository?.url) {
      navigator.clipboard.writeText(repository.url);
    }
  };

  if (repoLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-neon-blue/30 border-t-neon-blue rounded-full animate-spin" />
      </div>
    );
  }

  if (!repository) {
    return (
      <div className="min-h-screen p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🔗</div>
          <h3 className="text-xl font-semibold text-white mb-2">
            No repository connected
          </h3>
          <p className="text-white/60 text-sm mb-6">
            Connect a Git repository to start tracking changes
          </p>
          <button className="px-6 py-3 rounded-lg bg-gradient-to-r from-neon-purple to-neon-pink text-white font-semibold hover:shadow-lg hover:shadow-neon-purple/50 transition-all duration-200">
            Connect Repository
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white mb-1">
            Git Integration
          </h1>
          <p className="text-white/60">View repository commits and branches</p>
        </div>

        {/* Repository Info */}
        <div className="glass-panel rounded-xl border border-white/10 p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-white mb-1">
                {repository.name}
              </h2>
              <p className="text-white/60 text-sm">
                {repository.description || "No description"}
              </p>
            </div>
            <button
              onClick={handleCopyUrl}
              className="px-4 py-2 rounded-lg glass-panel border border-white/10 text-white hover:bg-white/10 transition-all duration-200 text-sm flex items-center gap-2"
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
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
              <span>Clone URL</span>
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="glass-panel rounded-lg p-3 border border-white/10">
              <div className="text-white/60 text-xs mb-1">Commits</div>
              <div className="text-2xl font-bold text-white">
                {commits.length}
              </div>
            </div>
            <div className="glass-panel rounded-lg p-3 border border-white/10">
              <div className="text-white/60 text-xs mb-1">Branches</div>
              <div className="text-2xl font-bold text-white">
                {branches.length}
              </div>
            </div>
            <div className="glass-panel rounded-lg p-3 border border-white/10">
              <div className="text-white/60 text-xs mb-1">Default Branch</div>
              <div className="text-lg font-bold text-neon-blue">
                {repository.default_branch}
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Commits */}
          <div className="lg:col-span-2">
            <div className="glass-panel rounded-xl border border-white/10 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-white">Recent Commits</h3>
                <select
                  value={selectedBranch}
                  onChange={(e) => setSelectedBranch(e.target.value)}
                  className="px-3 py-1.5 rounded-lg glass-panel border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-neon-blue/50"
                >
                  {branches.map((branch) => (
                    <option key={branch.name} value={branch.name}>
                      {branch.name}
                    </option>
                  ))}
                </select>
              </div>

              {commitsLoading ? (
                <div className="text-center py-8">
                  <div className="inline-block w-8 h-8 border-4 border-neon-blue/30 border-t-neon-blue rounded-full animate-spin" />
                </div>
              ) : commits.length === 0 ? (
                <div className="text-center py-8">
                  <div className="text-4xl mb-2">📝</div>
                  <p className="text-white/60 text-sm">No commits yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {commits.map((commit) => (
                    <div
                      key={commit.hash}
                      className="glass-panel rounded-lg p-4 border border-white/10 hover:bg-white/5 transition-all duration-200"
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-2 h-2 rounded-full bg-neon-blue mt-2" />
                        <div className="flex-1">
                          <div className="text-white font-medium text-sm mb-1">
                            {commit.message}
                          </div>
                          <div className="flex items-center gap-3 text-white/60 text-xs">
                            <span>{commit.author}</span>
                            <span>•</span>
                            <span>
                              {new Date(commit.date).toLocaleDateString()}
                            </span>
                            <span>•</span>
                            <span className="font-mono">
                              {commit.hash.substring(0, 7)}
                            </span>
                            <span>•</span>
                            <span>{commit.files_changed} files</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Branches */}
          <div>
            <div className="glass-panel rounded-xl border border-white/10 p-6">
              <h3 className="text-xl font-bold text-white mb-4">Branches</h3>

              {branchesLoading ? (
                <div className="text-center py-8">
                  <div className="inline-block w-8 h-8 border-4 border-neon-blue/30 border-t-neon-blue rounded-full animate-spin" />
                </div>
              ) : (
                <div className="space-y-2">
                  {branches.map((branch) => (
                    <button
                      key={branch.name}
                      onClick={() => setSelectedBranch(branch.name)}
                      className={`w-full p-3 rounded-lg text-left transition-all duration-200 ${
                        selectedBranch === branch.name
                          ? "bg-neon-blue/20 border border-neon-blue/50"
                          : "glass-panel border border-white/10 hover:bg-white/5"
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <svg
                          className="w-4 h-4 text-neon-blue"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"
                          />
                        </svg>
                        <span className="text-white font-medium text-sm">
                          {branch.name}
                        </span>
                      </div>
                      <div className="text-white/60 text-xs ml-6">
                        Last commit:{" "}
                        {new Date(branch.last_commit_date).toLocaleDateString()}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
