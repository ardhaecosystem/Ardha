export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="text-xl font-bold">Ardha Dashboard</div>
      </nav>
      <main className="p-6">{children}</main>
    </div>
  );
}
