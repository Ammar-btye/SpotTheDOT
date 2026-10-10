from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..db.queries import DIMENSIONS
from ..deps import Services, get_services
from ..schemas.misc import Overview, Reliability
from ..services.analytics import overview_cards

router = APIRouter(prefix="/insights", tags=["insights"])
SMALL_SAMPLE_N = 20


@router.get("/overview", response_model=Overview)
async def overview(svc: Services = Depends(get_services)) -> dict:
    """The Overview page's headline insights, computed live from the database, each with a one-line pitch:
    green-but-broken missions, the battery cliff, V1 vs V2 at matched battery, worst waypoints, inspection
    reliability, repeat-offender assets, questionable readings, and live triage routing."""
    o = await svc.repo.overview()
    return {"insights": overview_cards(o), "stored_insights": o.get("stored") or [],
            "generated_at": dt.datetime.now(dt.timezone.utc)}


@router.get("/reliability", response_model=Reliability)
async def reliability(group_by: Optional[str] = Query("location_id", description="|".join(DIMENSIONS)),
                      action_type: Optional[str] = None, location_id: Optional[str] = None,
                      configuration_version: Optional[str] = None,
                      battery_band: Optional[str] = Query(None, description="<=25 | 26-40 | 41-60 | 61-80 | 81+"),
                      environment: Optional[str] = None,
                      min_battery: Optional[int] = Query(None, description="Only actions with battery > this."),
                      svc: Services = Depends(get_services)) -> dict:
    """Action success rate with a 95% Wilson interval, grouped by one dimension and filtered by any others.
    E.g. `group_by=configuration_version&min_battery=40` is the V1-vs-V2 comparison at matched battery.
    Groups with n < 20 carry a small-sample warning."""
    filters = {"action_type": action_type, "location_id": location_id,
               "configuration_version": configuration_version, "battery_band": battery_band,
               "environment": environment, "min_battery": min_battery}
    rows = await svc.repo.reliability(group_by, filters)
    out = []
    for r in rows:
        item = {"group": r["grp"], "n": r["n"], "n_success": r["n_success"],
                "success_rate_pct": r["success_rate_pct"], "ci95_pct": r["ci95_pct"],
                "mean_battery": r.get("mean_battery")}
        if r["n"] < SMALL_SAMPLE_N:
            item["warning"] = "small sample (n=%d < %d): indicative only" % (r["n"], SMALL_SAMPLE_N)
        out.append(item)
    return {"group_by": group_by, "filters": {k: v for k, v in filters.items() if v is not None}, "rows": out}
