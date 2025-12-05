"use client";

import { useState, useMemo } from "react";
import { useAllTasks, Task } from "@/hooks/use-tasks";
import { KanbanColumn } from "@/components/tasks/kanban-column";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

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

  const tasksByStatus = useMemo(() => {
    let filteredTasks = tasks;

    if (searchQuery) {
      filteredTasks = filteredTasks.filter(
        (task) =>
          task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          task.description?.toLowerCase().includes(searchQuery.toLowerCase()),
      );
    }

    if (priorityFilter !== "all") {
      filteredTasks = filteredTasks.filter(
        (task) => task.priority === priorityFilter,
      );
    }

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
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-6 border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto animate-fade-in-up">
          <h1 className="text-4xl font-bold text-white mb-2 text-glow">
            Tasks Board
          </h1>
          <p className="text-white/60 text-lg">
            Manage your tasks across all projects
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="px-6 py-4 bg-black/40 border-b border-white/10 backdrop-blur-md sticky top-0 z-30">
        <div
          className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4 animate-fade-in-up"
          style={{ animationDelay: "0.1s" }}
        >
          <div className="flex items-center gap-4 w-full md:w-auto">
            <div className="relative flex-1 md:w-80">
              <Input
                type="text"
                placeholder="Search tasks..."
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

            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="h-10 px-4 rounded-md bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-transparent transition-all duration-200 hover:bg-white/10 cursor-pointer"
            >
              <option value="all" className="bg-black text-white">
                All Priorities
              </option>
              <option value="low" className="bg-black text-white">
                🔵 Low
              </option>
              <option value="medium" className="bg-black text-white">
                🟡 Medium
              </option>
              <option value="high" className="bg-black text-white">
                🔴 High
              </option>
              <option value="urgent" className="bg-black text-white">
                🚨 Urgent
              </option>
            </select>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-white/40 text-sm font-medium">
              {totalTasks} {totalTasks === 1 ? "task" : "tasks"}
            </div>

            <Button className="shadow-[0_0_15px_rgba(124,58,237,0.3)] hover:shadow-[0_0_25px_rgba(124,58,237,0.5)]">
              <span className="mr-2 text-lg">➕</span> New Task
            </Button>
          </div>
        </div>
      </div>

      {/* Board */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden px-6 py-6">
        {isLoading ? (
          <div className="flex gap-6 h-full min-w-max">
            {columns.map((col, i) => (
              <div key={col.status} className="w-80 flex-shrink-0">
                <div className="h-12 rounded-xl bg-white/5 border border-white/10 animate-pulse mb-4" />
                <div className="space-y-3">
                  {[1, 2, 3].map((j) => (
                    <div
                      key={j}
                      className="h-32 rounded-xl bg-white/5 border border-white/10 animate-pulse"
                      style={{ animationDelay: `${(i + j) * 0.1}s` }}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="h-full min-w-max">
            {totalTasks === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center glass-panel p-12 rounded-3xl border-dashed border-white/20">
                  <div className="text-7xl mb-6 filter drop-shadow-[0_0_15px_rgba(255,255,255,0.2)]">
                    📋
                  </div>
                  <h2 className="text-2xl font-bold text-white mb-2">
                    No tasks yet
                  </h2>
                  <p className="text-white/60 mb-8">
                    Create your first task to start organizing your work
                  </p>
                  <Button
                    size="lg"
                    className="shadow-[0_0_20px_rgba(124,58,237,0.3)]"
                  >
                    Create Your First Task
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex gap-6 h-full pb-4">
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
          <div
            className="absolute inset-0 bg-black/80 backdrop-blur-sm animate-fade-in"
            onClick={() => setSelectedTask(null)}
          />
          <Card className="relative z-10 w-full max-w-2xl p-8 bg-black/90 border-white/20 shadow-[0_0_50px_rgba(124,58,237,0.2)] animate-fade-in-up max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between mb-6">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-2xl font-bold text-white text-glow">
                    {selectedTask.title}
                  </h2>
                  <span className="px-2 py-1 rounded-md bg-primary/20 border border-primary/30 text-primary text-xs font-mono">
                    #{selectedTask.id}
                  </span>
                </div>
                {selectedTask.description && (
                  <p className="text-white/60 leading-relaxed">
                    {selectedTask.description}
                  </p>
                )}
              </div>
              <button
                onClick={() => setSelectedTask(null)}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors text-white/60 hover:text-white"
              >
                <svg
                  className="w-6 h-6"
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

            <div className="grid grid-cols-2 gap-6 mb-8 p-6 rounded-xl bg-white/5 border border-white/10">
              <div>
                <label className="text-xs uppercase tracking-wider text-white/40 font-semibold mb-1 block">
                  Status
                </label>
                <span className="inline-flex items-center px-3 py-1 rounded-full bg-white/10 text-white text-sm capitalize border border-white/10">
                  {selectedTask.status.replace("_", " ")}
                </span>
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-white/40 font-semibold mb-1 block">
                  Priority
                </label>
                <span className="inline-flex items-center px-3 py-1 rounded-full bg-white/10 text-white text-sm capitalize border border-white/10">
                  {selectedTask.priority}
                </span>
              </div>
              {selectedTask.due_date && (
                <div className="col-span-2">
                  <label className="text-xs uppercase tracking-wider text-white/40 font-semibold mb-1 block">
                    Due Date
                  </label>
                  <span className="text-white font-mono">
                    {new Date(selectedTask.due_date).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-4 pt-6 border-t border-white/10">
              <Button variant="outline" className="flex-1">
                Edit Task
              </Button>
              <Button onClick={() => setSelectedTask(null)} className="flex-1">
                Close
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
