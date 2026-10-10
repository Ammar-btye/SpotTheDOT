import { loadDashboard } from "@/lib/backend";

export async function GET() {
  try {
    return Response.json(await loadDashboard(), { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    console.error("Dashboard backend request failed", error);
    return Response.json(
      { error: "Cannot reach the dashboard data. Check that the backend is running, then retry." },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}
