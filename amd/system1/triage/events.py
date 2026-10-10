"""Canonical event records, shared by the policy, the renderers, the simulator and the baselines.

Three event kinds, matching the two benchmark tracks:

- ``pre_action``  (Track A, "Predict"): what SPOT knows *before* an action runs. No outcome fields.
                  Labels are the kit's real outcomes (did it fail, how, was an anomaly raised).
- ``action``      (Track B, "Triage"): the action *after* it ran: status, reading and anomaly.
- ``mission``     (Track B, "Triage"): a mission summary at MISSION_COMPLETED.

Kit missions are 10 actions each. The same builders run on simulated missions (simulate.py), so
real and synthetic events are structurally identical.
"""
from typing import Dict, List, Optional

SEV_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def pre_action_event(action: dict, mission: dict, location: dict, asset: dict,
                     history: List[dict], source: str) -> dict:
    """The state before `action` runs. `history` is the mission's earlier action events (post-outcome)."""
    failures_so_far = sum(1 for h in history if h["status"] == "FAILED")
    last = history[-1] if history else None
    return {
        "kind": "pre_action", "source": source,
        "event_id": "pre-" + action["action_id"], "action_id": action["action_id"],
        "mission_id": mission["mission_id"], "configuration_version": mission["configuration_version"],
        "timestamp": action["timestamp"], "sequence": action["sequence"],
        "action_type": action["action_type"], "battery_pct": action["battery_pct"],
        "location": location, "asset": asset,
        "mission_so_far": {
            "actions_done": len(history), "failures_so_far": failures_so_far,
            "last_status": last["status"] if last else None,
            "last_failure_type": last["failure_type"] if last else None,
            "start_battery_pct": mission["start_battery_pct"],
        },
    }


def action_event(action: dict, mission: dict, location: dict, asset: dict,
                 reading: Optional[dict], anomaly: Optional[dict], source: str) -> dict:
    return {
        "kind": "action", "source": source,
        "event_id": "act-" + action["action_id"], "action_id": action["action_id"],
        "mission_id": mission["mission_id"], "configuration_version": mission["configuration_version"],
        "timestamp": action["timestamp"], "sequence": action["sequence"],
        "action_type": action["action_type"], "status": action["status"],
        "failure_type": action["failure_type"], "duration_sec": action["duration_sec"],
        "battery_pct": action["battery_pct"], "location": location, "asset": asset,
        "reading": reading, "anomaly": anomaly,
    }


def mission_event(mission: dict, action_events: List[dict], source: str) -> dict:
    failed = [e for e in action_events if e["status"] == "FAILED"]
    anomalies = [dict(e["anomaly"], asset_criticality=e["asset"]["criticality"],
                      asset_name=e["asset"]["asset_name"])
                 for e in action_events if e["anomaly"]]
    by_sev = {s: sum(1 for a in anomalies if a["severity"] == s) for s in SEV_RANK}
    worst = max(anomalies, key=lambda a: SEV_RANK[a["severity"]], default=None)
    return {
        "kind": "mission", "source": source, "event_id": "mis-" + mission["mission_id"],
        "mission_id": mission["mission_id"], "configuration_version": mission["configuration_version"],
        "timestamp": mission["end_time"], "reported_status": mission["mission_status"],
        "duration_min": mission["duration_min"], "start_battery_pct": mission["start_battery_pct"],
        "end_battery_pct": mission["end_battery_pct"],
        "actions_total": len(action_events), "actions_failed": len(failed),
        "failure_types": sorted({e["failure_type"] for e in failed}),
        "anomalies_by_severity": by_sev,
        "worst_anomaly": None if worst is None else {
            "anomaly_type": worst["anomaly_type"], "severity": worst["severity"],
            "asset_name": worst["asset_name"], "asset_criticality": worst["asset_criticality"]},
    }


def mission_events(mission: dict, actions: List[dict], locations: Dict[str, dict], assets: Dict[str, dict],
                   readings: Dict[str, dict], anomalies: Dict[str, dict], source: str) -> List[dict]:
    """All events for one mission: a pre_action + action event per action, then one mission event."""
    out, history = [], []
    for a in actions:
        loc, asset = locations[a["location_id"]], assets[a["asset_id"]]
        out.append(pre_action_event(a, mission, loc, asset, history, source))
        ev = action_event(a, mission, loc, asset, readings.get(a["action_id"]), anomalies.get(a["action_id"]), source)
        out.append(ev)
        history.append(ev)
    out.append(mission_event(mission, history, source))
    return out
