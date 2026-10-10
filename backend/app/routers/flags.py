from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from ..deps import Services, current_request_id, get_services
from ..schemas.flags import AckIn, AckOut, ContextPacket, Explanation, FlagDetail, FlagList

router = APIRouter(prefix="/flags", tags=["flags"])
FlagId = Path(..., ge=1, description="flags.flag_id")


@router.get("", response_model=FlagList)
async def list_flags(status: Optional[str] = Query(None, description="OPEN | ACKNOWLEDGED | RESOLVED"),
                     escalated: Optional[bool] = Query(True, description="Default: escalated flags only."),
                     severity: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH | CRITICAL"),
                     mission_id: Optional[str] = None, asset_id: Optional[str] = None,
                     location_id: Optional[str] = None,
                     limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                     svc: Services = Depends(get_services)) -> dict:
    """The operator queue: open flags first, then by score (priority x confidence), newest first."""
    rows, total = await svc.repo.list_flags(status=status, escalated=escalated, severity=severity,
                                            mission_id=mission_id, asset_id=asset_id, location_id=location_id,
                                            limit=limit, offset=offset)
    return {"items": rows, "page": {"total": total, "limit": limit, "offset": offset}}


@router.get("/{flag_id}", response_model=FlagDetail)
async def get_flag(flag_id: int = FlagId, svc: Services = Depends(get_services)) -> dict:
    """One flag with its event (enriched payload + triage summary), operator acks, System 2 assessment and
    Laya's stored answers."""
    row = await svc.flags.load(flag_id)
    f = row["flag"]
    preds = await svc.repo.predictions(f.get("action_id"), f.get("mission_id"))
    return {"flag": f, "event": row.get("event"), "acks": row.get("acks") or [], "assessment": row.get("assessment"),
            "system1": preds}


@router.get("/{flag_id}/context", response_model=ContextPacket, response_model_exclude_none=True)
async def context(flag_id: int = FlagId, svc: Services = Depends(get_services)) -> dict:
    """The context packet System 2 reads, from the MCP server's `get_flag_context` (RAG over pgvector + SQL).
    If the MCP server is down, a SQL-built minimal packet (`source: sql_fallback`) with the flag, the event,
    Laya's answers, waypoint/battery reliability and the asset's history."""
    return await svc.flags.context(flag_id, current_request_id())


@router.post("/{flag_id}/explain", response_model=Explanation, response_model_exclude_none=True)
async def explain(flag_id: int = FlagId,
                  refresh: bool = Query(False, description="Regenerate even if an assessment is stored."),
                  svc: Services = Depends(get_services)) -> dict:
    """Orbit-style explanation (question / answer / reasoning / recommended action) from System 2
    (`SYSTEM2_URL` /v1/assess, with the context packet). Stored in `assessments`; later calls return it unless
    `refresh=true`. If System 2 is unset or down: a templated explanation from the flag's reasons
    (`source: template`)."""
    return await svc.flags.explain(flag_id, current_request_id(), refresh=refresh)


@router.get("/{flag_id}/explain", response_model=Explanation, response_model_exclude_none=True)
async def get_explanation(flag_id: int = FlagId, svc: Services = Depends(get_services)) -> dict:
    """Same as POST without `refresh`: the stored explanation, generated on first request."""
    return await svc.flags.explain(flag_id, current_request_id(), refresh=False)


@router.post("/{flag_id}/ack", response_model=AckOut)
async def ack(body: AckIn, flag_id: int = FlagId, svc: Services = Depends(get_services)) -> dict:
    """Record an operator action in `acknowledgements` and update the flag status (ACKNOWLEDGE -> ACKNOWLEDGED,
    RESOLVE -> RESOLVED, ESCALATE -> OPEN). A note is embedded and upserted as RAG document `note:<ack_id>`
    (kind `operator_note`) when the embedding service is up, so System 2 learns from operators."""
    return await svc.flags.ack(flag_id, body.action, body.note, body.operator, current_request_id())
