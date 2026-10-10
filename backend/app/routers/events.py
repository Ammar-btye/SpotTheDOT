from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends, Query

from ..db.queries import encode_cursor
from ..deps import Services, current_request_id, get_services, require_admin
from ..schemas.common import TriageMode
from ..schemas.events import BatchResult, EventBatch, Feed, IngestResult, SpotEvent

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=IngestResult, dependencies=[Depends(require_admin)])
async def ingest_event(event: SpotEvent = Body(...),
                       source: str = Query("api", max_length=60, description="raw.spot_event_log.source"),
                       triage_mode: Optional[TriageMode] = Query(None, description="Override TRIAGE_MODE."),
                       svc: Services = Depends(get_services)) -> dict:
    """Ingest one SPOT event through the 7-step pipeline: raw log -> `events` -> canonical event -> System 1
    (Laya) -> `system1_predictions` -> validator (TRIAGE_MODE) -> `flags` when escalated.

    The response shows every step: Laya's answers, the rules verdict, the combined decision and the flag.
    If System 1 is down the decision is rules-only (`system1.status = laya_unavailable`); if the database is
    down the verdict is still returned with `persisted: false`."""
    rid = current_request_id() or "r-unknown"
    return await svc.pipeline.ingest(event.model_dump(), source=source, request_id=rid, mode=triage_mode)


@router.post("/batch", response_model=BatchResult, dependencies=[Depends(require_admin)])
async def ingest_batch(batch: EventBatch, svc: Services = Depends(get_services)) -> dict:
    """Ingest up to 500 events in order. Each event gets its own request_id (`<request_id>-<n>`) so its rows
    in raw.spot_event_log, app.model_calls and app.request_log tie together."""
    rid = current_request_id() or "r-unknown"
    results = []
    for i, ev in enumerate(batch.events):
        results.append(await svc.pipeline.ingest(ev.model_dump(), source=batch.source, request_id="%s-%03d" % (rid, i),
                                                 mode=batch.triage_mode))
    return {"request_id": rid, "count": len(results),
            "escalated": sum(1 for r in results if (r.get("decision") or {}).get("escalated")),
            "flags_created": sum(1 for r in results if (r.get("flag") or {}).get("created")), "results": results}


@router.get("", response_model=Feed)
async def feed(after: Optional[str] = Query(None, description="Cursor: return events ingested after it (polling)."),
               before: Optional[str] = Query(None, description="Cursor: return events ingested before it (paging)."),
               mission_id: Optional[str] = None, event_type: Optional[str] = None,
               limit: int = Query(50, ge=1, le=500), svc: Services = Depends(get_services)) -> dict:
    """The live event feed, oldest first. First call (no cursor) returns the latest `limit` events; then poll
    with `after=<next_cursor>` to get only new ones. Each item carries its triage summary
    (`payload.triage`) and its flag, if any."""
    rows = await svc.repo.list_events(after=after, before=before, mission_id=mission_id, event_type=event_type,
                                      limit=limit)
    for r in rows:
        r["cursor"] = encode_cursor(r["ingested_at"], r["event_id"])
    return {"items": rows, "next_cursor": rows[-1]["cursor"] if rows else after,
            "prev_cursor": rows[0]["cursor"] if rows else before}
