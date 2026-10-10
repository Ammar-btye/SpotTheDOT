"""Shapes SQL results into the dashboard's headline insights (research/spot-data-insights-2026-10-09.md):
green-but-broken missions, the battery cliff, V1 vs V2 at matched battery, worst waypoints, and more.
Every number is computed from the database at request time, never hard-coded.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..db.queries import rate, wilson
from .triage import T_policy as P


def mission_view(r: Dict[str, Any]) -> Dict[str, Any]:
    """A mission row + True Mission Health (action success rate unless mission_kpis has a value)."""
    total, failed = r.get("actions_total") or 0, r.get("actions_failed") or 0
    serious = r.get("serious_anomalies") or 0
    misleading = r.get("mission_status") == "COMPLETED" and (failed > 0 or serious > 0)
    if r.get("kpi_true_health") is not None:
        health, src = float(r["kpi_true_health"]), "mission_kpis"
    else:
        health, src = (rate(total - failed, total), "action success rate")
    why = []
    if failed:
        why.append("%d of %d actions failed" % (failed, total))
    if serious:
        why.append("%d HIGH/CRITICAL anomal%s" % (serious, "y" if serious == 1 else "ies"))
    out = {k: v for k, v in r.items() if k != "kpi_true_health"}
    out.update(true_health_pct=health, true_health_source=src, status_misleading=misleading,
               why="; ".join(why) if why else None,
               true_status="NEEDS_REVIEW" if misleading else r.get("mission_status"))
    return out


def _band(rows: List[Dict[str, Any]], key: str) -> Optional[Dict[str, Any]]:
    return next((r for r in rows if r.get("grp") == key), None)


def overview_cards(o: Dict[str, Any]) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    g = o.get("green") or {}
    if g:
        cards.append({
            "key": "green_but_broken", "label": "Green but broken: reported status hides failures",
            "value": g.get("completed_with_failures"), "unit": "missions",
            "detail": g,
            "pitch": "%d of %d missions say COMPLETED, yet %d of those contain FAILED actions, and %d of the %d "
                     "HIGH/CRITICAL anomalies happened inside COMPLETED missions." % (
                         g.get("reported_completed", 0), g.get("missions", 0), g.get("completed_with_failures", 0),
                         g.get("serious_in_completed", 0), g.get("serious_anomalies", 0))})

    bands = o.get("battery_bands") or []
    low = _band(bands, "<=25")
    above = [b for b in bands if b.get("grp") != "<=25"]
    if low:
        n_above = sum(b["n"] for b in above)
        s_above = sum(b["n_success"] for b in above)
        failed = o.get("failed_missions") or []
        cards.append({
            "key": "battery_cliff", "label": "Battery cliff at <= %d%%" % P.BATTERY_LOW,
            "value": low["success_rate_pct"], "unit": "% action success at <= 25% battery",
            "detail": {"bands": bands, "above_25_success_pct": rate(s_above, n_above), "failed_missions": failed,
                       "by_config": o.get("battery_bands_by_config")},
            "pitch": "Actions succeed %s%% of the time at <= 25%% battery (n=%d) vs %s%% above it.%s Recommend "
                     "return-to-dock below ~30%%." % (
                         low["success_rate_pct"], low["n"], rate(s_above, n_above),
                         (" The only FAILED mission (%s) ended at %s%%." % (failed[0]["mission_id"],
                                                                           failed[0]["end_battery_pct"])
                          if len(failed) == 1 else ""))})

    cfg = {r["grp"]: r for r in o.get("config") or []}
    mat = {r["grp"]: r for r in o.get("config_matched") or []}
    if "V1" in cfg and "V2" in cfg:
        head = round(cfg["V2"]["success_rate_pct"] - cfg["V1"]["success_rate_pct"], 1)
        matched = (round(mat["V2"]["success_rate_pct"] - mat["V1"]["success_rate_pct"], 1)
                   if "V1" in mat and "V2" in mat else None)
        bat = {r["config"]: r for r in o.get("config_battery") or []}
        share = round(100 * (head - matched) / head) if matched is not None and head > 0 else None
        by_type: Dict[str, Dict[str, Any]] = {}
        for r in o.get("config_action_type") or []:
            by_type.setdefault(r["action_type"], {})[r["config"]] = {"n": r["n"],
                                                                     "success_rate_pct": rate(r["n_success"], r["n"])}
        cards.append({
            "key": "v1_vs_v2_matched_battery", "label": "V1 vs V2 at matched battery",
            "value": matched, "unit": "pts improvement at battery > 40%",
            "detail": {"headline": {k: cfg[k] for k in ("V1", "V2")}, "matched_battery_gt40":
                       {k: mat[k] for k in ("V1", "V2") if k in mat}, "headline_gain_pts": head,
                       "matched_gain_pts": matched, "share_explained_by_battery_pct": share,
                       "battery": bat, "by_action_type": by_type},
            "pitch": "V2's headline gain is +%s pts (%s%% -> %s%%), but at matched battery (> 40%%) it is +%s pts: "
                     "about %s%% of the 'improvement' is battery management. V2 starts at %s%% vs %s%% and drains "
                     "%s vs %s %%/action. Small sample." % (
                         head, cfg["V1"]["success_rate_pct"], cfg["V2"]["success_rate_pct"], matched, share,
                         _r(bat.get("V2", {}).get("mean_start_battery")), _r(bat.get("V1", {}).get("mean_start_battery")),
                         _r(bat.get("V2", {}).get("drain_per_action")), _r(bat.get("V1", {}).get("drain_per_action")))})

    locs = o.get("locations") or []
    if locs:
        worst = []
        for r in locs[:5]:
            lo, hi = wilson(r["n_success"], r["n"])
            worst.append({**r, "success_rate_pct": rate(r["n_success"], r["n"]), "ci95_pct": [lo, hi]})
        loc_env = o.get("localization_by_env") or []
        cards.append({
            "key": "worst_waypoints", "label": "Worst waypoints (location and environment drive failures)",
            "value": worst[0]["success_rate_pct"] if worst else None, "unit": "% success at the worst waypoint",
            "detail": {"worst": worst, "localization_failures_by_environment": loc_env},
            "pitch": "Worst waypoints: %s. %s" % (
                ", ".join("%s %s (%s%%, %s)" % (w["location_id"], w["location_name"], w["success_rate_pct"],
                                                w["environment"]) for w in worst[:3]),
                ("Localization failures by environment: %s." % ", ".join(
                    "%s %d" % (e["environment"], e["n"]) for e in loc_env)) if loc_env else "")})

    types = o.get("action_types") or []
    if types:
        s = sorted(types, key=lambda r: r["success_rate_pct"] or 0)
        cards.append({"key": "inspection_reliability", "label": "Inspection type reliability",
                      "value": s[0]["success_rate_pct"], "unit": "% success, least reliable type",
                      "detail": {"by_action_type": types},
                      "pitch": "%s is the least reliable inspection (%s%%); %s the most (%s%%)." % (
                          s[0]["grp"], s[0]["success_rate_pct"], s[-1]["grp"], s[-1]["success_rate_pct"])})

    rep = o.get("repeat_offenders") or []
    if rep:
        cards.append({"key": "severity_vs_priority", "label": "Severity is not priority: repeat offenders",
                      "value": rep[0]["anomalies"], "unit": "anomalies on the worst asset",
                      "detail": {"repeat_offenders": rep, "severity_vs_criticality": o.get("severity_vs_criticality")},
                      "pitch": "Repeat offenders: %s. Priority = severity x asset criticality." % ", ".join(
                          "%s (%d anomalies, %s criticality)" % (r["asset_id"], r["anomalies"], r["criticality"])
                          for r in rep[:3])})

    rq = o.get("readings_quality") or []
    if rq:
        q_failed = sum(r["n"] for r in rq if r["quality"] == "QUESTIONABLE" and r["status"] == "FAILED")
        q_total = sum(r["n"] for r in rq if r["quality"] == "QUESTIONABLE")
        cards.append({"key": "questionable_readings", "label": "Questionable readings come from failed actions",
                      "value": q_failed, "unit": "of %d QUESTIONABLE readings" % q_total, "detail": {"matrix": rq},
                      "pitch": "%d of %d QUESTIONABLE readings come from FAILED actions: don't trust a value from a "
                               "failed action." % (q_failed, q_total)})

    live = o.get("live") or {}
    if live:
        triaged = live.get("events_triaged") or 0
        esc = live.get("flags_escalated") or 0
        cards.append({"key": "live_triage", "label": "Live triage: System 1 routes, System 2 explains",
                      "value": esc, "unit": "escalated flags", "detail": live,
                      "pitch": ("System 1 triaged %d events and escalated %d (%s%%); only those reach System 2."
                                % (triaged, esc, rate(esc, triaged))) if triaged else
                               "No live events yet: start a replay."})
    return cards


def _r(v: Any) -> Any:
    return round(v, 1) if isinstance(v, (int, float)) else v
