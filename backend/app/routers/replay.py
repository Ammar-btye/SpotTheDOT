from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from ..db.pool import DatabaseUnavailable
from ..deps import Services, get_services, require_admin
from ..schemas.misc import ReplayStart, ReplayStatus

# Audit H3: every /replay route needs X-Admin-Token (ADMIN_TOKEN).
router = APIRouter(prefix="/replay", tags=["replay"], dependencies=[Depends(require_admin)])


@router.post("/start", response_model=ReplayStatus)
async def start(body: ReplayStart = ReplayStart(), svc: Services = Depends(get_services)) -> dict:
    """Start streaming the kit's replay.ndjson (KIT_DIR) through the ingest pipeline as a background task.
    Gaps follow the robot's timestamps divided by `speed`, capped at `max_gap_s`. 409 if one is running."""
    if svc.replay.running:
        raise HTTPException(409, "a replay is already running; POST /api/v1/replay/stop first")
    reset_error = None
    if body.reset:
        try:
            await svc.repo.reset_demo(clear_predictions=False)
        except (DatabaseUnavailable, psycopg.Error) as exc:  # the replay still runs (verdicts without storage)
            reset_error = str(exc)
        svc.ref.reset()
    out = await svc.replay.start(speed=body.speed, max_gap_s=body.max_gap_s, missions=body.missions,
                                 start_at=body.start_at, limit=body.limit, triage_mode=body.triage_mode)
    if reset_error:
        out["reset_error"] = reset_error
    return out


@router.post("/stop", response_model=ReplayStatus)
async def stop(svc: Services = Depends(get_services)) -> dict:
    """Stop the running replay (no-op if none). Events already ingested stay."""
    return await svc.replay.stop()


@router.get("/status", response_model=ReplayStatus)
async def status(svc: Services = Depends(get_services)) -> dict:
    """Progress of the current or last replay: sent/total, escalations, flags created, Laya fallbacks, last event."""
    return svc.replay.status()
