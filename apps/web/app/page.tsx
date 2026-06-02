export default function Home() {
  return (
    <main className="min-h-screen bg-gray-950 text-white">
      <section className="mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center px-6 text-center">
        <p className="mb-4 rounded-full border border-gray-700 px-4 py-2 text-sm text-gray-300">
          FlowState
        </p>

        <h1 className="mb-6 text-5xl font-bold tracking-tight">
          Track your job applications automatically.
        </h1>

        <p className="mb-8 max-w-2xl text-lg text-gray-400">
          FlowState connects to Gmail, detects job application updates, and
          organizes your recruiting progress into one clean dashboard.
        </p>

        <div className="flex gap-4">
          <button className="rounded-lg bg-white px-5 py-3 font-medium text-gray-950">
            Get Started
          </button>

          <button className="rounded-lg border border-gray-700 px-5 py-3 font-medium text-gray-200">
            View Dashboard
          </button>
        </div>
      </section>
    </main>
  );
}