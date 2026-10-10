"""Ground-truth labels for every event.

Track A ("Predict", pre_action events): labels are the kit's REAL outcomes, not rules.
    will_fail        did the action fail?
    failure_mode     navigation / data_quality / robot_health / none (grouped kit failure_type)
    anomaly_expected was an anomaly raised on this action?

Track B ("Triage", action + mission events): labels come from a documented operator-triage policy,
modelled on alarm rationalization (ISA-18.2: consequence x urgency) and grounded in the kit's own
evidence (research/spot-data-insights-2026-10-09.md). Every threshold below is a named constant.
This same policy is the deterministic validator's rulebook, so Track B measures how well Laya
reproduces it from text (incl. prose and counterfactual edits), not an independent truth.

POLICY_VERSION changes whenever a rule changes, so stale datasets can be detected.
"""
from typing import Dict, Optional, Tuple

POLICY_VERSION = "2026-10-10.1"

SEV = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
CRIT = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

# Battery cliff: kit action success is 33% at <=25% battery vs 80-90% above (insight #2).
BATTERY_CRITICAL = 15
BATTERY_LOW = 25
BATTERY_WATCH = 35

# Safe operating bands for GOOD-quality readings, set at ~5th/95th percentile of the kit's GOOD readings.
SAFE_BANDS: Dict[str, Tuple[Optional[float], Optional[float]]] = {
    "TEMPERATURE_C": (None, 78.0),
    "PRESSURE_PSI": (76.0, 140.0),
    "SOUND_DB": (None, 82.0),
    "VISUAL_SCORE": (72.0, None),
    "LOCALIZATION_CONFIDENCE_PCT": (80.0, None),
}
# Outside these, a reading is physically implausible: a sensor glitch, never a real value.
PLAUSIBLE: Dict[str, Tuple[float, float]] = {
    "TEMPERATURE_C": (-40.0, 400.0),
    "PRESSURE_PSI": (0.0, 300.0),          # the kit's gauge face reads 0-300 psi
    "SOUND_DB": (0.0, 140.0),
    "VISUAL_SCORE": (0.0, 100.0),
    "LOCALIZATION_CONFIDENCE_PCT": (0.0, 100.0),
}

NAV_FAILURES = {"LOCALIZATION_FAILURE", "OBSTACLE_DETECTION", "PATH_BLOCKED"}
DATA_FAILURES = {"SENSOR_TIMEOUT", "READING_UNRELIABLE", "SIGNAL_NOISE", "TARGET_NOT_DETECTED"}
COMMS_FAILURES = {"COMMUNICATION_LOSS"}
EQUIPMENT_ANOMALIES = {"ABNORMAL_VIBRATION", "ABNORMAL_TEMPERATURE", "GAUGE_OUT_OF_RANGE", "VISUAL_DEFECT"}
NAV_ANOMALIES = {"NAVIGATION_OBSTRUCTION", "LOCALIZATION_ISSUE"}
DATA_ANOMALIES = {"SIGNAL_DEGRADATION"}


def failure_mode(failure_type: Optional[str]) -> str:
    if failure_type is None:
        return "none"
    if failure_type in NAV_FAILURES:
        return "navigation"
    if failure_type in COMMS_FAILURES:
        return "robot_health"
    if failure_type in DATA_FAILURES:
        return "data_quality"
    raise ValueError("unknown failure_type %r" % failure_type)


def reading_state(ev: dict) -> Tuple[str, bool]:
    """('none' | 'untrusted' | 'trusted', out_of_safe_band)."""
    r = ev.get("reading")
    if not r:
        return "none", False
    lo, hi = PLAUSIBLE[r["measurement_type"]]
    if r["quality"] != "GOOD" or ev["status"] == "FAILED" or not (lo <= r["value"] <= hi):
        return "untrusted", False
    blo, bhi = SAFE_BANDS[r["measurement_type"]]
    out = (blo is not None and r["value"] < blo) or (bhi is not None and r["value"] > bhi)
    return "trusted", out


def label_action(ev: dict) -> Dict[str, str]:
    an = ev.get("anomaly")
    sev = SEV[an["severity"]] if an else 0
    atype = an["anomaly_type"] if an else None
    crit = CRIT[ev["asset"]["criticality"]]
    batt, failed, ft = ev["battery_pct"], ev["status"] == "FAILED", ev["failure_type"]
    trust, out_band = reading_state(ev)
    loc_band = out_band and ev["reading"]["measurement_type"] == "LOCALIZATION_CONFIDENCE_PCT"
    equip_band = out_band and not loc_band

    if (sev == 4 or (sev == 3 and crit >= 3) or (failed and batt <= BATTERY_CRITICAL)
            or (ft in COMMS_FAILURES and batt <= BATTERY_LOW)):
        priority = "P1"
    elif (sev == 3 or (sev == 2 and crit >= 3) or (failed and crit >= 3) or batt <= BATTERY_LOW
          or (equip_band and crit >= 2)):
        priority = "P2"
    elif sev >= 1 or failed or trust == "untrusted" or batt <= BATTERY_WATCH or out_band:
        priority = "P3"
    else:
        priority = "P4"

    if atype in EQUIPMENT_ANOMALIES:
        category = "equipment"
    elif batt <= BATTERY_CRITICAL or ft in COMMS_FAILURES:
        category = "robot_health"
    elif ft in NAV_FAILURES or atype in NAV_ANOMALIES or loc_band:
        category = "navigation"
    elif ft in DATA_FAILURES or atype in DATA_ANOMALIES or trust == "untrusted":
        category = "data_quality"
    elif batt <= BATTERY_WATCH:
        category = "robot_health"
    elif equip_band:
        category = "equipment"
    else:
        category = "none"
    assert (priority == "P4") == (category == "none"), (priority, category, ev["event_id"])

    return {
        "escalate": "A" if priority in ("P1", "P2") else "B",
        "priority": priority,
        "category": category,
        "reading_trust": {"trusted": "A", "untrusted": "B", "none": "C"}[trust],
    }


def label_mission(ev: dict) -> Dict[str, str]:
    serious = ev["anomalies_by_severity"]["HIGH"] + ev["anomalies_by_severity"]["CRITICAL"]
    misleading = ev["reported_status"] == "COMPLETED" and (ev["actions_failed"] > 0 or serious > 0)
    if (misleading and serious > 0) or ev["reported_status"] == "FAILED":
        priority = "P2"
    elif misleading or ev["end_battery_pct"] <= BATTERY_LOW:
        priority = "P3"
    else:
        priority = "P4"
    return {
        "escalate": "A" if priority in ("P1", "P2") else "B",
        "priority": priority,
        "mission_misleading": "A" if misleading else "B",
    }


def label_pre_action(outcome: dict) -> Dict[str, str]:
    """`outcome` is the matching post-outcome action event (the real result)."""
    return {
        "will_fail": "A" if outcome["status"] == "FAILED" else "B",
        "failure_mode": failure_mode(outcome["failure_type"]),
        "anomaly_expected": "A" if outcome["anomaly"] else "B",
    }


def label(ev: dict, outcome: Optional[dict] = None) -> Dict[str, str]:
    if ev["kind"] == "action":
        return label_action(ev)
    if ev["kind"] == "mission":
        return label_mission(ev)
    if outcome is None:
        raise ValueError("pre_action labels need the real outcome event")
    return label_pre_action(outcome)
