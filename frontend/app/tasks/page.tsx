"use client";

import { useState, useMemo } from "react";
import { useAllTasks, Task } from "@/hooks/use-tasks";
import { KanbanColumn } from "@/components/tasks/kanban-column";

const columns = [
  { title: "To Do", status: "todo" as const },
  { title: "In Progress", status: "in_progress" as const },
  { title: "In Review", status: "in_review" as const },
  { title: "Done", status: "done" as const },
  { title: "Blocked", status: "blocked" as const },
];

export default function TasksPage() {
  const { data: tasks = [], isLoading } = useAllTasks();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");

  // Group tasks by status
  const tasksByStatus = useMemo(() => {
    let filteredTasks = tasks;

    // Apply search filter
    if (searchQuery) {
      filteredTasks = filteredTasks.filter(
        (task) =>
          task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          task.description?.toLowerCase().includes(searchQuery.toLowerCase()),
      );
    }

    // Apply priority filter
    if (priorityFilter !== "all") {
      filteredTasks = filteredTasks.filter(
        (task) => task.priority === priorityFilter,
      );
    }

    // Group by status
    return columns.reduce(
      (acc, col) => {
        acc[col.status] = filteredTasks.filter(
          (task) => task.status === col.status,
        );
        return acc;
      },
      {} as Record<string, Task[]>,
    );
  }, [tasks, searchQuery, priorityFilter]);

  const totalTasks = tasks.length;

  return (
    <div className="h-full">
      {/* Header */}
      <div className="px-6 py-6 border-b border-white/10">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-4xl font-bold text-white mb-2">Tasks Board</h1>
          <p className="text-white/60 text-lg">
            Manage your tasks across all projects
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="px-6 py-4 bg-black/30 border-b border-white/10">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          {/* Left Side */}
          <div className="flex items-center gap-4 w-full md:w-auto">
            {/* Search */}
            <div className="relative flex-1 md:w-80">
              <input
                type="text"
                placeholder="Search tasks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 pl-10 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-transparent transition-all duration-200"
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

            {/* Priority Filter */}
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-transparent transition-all duration-200 [&>option]:bg-black [&>option]:text-white [&>option]:py-2"
              style={{
                colorScheme: "dark",
              }}
            >
              <option value="all" className="bg-black text-white py-2">
                All Priorities
              </option>
              <option value="low" className="bg-black text-white py-2">
                🔵 Low
              </option>
              <option value="medium" className="bg-black text-white py-2">
                🟡 Medium
              </option>
              <option value="high" className="bg-black text-white py-2">
                🔴 High
              </option>
              <option value="urgent" className="bg-black text-white py-2">
                🚨 Urgent
              </option>
            </select>
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-3">
            {/* Stats */}
            <div className="text-white/60 text-sm">
              {totalTasks} {totalTasks === 1 ? "task" : "tasks"}
            </div>

            {/* Create Task */}
            <button className="flex items-center gap-2 px-6 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-200 shadow-lg shadow-purple-500/25">
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
              <span>New Task</span>
            </button>
          </div>
        </div>
      </div>

      {/* Board */}
      <div className="px-6 py-6 overflow-x-auto">
        {isLoading ? (
          <div className="max-w-7xl mx-auto">
            <div className="flex gap-6">
              {columns.map((col) => (
                <div key={col.status} className="flex-shrink-0 w-80">
                  <div className="h-32 rounded-xl bg-white/5 border border-white/10 animate-pulse mb-4" />
                  <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className="h-32 rounded-xl bg-white/5 border border-white/10 animate-pulse"
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-7xl mx-auto">
            {totalTasks === 0 ? (
              <div className="text-center py-20">
                <div className="text-7xl mb-6">📋</div>
                <h2 className="text-2xl font-bold text-white mb-2">
                  No tasks yet
                </h2>
                <p className="text-white/60 mb-8">
                  Create your first task to start organizing your work
                </p>
                <button className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-200 shadow-lg shadow-purple-500/25">
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
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                  <span>Create Your First Task</span>
                </button>
              </div>
            ) : (
              <div className="flex gap-6 pb-6">
                {columns.map((col) => (
                  <KanbanColumn
                    key={col.status}
                    title={col.title}
                    status={col.status}
                    tasks={tasksByStatus[col.status] || []}
                    onTaskClick={setSelectedTask}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Task Detail Modal */}
      {selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            onClick={() => setSelectedTask(null)}
          />

          {/* Modal */}
          <div className="relative z-10 w-full max-w-2xl backdrop-blur-xl bg-black/90 rounded-2xl border border-white/20 p-8 max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-2xl font-bold text-white">
                    {selectedTask.title}
                  </h2>
                  <span className="px-2 py-1 rounded-lg bg-purple-500/20 text-purple-400 text-xs">
                    #{selectedTask.id}
                  </span>
                </div>
                {selectedTask.description && (
                  <p className="text-white/60">{selectedTask.description}</p>
                )}
              </div>
              <button
                onClick={() => setSelectedTask(null)}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              >
                <svg
                  className="w-5 h-5 text-white/60"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {/* Details */}
            <div className="space-y-4 mb-6">
              <div className="flex items-center gap-4 text-sm">
                <span className="text-white/60">Status:</span>
                <span className="px-3 py-1 rounded-lg bg-white/10 text-white capitalize">
                  {selectedTask.status.replace("_", " ")}
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-white/60">Priority:</span>
                <span className="px-3 py-1 rounded-lg bg-white/10 text-white capitalize">
                  {selectedTask.priority}
                </span>
              </div>
              {selectedTask.due_date && (
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-white/60">Due Date:</span>
                  <span className="text-white">
                    {new Date(selectedTask.due_date).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              <button className="flex-1 px-4 py-2 rounded-lg bg-white/10 text-white hover:bg-white/20 transition-colors">
                Edit
              </button>
              <button
                onClick={() => setSelectedTask(null)}
                className="flex-1 px-4 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold hover:from-purple-700 hover:to-pink-700 transition-all duration-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
