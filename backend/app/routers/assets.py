from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..db.queries import rate
from ..deps import Services, get_services
from ..schemas.common import JSON
from ..schemas.misc import AssetOut

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=List[AssetOut])
async def list_assets(criticality: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH | CRITICAL"),
                      location_id: Optional[str] = None, svc: Services = Depends(get_services)) -> list:
    """Every inspected asset, most critical first, with action success, anomaly counts and open flags."""
    rows = await svc.repo.list_assets()
    if criticality:
        rows = [r for r in rows if r.get("criticality") == criticality]
    if location_id:
        rows = [r for r in rows if r.get("location_id") == location_id]
    for r in rows:
        r["success_rate_pct"] = rate(r["actions"] - r["failed_actions"], r["actions"])
    return rows


@router.get("/{asset_id}", response_model=JSON)
async def get_asset(asset_id: str, svc: Services = Depends(get_services)) -> dict:
    """One asset: its location, reading history (with quality), anomalies, flags and action success."""
    row = await svc.repo.asset_detail(asset_id)
    if row is None:
        raise HTTPException(404, "no asset %s" % asset_id)
    st = row.get("action_stats") or {}
    row["success_rate_pct"] = rate(st.get("n_success") or 0, st.get("n") or 0)
    return row
