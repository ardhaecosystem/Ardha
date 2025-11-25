"use client";

import { useAuth } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading, user, logout } = useAuth();
  const router = useRouter();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  // Show loading state while checking authentication
  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Header */}
      <nav className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <h1 className="text-xl font-bold text-gray-900">Ardha Dashboard</h1>
            <div className="hidden md:flex space-x-6">
              <a
                href="/dashboard"
                className="text-gray-700 hover:text-gray-900 font-medium"
              >
                Dashboard
              </a>
              <a
                href="/projects"
                className="text-gray-700 hover:text-gray-900 font-medium"
              >
                Projects
              </a>
              <a
                href="/tasks"
                className="text-gray-700 hover:text-gray-900 font-medium"
              >
                Tasks
              </a>
              <a
                href="/chats"
                className="text-gray-700 hover:text-gray-900 font-medium"
              >
                AI Chat
              </a>
            </div>
          </div>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">
                  {user?.full_name || user?.username}
                </p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
              <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center">
                <span className="text-white text-sm font-medium">
                  {(user?.full_name || user?.username || "U")
                    .charAt(0)
                    .toUpperCase()}
                </span>
              </div>
            </div>

            <button
              onClick={logout}
              className="text-gray-500 hover:text-gray-700 font-medium text-sm"
            >
              Sign out
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="p-6">{children}</main>
    </div>
  );
}
