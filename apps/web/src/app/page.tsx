export const dynamic = "force-dynamic"; // キャッシュを防いで毎回最新のステータスを取る

export default async function Home() {
  const apiBaseUrl =
    process.env.API_INTERNAL_BASE_URL ?? "http://127.0.0.1:8000";

  let apiStatus;
  try {
    const res = await fetch(`${apiBaseUrl}/health`, { cache: "no-store" });
    apiStatus = await res.json();
  } catch {
    apiStatus = { status: "Error", service: "API Not reachable" };
  }

  let dbStatus;
  try {
    const res = await fetch(`${apiBaseUrl}/db/health`, { cache: "no-store" });
    dbStatus = await res.json();
  } catch {
    dbStatus = { status: "Error", database: "DB Not connected" };
  }

  return (
    <main className="min-h-screen p-8 bg-gray-50 text-gray-800">
      <h1 className="text-2xl font-bold mb-6">BOATRACE=LOVE MVP Dashboard</h1>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="p-6 bg-white rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-2 text-blue-600">
            API Status
          </h2>
          <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
            {JSON.stringify(apiStatus, null, 2)}
          </pre>
        </div>

        <div className="p-6 bg-white rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-2 text-green-600">
            Database Status
          </h2>
          <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
            {JSON.stringify(dbStatus, null, 2)}
          </pre>
        </div>
      </div>
    </main>
  );
}
