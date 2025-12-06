"use client";

import { useState } from "react";
import { useFiles, useUploadFile, useDeleteFile } from "@/hooks/use-files";

type ViewMode = "grid" | "list";
type SortBy = "name" | "date" | "size" | "type";

export default function FilesPage() {
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(1); // TODO: Get from projects
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [sortBy, setSortBy] = useState<SortBy>("date");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFile, setSelectedFile] = useState<any>(null);

  const { data: files = [], isLoading } = useFiles(selectedProjectId);
  const uploadFile = useUploadFile();
  const deleteFile = useDeleteFile();

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedProjectId) return;

    try {
      await uploadFile.mutateAsync({ projectId: selectedProjectId, file });
    } catch (error) {
      console.error("Upload failed:", error);
    }
  };

  const handleDelete = async (fileId: number) => {
    if (!selectedProjectId || !confirm("Delete this file?")) return;

    try {
      await deleteFile.mutateAsync({ projectId: selectedProjectId, fileId });
    } catch (error) {
      console.error("Delete failed:", error);
    }
  };

  // Filter and sort files
  const filteredFiles = files
    .filter((file) =>
      file.name.toLowerCase().includes(searchQuery.toLowerCase()),
    )
    .sort((a, b) => {
      switch (sortBy) {
        case "name":
          return a.name.localeCompare(b.name);
        case "date":
          return (
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          );
        case "size":
          return b.size - a.size;
        case "type":
          return a.type.localeCompare(b.type);
        default:
          return 0;
      }
    });

  // File type icons
  const getFileIcon = (type: string) => {
    if (type.includes("image")) return "🖼️";
    if (type.includes("pdf")) return "📄";
    if (type.includes("video")) return "🎥";
    if (type.includes("audio")) return "🎵";
    if (type.includes("zip") || type.includes("archive")) return "📦";
    if (type.includes("text") || type.includes("code")) return "📝";
    return "📎";
  };

  // Format file size
  const formatSize = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white mb-1">Files</h1>
          <p className="text-white/60">
            Manage your project files and documents
          </p>
        </div>

        {/* Toolbar */}
        <div className="glass-panel rounded-xl border border-white/10 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search files..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full px-4 py-2 pl-10 rounded-lg glass-panel border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-neon-blue/50 text-sm"
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
            </div>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortBy)}
              className="px-4 py-2 rounded-lg glass-panel border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-neon-blue/50"
            >
              <option value="date">Sort by Date</option>
              <option value="name">Sort by Name</option>
              <option value="size">Sort by Size</option>
              <option value="type">Sort by Type</option>
            </select>

            {/* View Toggle */}
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode("grid")}
                className={`p-2 rounded-lg transition-all duration-200 ${
                  viewMode === "grid"
                    ? "bg-neon-blue/20 text-neon-blue"
                    : "glass-panel text-white/60 hover:text-white"
                }`}
              >
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
                    d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
                  />
                </svg>
              </button>
              <button
                onClick={() => setViewMode("list")}
                className={`p-2 rounded-lg transition-all duration-200 ${
                  viewMode === "list"
                    ? "bg-neon-blue/20 text-neon-blue"
                    : "glass-panel text-white/60 hover:text-white"
                }`}
              >
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
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              </button>
            </div>

            {/* Upload Button */}
            <label className="px-4 py-2 rounded-lg bg-gradient-to-r from-neon-purple to-neon-pink text-white font-semibold hover:shadow-lg hover:shadow-neon-purple/50 transition-all duration-200 cursor-pointer text-sm flex items-center gap-2">
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
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <span>Upload</span>
              <input
                type="file"
                onChange={handleFileUpload}
                className="hidden"
                disabled={uploadFile.isPending}
              />
            </label>
          </div>
        </div>

        {/* Files Content */}
        {isLoading ? (
          <div className="text-center py-20">
            <div className="inline-block w-12 h-12 border-4 border-neon-blue/30 border-t-neon-blue rounded-full animate-spin" />
          </div>
        ) : filteredFiles.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-6xl mb-4 animate-float-slow">📁</div>
            <h3 className="text-xl font-semibold text-white mb-2">
              No files yet
            </h3>
            <p className="text-white/60 text-sm mb-6">
              Upload your first file to get started
            </p>
            <label className="inline-block px-6 py-3 rounded-lg bg-gradient-to-r from-neon-purple to-neon-pink text-white font-semibold hover:shadow-lg hover:shadow-neon-purple/50 transition-all duration-200 cursor-pointer">
              Upload File
              <input
                type="file"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>
        ) : (
          <>
            {/* Grid View */}
            {viewMode === "grid" && (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {filteredFiles.map((file) => (
                  <div
                    key={file.id}
                    className="group relative glass-panel rounded-xl border border-white/10 p-4 hover:bg-white/5 transition-all duration-300 cursor-pointer"
                    onClick={() => setSelectedFile(file)}
                  >
                    {/* File Icon */}
                    <div className="text-5xl mb-3 text-center group-hover:scale-110 transition-transform duration-300">
                      {getFileIcon(file.type)}
                    </div>

                    {/* File Name */}
                    <div className="text-white text-sm font-medium mb-1 line-clamp-2 text-center">
                      {file.name}
                    </div>

                    {/* File Size */}
                    <div className="text-white/40 text-xs text-center">
                      {formatSize(file.size)}
                    </div>

                    {/* Delete Button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(file.id);
                      }}
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 transition-all duration-200"
                    >
                      <svg
                        className="w-3.5 h-3.5 text-red-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* List View */}
            {viewMode === "list" && (
              <div className="glass-panel rounded-xl border border-white/10 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-white/5 border-b border-white/10">
                    <tr>
                      <th className="px-4 py-3 text-left text-white/80 text-sm font-semibold">
                        Name
                      </th>
                      <th className="px-4 py-3 text-left text-white/80 text-sm font-semibold">
                        Size
                      </th>
                      <th className="px-4 py-3 text-left text-white/80 text-sm font-semibold">
                        Type
                      </th>
                      <th className="px-4 py-3 text-left text-white/80 text-sm font-semibold">
                        Date
                      </th>
                      <th className="px-4 py-3 text-right text-white/80 text-sm font-semibold">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredFiles.map((file) => (
                      <tr
                        key={file.id}
                        className="border-b border-white/5 hover:bg-white/5 transition-all duration-200 cursor-pointer"
                        onClick={() => setSelectedFile(file)}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <span className="text-2xl">
                              {getFileIcon(file.type)}
                            </span>
                            <span className="text-white text-sm font-medium">
                              {file.name}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-white/60 text-sm">
                          {formatSize(file.size)}
                        </td>
                        <td className="px-4 py-3 text-white/60 text-sm">
                          {file.type}
                        </td>
                        <td className="px-4 py-3 text-white/60 text-sm">
                          {new Date(file.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDelete(file.id);
                            }}
                            className="p-1.5 rounded-lg hover:bg-red-500/20 transition-all duration-200"
                          >
                            <svg
                              className="w-4 h-4 text-red-400"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                              />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
