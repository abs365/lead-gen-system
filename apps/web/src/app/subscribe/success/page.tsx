export default function SuccessPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
      <div className="text-center max-w-md">
        <div className="text-6xl mb-6">✅</div>
        <h1 className="text-3xl font-bold mb-4">You're subscribed!</h1>
        <p className="text-gray-400 mb-8">Welcome to LeadGen. You'll start receiving commercial plumbing leads within 24 hours. Reply YES to any email to claim a lead.</p>
        <a href="/" className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-lg">
          Go to Dashboard
        </a>
      </div>
    </div>
  );
}