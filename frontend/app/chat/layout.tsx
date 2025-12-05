import { ProtectedRoute } from '@/components/auth/protected-route';
import { Navbar } from '@/components/navigation/navbar';

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <div className="h-screen w-full bg-black flex flex-col overflow-hidden">
        {/* Futuristic Cyber Background */}
        <div
          className="fixed inset-0 z-0 pointer-events-none"
          style={{
            background: `
              radial-gradient(ellipse 120% 80% at 70% 20%, rgba(0, 255, 255, 0.08), transparent 50%),
              radial-gradient(ellipse 100% 60% at 30% 10%, rgba(138, 43, 226, 0.10), transparent 60%),
              radial-gradient(ellipse 90% 70% at 50% 0%, rgba(255, 20, 147, 0.08), transparent 65%),
              #000000
            `,
          }}
        />
        
        {/* CRT Scanlines Effect */}
        <div 
          className="fixed inset-0 z-0 pointer-events-none opacity-5"
          style={{
            backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 255, 255, 0.5) 3px)',
            backgroundSize: '100% 4px',
          }}
        />

        {/* Grid Pattern Overlay */}
        <div 
          className="fixed inset-0 z-0 pointer-events-none opacity-[0.03]"
          style={{
            backgroundImage: `
              linear-gradient(rgba(0, 255, 255, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0, 255, 255, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px',
          }}
        />

        {/* Navigation Bar */}
        <div className="relative z-50">
          <Navbar />
        </div>

        {/* Main Chat Content */}
        <main className="relative z-10 flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </ProtectedRoute>
  );
}