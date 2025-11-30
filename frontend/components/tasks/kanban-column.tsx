"use client";

import { Task } from "@/hooks/use-tasks";
import { TaskCard } from "./task-card";

interface KanbanColumnProps {
  title: string;
  status: Task["status"];
  tasks: Task[];
  onTaskClick: (task: Task) => void;
}

const statusColors = {
  todo: "from-gray-500/20",
  in_progress: "from-blue-500/20",
  in_review: "from-yellow-500/20",
  done: "from-green-500/20",
  blocked: "from-red-500/20",
};

export function KanbanColumn({
  title,
  status,
  tasks,
  onTaskClick,
}: KanbanColumnProps) {
  return (
    <div className="flex-shrink-0 w-80">
      {/* Column Header */}
      <div className="mb-4">
        <div
          className={`backdrop-blur-xl bg-gradient-to-r ${statusColors[status]} to-transparent rounded-xl border border-white/10 p-4`}
        >
          <div className="flex items-center justify-between">
            <h3 className="text-white font-semibold text-lg">{title}</h3>
            <span className="text-white/60 text-sm">{tasks.length}</span>
          </div>
        </div>
      </div>

      {/* Tasks */}
      <div className="space-y-3 min-h-[400px]">
        {tasks.length === 0 ? (
          <div className="backdrop-blur-xl bg-white/5 rounded-xl border border-white/10 border-dashed p-8 text-center">
            <div className="text-4xl mb-2">✨</div>
            <p className="text-white/40 text-sm">No tasks</p>
          </div>
        ) : (
          tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onClick={() => onTaskClick(task)}
            />
          ))
        )}
      </div>
    </div>
  );
}
