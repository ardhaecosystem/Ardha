import { ProtectedRoute } from "@/components/auth/protected-route";
import { Navbar } from "@/components/navigation/navbar";

export default function GitLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen w-full bg-black flex flex-col">
        {/* Aurora Background */}
        <div
          className="fixed inset-0 z-0"
          style={{
            background: `
              radial-gradient(ellipse 120% 80% at 70% 20%, rgba(0, 255, 255, 0.08), transparent 50%),
              radial-gradient(ellipse 100% 60% at 30% 10%, rgba(138, 43, 226, 0.10), transparent 60%),
              #000000
            `,
          }}
        />

        <Navbar />

        <main className="relative z-10 flex-1">{children}</main>
      </div>
    </ProtectedRoute>
  );
}
