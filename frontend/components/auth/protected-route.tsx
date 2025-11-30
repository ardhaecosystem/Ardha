"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, accessToken, user } = useAuthStore();

  useEffect(() => {
    // Check authentication on mount and route change
    const isAuth = isAuthenticated && accessToken && user;

    if (!isAuth) {
      // Store intended destination
      sessionStorage.setItem("redirectAfterLogin", pathname);

      // Redirect to login
      router.push("/login");
    }
  }, [pathname, isAuthenticated, accessToken, user, router]);

  // Show loading spinner while checking auth (prevents flash of protected content)
  if (!isAuthenticated || !accessToken || !user) {
    return (
      <div className="min-h-screen w-full bg-black flex items-center justify-center">
        <div className="animate-spin w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return <>{children}</>;
}
