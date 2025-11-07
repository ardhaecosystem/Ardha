export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-purple-50 to-white">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <h1 className="text-6xl font-bold text-gray-900 mb-6">
            Welcome to <span className="text-purple-600">Ardha</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            AI-Powered Development Platform - Unified workspace for AI-assisted software development
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-16">
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold mb-2">Research Mode</h3>
              <p className="text-gray-600">Market research and idea validation</p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold mb-2">Architect Mode</h3>
              <p className="text-gray-600">System design and architecture decisions</p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-lg font-semibold mb-2">Implementation Mode</h3>
              <p className="text-gray-600">Code generation and debugging</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}