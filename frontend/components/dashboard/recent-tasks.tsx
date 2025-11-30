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
      <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8">
        <h2 className="text-2xl font-bold text-white mb-6">Recent Tasks</h2>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-16 bg-white/5 rounded-xl animate-pulse"
            ></div>
          ))}
        </div>
      </div>
    );
  }

  if (!tasks || tasks.length === 0) {
    return (
      <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8">
        <h2 className="text-2xl font-bold text-white mb-6">Recent Tasks</h2>
        <div className="text-center py-12">
          <div className="text-6xl mb-4">✅</div>
          <h3 className="text-white font-semibold mb-2">No tasks yet</h3>
          <p className="text-white/60 text-sm">
            Tasks will appear here once you create them
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="backdrop-blur-xl bg-white/5 rounded-2xl border border-white/10 p-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Recent Tasks</h2>
        <Link
          href="/tasks"
          className="text-purple-400 hover:text-purple-300 text-sm font-medium transition-colors"
        >
          View all →
        </Link>
      </div>

      <div className="space-y-3">
        {tasks.map((task) => (
          <div
            key={task.id}
            className="p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all duration-200"
          >
            <div className="flex items-start gap-3">
              {/* Priority Icon */}
              <div className="text-xl mt-0.5">
                {priorityIcons[task.priority as keyof typeof priorityIcons] ||
                  "⚪"}
              </div>

              {/* Task Info */}
              <div className="flex-1 min-w-0">
                <h3 className="text-white font-medium mb-1 line-clamp-1">
                  {task.title}
                </h3>
                {task.description && (
                  <p className="text-white/60 text-sm line-clamp-1">
                    {task.description}
                  </p>
                )}
                <div className="flex items-center gap-3 mt-2">
                  {/* Status Badge */}
                  <span
                    className={`px-2 py-1 rounded-lg text-xs font-medium ${
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
