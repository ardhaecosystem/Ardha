"use client";

import { Task } from "@/hooks/use-tasks";

interface TaskCardProps {
  task: Task;
  onClick?: () => void;
}

const priorityConfig = {
  low: { icon: "🔵", color: "text-blue-400" },
  medium: { icon: "🟡", color: "text-yellow-400" },
  high: { icon: "🔴", color: "text-red-400" },
  urgent: { icon: "🚨", color: "text-red-500" },
};

export function TaskCard({ task, onClick }: TaskCardProps) {
  const priority = priorityConfig[task.priority];

  return (
    <div onClick={onClick} className="group relative cursor-pointer">
      {/* Glow Effect */}
      <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

      {/* Card */}
      <div className="relative backdrop-blur-xl bg-white/5 rounded-xl border border-white/10 p-4 hover:bg-white/10 hover:border-purple-500/50 transition-all duration-200">
        {/* Priority & ID */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-lg">{priority.icon}</span>
          <span className="text-xs text-white/40">#{task.id}</span>
        </div>

        {/* Title */}
        <h4 className="text-white font-semibold mb-2 line-clamp-2 group-hover:text-purple-400 transition-colors">
          {task.title}
        </h4>

        {/* Description */}
        {task.description && (
          <p className="text-white/60 text-sm line-clamp-2 mb-3">
            {task.description}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-white/40">
          {/* Due Date */}
          {task.due_date && (
            <div className="flex items-center gap-1">
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
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <span>{new Date(task.due_date).toLocaleDateString()}</span>
            </div>
          )}

          {/* Assignee Placeholder */}
          {task.assigned_to && (
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-xs font-bold">
              {task.assigned_to.toString().charAt(0)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
