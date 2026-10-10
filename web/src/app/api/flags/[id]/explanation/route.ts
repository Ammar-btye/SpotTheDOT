import { backendRequest } from "@/lib/backend";
import { dashboardFeatures } from "@/lib/features";
import { flagFailure, validFlagId } from "@/lib/flag-route";
import type { FlagExplanation } from "@/lib/flag-detail";

export async function GET(_request: Request, context: RouteContext<"/api/flags/[id]/explanation">) {
  if (!dashboardFeatures().flagExplanations) return Response.json({ error: "Explanations are disabled." }, { status: 404 });
  const { id } = await context.params;
  if (!validFlagId(id)) return Response.json({ error: "Invalid flag." }, { status: 400 });
  try {
    return Response.json(await backendRequest<FlagExplanation>(`/flags/${id}/explain`, {}, 50_000), { headers: { "Cache-Control": "no-store" } });
  } catch (error) { return flagFailure(error); }
}
