from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..db.queries import rate, wilson
from ..deps import Services, get_services
from ..schemas.common import JSON
from ..schemas.misc import LocationOut

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=List[LocationOut])
async def list_locations(svc: Services = Depends(get_services)) -> list:
    """Every waypoint with environment, coordinates, action success rate (95% CI), failure types and open
    flags: the data behind the floor-plan heat map."""
    rows = await svc.repo.list_locations()
    for r in rows:
        r["success_rate_pct"] = rate(r["successes"], r["actions"])
        r["ci95_pct"] = list(wilson(r["successes"], r["actions"]))
    return rows


@router.get("/{location_id}", response_model=JSON)
async def get_location(location_id: str, svc: Services = Depends(get_services)) -> dict:
    """One waypoint: its assets, success by action type, failure types, anomalies and flags."""
    row = await svc.repo.location_detail(location_id)
    if row is None:
        raise HTTPException(404, "no location %s" % location_id)
    for r in row.get("by_action_type") or []:
        r["success_rate_pct"] = rate(r["n_success"], r["n"])
    return row
