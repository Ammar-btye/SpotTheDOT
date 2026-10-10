from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..db.pool import DatabaseUnavailable
from ..deps import Services, current_request_id, get_services
from ..schemas.misc import Forecast, PredictIn, PredictOut
from ..services import validator as V
from ..services.http import ServiceUnavailable

FORECAST_LIVE_MAX = 5
router = APIRouter(prefix="/system1", tags=["system1"])


@router.post("/predict", response_model=PredictOut, response_model_exclude_none=True)
async def predict(body: PredictIn, svc: Services = Depends(get_services)) -> dict:
    """Proxy to Laya's `/v1/predict`. Each item is a canonical event (`event` + `kind`) or just a kit
    `action_id` (the backend builds the event). Nothing is stored. If System 1 is down, action/mission items
    get the validator's answers instead (`source: rules_fallback`); pre_action items get none."""
    items: List[Dict[str, Any]] = []
    for i, it in enumerate(body.items):
        if it.event is not None:
            if not it.kind:
                raise HTTPException(422, "items[%d]: `kind` is required with `event`" % i)
            ev, kind = it.event, it.kind
        elif it.action_id:
            kind = it.kind or "pre_action"
            if kind == "mission":
                raise HTTPException(422, "items[%d]: build mission events with `event`" % i)
            ev = svc.ref.canonical_for_action(it.action_id, kind)
            if ev is None:
                raise HTTPException(404, "items[%d]: unknown action_id %s" % (i, it.action_id))
        else:
            raise HTTPException(422, "items[%d]: give `event` or `action_id`" % i)
        item = {"id": it.id or ev.get("event_id") or "item-%d" % i, "kind": kind, "event": ev}
        if it.questions:
            item["questions"] = it.questions
        items.append(item)
    try:
        resp = await svc.system1.predict(items, request_id=current_request_id())
        return {"source": "system1", **resp}
    except ServiceUnavailable as exc:
        out = []
        for it in items:
            try:
                rv = V.rules_verdict(it["kind"], it["event"])
            except (KeyError, TypeError, ValueError) as e:
                rv, err = None, "event not understood by the validator: %s" % e
            else:
                err = None
            answers = {q: {"answer": a, "probs": {a: 1.0}, "confidence": 1.0}
                       for q, a in (rv or {}).get("labels", {}).items()}
            out.append({"id": it["id"], "kind": it["kind"], "answers": answers,
                        **({"note": err or "no rules for pre_action events"} if not answers else {})})
        return {"source": "rules_fallback", "model": "policy.py@" + V.POLICY_VERSION, "items": out,
                "error": exc.reason}


@router.get("/forecast", response_model=Forecast)
async def forecast(mission_id: Optional[str] = Query(None, description="Forecast every action of this mission."),
                   action_id: Optional[str] = Query(None, description="Forecast one action."),
                   live: bool = Query(True, description="Call Laya for actions without stored predictions."),
                   svc: Services = Depends(get_services)) -> dict:
    """Pre-action failure forecast (Laya's Track A: will_fail, failure_mode, anomaly_expected) for a mission's
    actions or one action. Uses stored predictions first, then calls Laya live (and stores the answers).
    Always includes the empirical baseline (failure rate of this action type at this waypoint) and, for kit
    actions, the actual outcome so the dashboard can show where Laya was right. If Laya is down, the baseline
    is the forecast (`source: baseline`)."""
    if not mission_id and not action_id:
        raise HTTPException(422, "give mission_id or action_id")
    acts = ([svc.ref.actions[action_id]] if action_id in svc.ref.actions else []) if action_id else \
        svc.ref.mission_actions(mission_id)  # type: ignore[arg-type]
    if not acts:
        raise HTTPException(404, "no kit actions for %s" % (action_id or mission_id))
    ids = [a["action_id"] for a in acts]
    stored: Dict[str, Dict[str, Any]] = {}
    try:
        for p in await svc.repo.predictions_for_actions(ids, "pre_action"):
            stored.setdefault(p["action_id"], {}).setdefault(p["question"], p)
    except DatabaseUnavailable:
        pass
    baseline: Dict[tuple, float] = {}
    try:
        rows = await svc.repo.failure_baseline()
        baseline = {(r["location_id"], r["action_type"]): round(100.0 * r["failed"] / r["n"], 1)
                    for r in rows if r["n"]}
    except Exception:  # noqa: BLE001 - the baseline is optional
        baseline = {}
    missing = [a for a in acts if a["action_id"] not in stored]
    live_answers: Dict[str, Dict[str, Any]] = {}
    status = "ok"
    if missing and live:
        items = []
        # Audit H2: on CPU each pre_action event costs ~2-3 s of Laya time and Laya serves one request at a time,
        # so a live forecast asks for at most FORECAST_LIVE_MAX actions; the rest get the empirical baseline.
        for a in missing[:FORECAST_LIVE_MAX]:
            ev = svc.ref.canonical_for_action(a["action_id"], "pre_action")
            if ev:
                items.append({"id": a["action_id"], "kind": "pre_action", "event": ev})
        try:
            resp = await svc.system1.predict(items, request_id=current_request_id())
            for it in resp.get("items") or []:
                live_answers[it["id"]] = it.get("answers") or {}
                try:
                    await svc.repo.store_predictions("pre_action", it["id"], svc.ref.actions[it["id"]]["mission_id"],
                                                     resp.get("model") or "unknown", it.get("answers") or {})
                except Exception:  # noqa: BLE001 - storing is best effort
                    pass
        except ServiceUnavailable:
            status = "laya_unavailable"
    elif missing:
        status = "laya_unavailable" if not stored else "ok"
    out = []
    for a in acts:
        aid = a["action_id"]
        base = baseline.get((a["location_id"], a["action_type"]))
        item: Dict[str, Any] = {"action_id": aid, "sequence": a["sequence"], "action_type": a["action_type"],
                                "location_id": a["location_id"], "asset_id": a["asset_id"],
                                "battery_pct": a["battery_pct"], "baseline_fail_pct": base,
                                "actual": {"status": a["status"], "failure_type": a["failure_type"],
                                           "anomaly": svc.ref.anomalies.get(aid) is not None}}
        if aid in stored:
            s = stored[aid]
            item.update(source="system1_stored", model=(s.get("will_fail") or {}).get("model"),
                        p_fail=((s.get("will_fail") or {}).get("probs") or {}).get("A"),
                        failure_mode=(s.get("failure_mode") or {}).get("answer"),
                        p_anomaly=((s.get("anomaly_expected") or {}).get("probs") or {}).get("A"))
        elif aid in live_answers:
            ans = live_answers[aid]
            item.update(source="system1_live", p_fail=((ans.get("will_fail") or {}).get("probs") or {}).get("A"),
                        failure_mode=(ans.get("failure_mode") or {}).get("answer"),
                        p_anomaly=((ans.get("anomaly_expected") or {}).get("probs") or {}).get("A"))
        else:
            item.update(source="baseline", p_fail=(base / 100.0) if base is not None else None)
        out.append(item)
    return {"scope": {"mission_id": mission_id, "action_id": action_id}, "items": out, "system1": status}
