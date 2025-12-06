"use client";

import Link from "next/link";
import { useRecentTasks } from "@/hooks/use-tasks";

const statusColors = {
  todo: "bg-gray-500/20 text-gray-300",
  in_progress: "bg-blue-500/20 text-blue-300",
  in_review: "bg-yellow-500/20 text-yellow-300",
  done: "bg-green-500/20 text-green-300",
  blocked: "bg-red-500/20 text-red-300",
};

const priorityIcons = {
  low: "🔵",
  medium: "🟡",
  high: "🔴",
  urgent: "🚨",
};

export function RecentTasks() {
  const { data: tasks, isLoading } = useRecentTasks(10);

  if (isLoading) {
    return (
      <div className="glass-panel rounded-xl border border-white/10 p-6">
        <h2 className="text-xl font-bold text-white mb-4">Recent Tasks</h2>
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-14 bg-white/5 rounded-lg animate-pulse"
            ></div>
          ))}
        </div>
      </div>
    );
  }

  if (!tasks || tasks.length === 0) {
    return (
      <div className="glass-panel rounded-xl border border-white/10 p-6">
        <h2 className="text-xl font-bold text-white mb-4">Recent Tasks</h2>
        <div className="text-center py-12">
          <div className="text-5xl mb-3 animate-float-slow">✅</div>
          <h3 className="text-white text-base font-semibold mb-1">
            No tasks yet
          </h3>
          <p className="text-white/60 text-sm">
            Tasks will appear here once you create them
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-xl border border-white/10 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-white">Recent Tasks</h2>
        <Link
          href="/tasks"
          className="text-purple-400 hover:text-purple-300 text-xs font-medium transition-colors"
        >
          View all →
        </Link>
      </div>

      <div className="space-y-2">
        {tasks.map((task) => (
          <div
            key={task.id}
            className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-all duration-200"
          >
            <div className="flex items-start gap-2">
              {/* Priority Icon */}
              <div className="text-base mt-0.5">
                {priorityIcons[task.priority as keyof typeof priorityIcons] ||
                  "⚪"}
              </div>

              {/* Task Info */}
              <div className="flex-1 min-w-0">
                <h3 className="text-white text-sm font-medium mb-0.5 line-clamp-1">
                  {task.title}
                </h3>
                {task.description && (
                  <p className="text-white/60 text-xs line-clamp-1 mb-1.5">
                    {task.description}
                  </p>
                )}
                <div className="flex items-center gap-2">
                  {/* Status Badge */}
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      statusColors[task.status as keyof typeof statusColors] ||
                      "bg-gray-500/20 text-gray-300"
                    }`}
                  >
                    {task.status.replace("_", " ")}
                  </span>

                  {/* Due Date */}
                  {task.due_date && (
                    <span className="text-white/40 text-xs">
                      Due {new Date(task.due_date).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
