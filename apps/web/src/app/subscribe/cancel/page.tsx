export default function CancelPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
      <div className="text-center max-w-md">
        <div className="text-6xl mb-6">↩️</div>
        <h1 className="text-3xl font-bold mb-4">No problem</h1>
        <p className="text-gray-400 mb-8">Your subscription was not started. Come back anytime when you're ready to receive leads.</p>
        <a href="/subscribe" className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-lg">
          View Plans
        </a>
      </div>
    </div>
  );
}