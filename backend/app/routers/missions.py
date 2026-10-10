from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import Services, current_request_id, get_services
from ..schemas.misc import Debrief, MissionDetail, MissionList, Timeline
from ..services.analytics import mission_view
from ..services.http import ServiceUnavailable
from ..services.system2 import template_debrief
from ..services.triage import T_policy as P

router = APIRouter(prefix="/missions", tags=["missions"])


async def _mission(svc: Services, mission_id: str) -> Dict[str, Any]:
    rows = await svc.repo.mission_health()
    row = next((r for r in rows if r["mission_id"] == mission_id), None)
    if row is None:
        raise HTTPException(404, "no mission %s" % mission_id)
    return mission_view(row)


@router.get("", response_model=MissionList)
async def list_missions(misleading_only: bool = Query(False, description="Only missions whose reported status "
                                                                         "hides failures (green but broken)."),
                        config: Optional[str] = Query(None, description="V1 | V2"),
                        svc: Services = Depends(get_services)) -> dict:
    """All missions with reported status vs **True Mission Health**: failed actions, HIGH/CRITICAL anomalies,
    `status_misleading` (COMPLETED but hiding problems), open flags and how many events were ingested live."""
    items = [mission_view(r) for r in await svc.repo.mission_health()]
    if config:
        items = [m for m in items if m.get("configuration_version") == config]
    totals = {"missions": len(items),
              "reported_completed": sum(1 for m in items if m.get("mission_status") == "COMPLETED"),
              "misleading": sum(1 for m in items if m["status_misleading"]),
              "open_flags": sum(m.get("flags_open") or 0 for m in items)}
    if misleading_only:
        items = [m for m in items if m["status_misleading"]]
    return {"items": items, "totals": totals}


@router.get("/{mission_id}", response_model=MissionDetail)
async def get_mission(mission_id: str, svc: Services = Depends(get_services)) -> dict:
    """One mission: summary + True Mission Health, every action (with reading, anomaly, flags) and its flags."""
    m = await _mission(svc, mission_id)
    return {"mission": m, "actions": await svc.repo.mission_actions(mission_id),
            "flags": await svc.repo.mission_flags(mission_id)}


@router.get("/{mission_id}/timeline", response_model=Timeline)
async def timeline(mission_id: str, svc: Services = Depends(get_services)) -> dict:
    """The mission in robot order: each action from the kit merged with its live-ingested events (and their
    triage verdicts) and flags, plus MISSION_STARTED/COMPLETED. Works before any replay (kit only)."""
    await _mission(svc, mission_id)
    actions = await svc.repo.mission_actions(mission_id)
    events = await svc.repo.mission_events(mission_id)
    by_action: Dict[str, List[Dict[str, Any]]] = {}
    mission_level: List[Dict[str, Any]] = []
    for e in events:
        (by_action.setdefault(e["action_id"], []) if e.get("action_id") else mission_level).append(e)
    items: List[Dict[str, Any]] = []
    for e in mission_level:
        items.append({"type": "mission_event", "timestamp": e["ts"], "event_type": e["event_type"],
                      "event_id": e["event_id"], "battery_pct": e.get("battery_pct"), "triage": e.get("triage")})
    for a in actions:
        evs = by_action.get(a["action_id"], [])
        items.append({"type": "action", "timestamp": a["timestamp"], "sequence": a["sequence"],
                      "action_id": a["action_id"], "action_type": a["action_type"], "status": a["status"],
                      "failure_type": a.get("failure_type"), "battery_pct": a["battery_pct"],
                      "battery_status": ("CRITICAL" if a["battery_pct"] <= P.BATTERY_CRITICAL else "LOW"
                                         if a["battery_pct"] <= P.BATTERY_LOW else "WATCH"
                                         if a["battery_pct"] <= P.BATTERY_WATCH else "OK")
                      if a.get("battery_pct") is not None else None,
                      "location": {"location_id": a["location_id"], "location_name": a.get("location_name"),
                                   "environment": a.get("environment")},
                      "asset": {"asset_id": a["asset_id"], "asset_name": a.get("asset_name"),
                                "criticality": a.get("criticality")},
                      "reading": a.get("reading"), "anomaly": a.get("anomaly"), "flags": a.get("flags") or [],
                      "events": [{"event_id": e["event_id"], "event_type": e["event_type"], "ts": e["ts"],
                                  "triage": e.get("triage")} for e in evs]})
    items.sort(key=lambda x: (str(x["timestamp"]), 0 if x.get("event_type") == "MISSION_STARTED" else
                              2 if x.get("event_type") == "MISSION_COMPLETED" else 1, x.get("sequence") or 0))
    return {"mission_id": mission_id, "items": items, "events_ingested": len(events)}


@router.get("/{mission_id}/debrief", response_model=Debrief, response_model_exclude_none=True)
async def debrief(mission_id: str, svc: Services = Depends(get_services)) -> dict:
    """Post-mission after-action summary: what happened, what the reported status hides, and what to do.
    From System 2 `/v1/debrief` when configured; otherwise a deterministic template (`source: template`)."""
    m = await _mission(svc, mission_id)
    actions = await svc.repo.mission_actions(mission_id)
    n = len(actions) or 1
    serious = [{"anomaly_id": a["anomaly"].get("anomaly_id"), "severity": a["anomaly"].get("severity"),
                "anomaly_type": a["anomaly"].get("anomaly_type"), "asset_id": a["asset_id"],
                "asset_criticality": a.get("criticality")}
               for a in actions if a.get("anomaly") and a["anomaly"].get("severity") in ("HIGH", "CRITICAL")]
    failure_types: Dict[str, int] = {}
    worst_loc: Dict[str, int] = {}
    for a in actions:
        if a["status"] == "FAILED":
            failure_types[a.get("failure_type") or "UNKNOWN"] = failure_types.get(a.get("failure_type") or "UNKNOWN",
                                                                                  0) + 1
            worst_loc[a["location_id"]] = worst_loc.get(a["location_id"], 0) + 1
    facts = {"mission": {k: m.get(k) for k in ("mission_id", "mission_name", "configuration_version", "mission_status",
                                               "start_battery_pct", "end_battery_pct", "duration_min", "start_time",
                                               "end_time")},
             "actions_total": m["actions_total"], "actions_failed": m["actions_failed"],
             "true_health_pct": m["true_health_pct"], "status_misleading": m["status_misleading"], "why": m["why"],
             "failure_types": failure_types, "failures_by_location": worst_loc, "serious_anomalies": serious,
             "battery_drain_per_action": round(((m.get("start_battery_pct") or 0) - (m.get("end_battery_pct") or 0)) / n,
                                               1),
             "actions_at_low_battery": sum(1 for a in actions if (a.get("battery_pct") or 100) <= P.BATTERY_LOW),
             "open_flags": m.get("flags_open")}
    try:
        out = await svc.system2.debrief({"mission_id": mission_id, "facts": facts}, current_request_id())
        if not out.get("summary"):
            raise ServiceUnavailable("system2", "debrief had no summary")
        recs = out.get("recommendations") or out.get("recommended_actions") or []
        return {"mission_id": mission_id, "summary": out["summary"],
                "recommendations": [r if isinstance(r, str) else str(r) for r in recs], "facts": facts,
                "source": "system2", "model": out.get("model")}
    except ServiceUnavailable as exc:
        t = template_debrief(facts)
        return {"mission_id": mission_id, **t, "facts": facts, "fallback_reason": exc.reason}
