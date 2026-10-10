"""Domain facts the tools share: enums, policy thresholds, battery bands and the allowed-action enum.

Thresholds and the validator's labelling come from amd/system1/triage/policy.py (the validator's rulebook), so
System 2 never disagrees with the validator about a number. Lookup order: $POLICY_PATH, the repo checkout
(amd/system1/triage/policy.py), then the vendored copy in spot_mcp/vendor/ (what the Docker image uses; a unit test
fails if it drifts from the original). `POLICY_SOURCE` says which one was loaded.
"""
from __future__ import annotations

import importlib.util
import logging
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger(__name__)

_VENDOR = Path(__file__).resolve().parent / "vendor"
_REPO_TRIAGE = Path(__file__).resolve().parents[2] / "system1" / "triage"


def _load(name: str, candidates):
    for path in candidates:
        if path and Path(path).is_file():
            spec = importlib.util.spec_from_file_location("spot_triage_" + name, path)
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            return mod, Path(path)
    raise ImportError("%s.py not found in %s" % (name, [str(c) for c in candidates if c]))


policy, _POLICY_PATH = _load("policy", [os.environ.get("POLICY_PATH"), _REPO_TRIAGE / "policy.py",
                                        _VENDOR / "policy.py"])
POLICY_SOURCE = ("vendored-policy.py@" if _POLICY_PATH.parent == _VENDOR else "amd/system1/triage/policy.py@") \
    + policy.POLICY_VERSION
BATTERY_CRITICAL, BATTERY_LOW, BATTERY_WATCH = policy.BATTERY_CRITICAL, policy.BATTERY_LOW, policy.BATTERY_WATCH
SAFE_BANDS: Dict[str, Tuple[Optional[float], Optional[float]]] = dict(policy.SAFE_BANDS)
PLAUSIBLE: Dict[str, Tuple[float, float]] = dict(policy.PLAUSIBLE)

# ── enums (kit vocabulary) ──────────────────────────────────────────────────────────────────────
ACTION_TYPES = ("ACOUSTIC_INSPECTION", "GAUGE_READING", "NAVIGATION", "THERMAL_INSPECTION", "VISUAL_INSPECTION")
CONFIG_VERSIONS = ("V1", "V2")
# Same bands as the risk_scores table. The policy cliff (<=25%) is a band edge.
BATTERY_BANDS = ("<=25", "26-40", "41-60", "61-80", "81+")
GROUP_BY = ("action_type", "location_id", "configuration_version", "battery_band")
CATEGORIES = ("equipment", "data_quality", "navigation", "robot_health", "mission", "none")
SMALL_SAMPLE_N = 20

# ── allowed recommended actions (System 2 must pick one of these) ───────────────────────────────
ALLOWED_ACTIONS: Dict[str, Dict[str, str]] = {
    "equipment": {
        "DISPATCH_TECHNICIAN": "send a technician to inspect the equipment this shift",
        "SCHEDULE_MAINTENANCE": "open a maintenance work order for the next maintenance window",
        "REINSPECT_NEXT_ROUTE": "re-check this asset on SPOT's next route and compare",
        "ESCALATE_TO_SUPERVISOR": "notify the shift supervisor now (critical asset or critical anomaly)",
        "MONITOR": "no action now; keep watching the trend",
    },
    "data_quality": {
        "REINSPECT_NOW": "send SPOT back to repeat the inspection now",
        "MANUAL_READING": "have a technician take the reading by hand",
        "CHECK_SENSOR_PAYLOAD": "inspect SPOT's sensor payload / camera for faults",
        "REINSPECT_NEXT_ROUTE": "repeat the inspection on the next route",
        "MONITOR": "no action now; keep watching",
    },
    "navigation": {
        "REINSPECT_NOW": "retry the waypoint now",
        "CLEAR_PATH": "have someone remove the obstacle blocking SPOT's path",
        "ADJUST_WAYPOINT": "move or re-record the waypoint / add fiducials (noisy or low-light area)",
        "UPDATE_AUTOWALK_MAP": "re-record the Autowalk route segment",
        "MONITOR": "no action now; keep watching",
    },
    "robot_health": {
        "RETURN_TO_DOCK": "send SPOT to the dock now",
        "CHARGE_BEFORE_NEXT_MISSION": "fully charge SPOT before the next mission",
        "CHECK_COMMS": "check radio / network coverage at this waypoint",
        "ABORT_MISSION": "stop the current mission",
        "MONITOR": "no action now; keep watching",
    },
    "mission": {
        "REVIEW_MISSION": "review the mission's failed actions and anomalies before signing it off",
        "RERUN_FAILED_ACTIONS": "schedule a mission that repeats only the failed actions",
        "CHARGE_BEFORE_NEXT_MISSION": "fully charge SPOT before the next mission",
        "MONITOR": "no action now",
    },
    "none": {
        "NO_ACTION": "routine event; log only",
        "MONITOR": "no action now; keep watching",
    },
}
ALL_ACTIONS = tuple(sorted({a for acts in ALLOWED_ACTIONS.values() for a in acts}))


def suggested_action(category: str, priority: Optional[str], facts: Dict[str, Any]) -> str:
    """Deterministic default the validator would pick. System 2 may choose another allowed action."""
    batt = facts.get("battery_pct")
    ft = facts.get("failure_type")
    if category == "equipment":
        if priority == "P1":
            return "ESCALATE_TO_SUPERVISOR" if facts.get("severity") == "CRITICAL" else "DISPATCH_TECHNICIAN"
        return "SCHEDULE_MAINTENANCE" if priority == "P2" else "REINSPECT_NEXT_ROUTE"
    if category == "robot_health":
        if ft == "COMMUNICATION_LOSS":
            return "CHECK_COMMS" if (batt is None or batt > BATTERY_LOW) else "RETURN_TO_DOCK"
        if batt is not None and batt <= BATTERY_CRITICAL:
            return "RETURN_TO_DOCK"
        return "CHARGE_BEFORE_NEXT_MISSION"
    if category == "navigation":
        if ft in ("PATH_BLOCKED", "OBSTACLE_DETECTION"):
            return "CLEAR_PATH"
        if ft == "LOCALIZATION_FAILURE" or facts.get("environment") in ("HIGH_NOISE", "LOW_LIGHT"):
            return "ADJUST_WAYPOINT"
        return "REINSPECT_NOW"
    if category == "data_quality":
        return "REINSPECT_NOW" if priority in ("P1", "P2") else "REINSPECT_NEXT_ROUTE"
    if category == "mission":
        return "REVIEW_MISSION"
    return "NO_ACTION"


# ── helpers ─────────────────────────────────────────────────────────────────────────────────────
def battery_band(pct: float) -> str:
    if pct <= 25:
        return "<=25"
    if pct <= 40:
        return "26-40"
    if pct <= 60:
        return "41-60"
    if pct <= 80:
        return "61-80"
    return "81+"


def battery_status(pct: float) -> str:
    if pct <= BATTERY_CRITICAL:
        return "CRITICAL"
    if pct <= BATTERY_LOW:
        return "LOW"
    if pct <= BATTERY_WATCH:
        return "WATCH"
    return "OK"


def band_check(measurement_type: str, value: Optional[float], quality: Optional[str],
               action_status: Optional[str]) -> Dict[str, Any]:
    """Mirror of policy.reading_state plus the band itself, so the model can quote both."""
    lo, hi = SAFE_BANDS.get(measurement_type, (None, None))
    plo, phi = PLAUSIBLE.get(measurement_type, (-math.inf, math.inf))
    out: Dict[str, Any] = {"safe_low": lo, "safe_high": hi}
    if value is None:
        out.update(trust="none", in_safe_band=None, reason="no value")
        return out
    reasons = []
    if quality != "GOOD":   # policy.reading_state: anything but GOOD (including a missing quality) is untrusted
        reasons.append("quality %s" % quality)
    if action_status == "FAILED":
        reasons.append("action FAILED (kit: every QUESTIONABLE reading comes from a failed action)")
    if not (plo <= value <= phi):
        reasons.append("physically implausible (outside %s..%s)" % (plo, phi))
    if reasons:
        out.update(trust="untrusted", in_safe_band=None, reason="; ".join(reasons))
        return out
    below = lo is not None and value < lo
    above = hi is not None and value > hi
    out.update(trust="trusted", in_safe_band=not (below or above),
               reason="below safe band" if below else "above safe band" if above else "within safe band")
    return out


def wilson(successes: int, n: int, z: float = 1.96) -> Tuple[Optional[float], Optional[float]]:
    if n <= 0:
        return None, None
    p = successes / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return round(max(0.0, c - h) * 100, 1), round(min(1.0, c + h) * 100, 1)


def rate_summary(n: int, n_success: int) -> Dict[str, Any]:
    lo, hi = wilson(n_success, n)
    out: Dict[str, Any] = {"n": n, "n_success": n_success,
                           "success_rate_pct": round(100.0 * n_success / n, 1) if n else None,
                           "ci95_pct": [lo, hi] if n else None}
    if n < SMALL_SAMPLE_N:
        out["warning"] = "small sample (n=%d < %d): indicative only" % (n, SMALL_SAMPLE_N)
    return out


# ── parameter validation (defence in depth; MCP schemas validate first) ─────────────────────────
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,63}$")


def check_id(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise ValueError("%s must be an id like 'A0136', 'HX-204', 'WP07' or 'M014' "
                         "(letters, digits, - _ . :, max 64 chars); got %r" % (name, value))
    return value


def check_text(name: str, value: Any, max_len: int = 500) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % name)
    v = " ".join(value.split())
    if len(v) > max_len:
        raise ValueError("%s is too long (%d chars, max %d)" % (name, len(v), max_len))
    return v


def check_int(name: str, value: Any, lo: int, hi: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not (lo <= value <= hi):
        raise ValueError("%s must be an integer in [%d, %d]; got %r" % (name, lo, hi, value))
    return value


def check_enum(name: str, value: Any, allowed) -> str:
    if value not in allowed:
        raise ValueError("%s must be one of %s; got %r" % (name, list(allowed), value))
    return value


# ── System 1 question wording (amd/system1/triage/questions.py), for readable forecasts ─────────
def _load_questions() -> Dict[str, Any]:
    try:
        mod, _ = _load("questions", [_POLICY_PATH.with_name("questions.py"), _VENDOR / "questions.py"])
        return dict(mod.QUESTIONS)
    except Exception:  # noqa: BLE001 - wording is optional
        return {}


QUESTIONS = _load_questions()


def answer_meaning(question: str, answer: str) -> Optional[str]:
    return (QUESTIONS.get(question) or {}).get("criteria", {}).get(answer)
