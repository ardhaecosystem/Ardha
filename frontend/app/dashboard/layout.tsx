import { ProtectedRoute } from "@/components/auth/protected-route";
import { Navbar } from "@/components/navigation/navbar";
import { Breadcrumbs } from "@/components/navigation/breadcrumbs";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen w-full bg-black text-white selection:bg-primary/30">
        {/* Animated Background */}
        <div className="fixed inset-0 z-0 pointer-events-none">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/10 via-black to-black opacity-50 animate-pulse-glow" />
          <div className="absolute top-0 left-0 w-full h-full bg-[url('/grid.svg')] opacity-10" />
        </div>

        {/* Navigation */}
        <div className="relative z-50">
          <Navbar />
        </div>

        {/* Main Content Area */}
        <div className="relative z-10 flex flex-col min-h-[calc(100vh-64px)]">
          {/* Breadcrumbs */}
          <div className="px-6 py-4 border-b border-white/5 bg-black/20 backdrop-blur-sm">
            <Breadcrumbs />
          </div>

          {/* Page Content */}
          <main className="flex-1 p-6 animate-fade-in">{children}</main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
