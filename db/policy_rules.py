"""The System 1 triage policy (amd/system1/triage/policy.py) as named rules.

Two uses:
- `db/setup.py seed` explains every escalated flag: flags.reasons = [{rule, detail, weight}], where `rule` is a
  name below. The RAG doc for that rule is `policy:<rule>` (kind 'policy'), so System 2 can cite it.
- `amd/embed/ingest.py` embeds one `policy` doc per rule (RULES + REFERENCE).

The predicates reuse policy.py's constants and helpers, and `check_against_policy()` asserts that the priority
they imply equals policy.label_action / label_mission on every event, so these rules can't drift from the code.
The texts are hand-written from the code; every number in them is interpolated from policy.py's constants.
"""
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from triage import policy as P

PRIO_ORDER = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
FLAG_SEVERITY = {"P1": "CRITICAL", "P2": "HIGH", "P3": "MEDIUM", "P4": "LOW"}
# Scores match backend/app/services/validator.py (canonical: it scores live flags; audit M11, integration log
# 2026-10-10). A seeded flag gets the backend's rules-only score, so seeded and live flags share one scale.
BASE_SCORE = {"P1": 90.0, "P2": 70.0, "P3": 45.0, "P4": 20.0}
WEIGHT = {"P1": 3, "P2": 2, "P3": 1}


def _h(s: str) -> str:
    return s.replace("_", " ").lower()


def _band(m: str) -> str:
    lo, hi = P.SAFE_BANDS[m]
    if lo is not None and hi is not None:
        return "%g to %g" % (lo, hi)
    return ("at most %g" % hi) if hi is not None else ("at least %g" % lo)


@dataclass(frozen=True)
class Rule:
    name: str
    scope: str                 # 'action' | 'mission' | 'reference'
    priority: Optional[str]    # P1..P3 for predicate rules, None for reference docs
    title: str
    text: str
    when: Optional[Callable[[dict], bool]] = None
    detail: Optional[Callable[[dict], str]] = None


def action_context(ev: dict) -> dict:
    """The facts label_action() decides on, computed exactly as policy.py does."""
    an = ev.get("anomaly")
    trust, out_band = P.reading_state(ev)
    loc_band = out_band and ev["reading"]["measurement_type"] == "LOCALIZATION_CONFIDENCE_PCT"
    return {
        "ev": ev, "sev": P.SEV[an["severity"]] if an else 0, "atype": an["anomaly_type"] if an else None,
        "an": an, "crit": P.CRIT[ev["asset"]["criticality"]], "batt": ev["battery_pct"],
        "failed": ev["status"] == "FAILED", "ft": ev["failure_type"], "trust": trust, "out_band": out_band,
        "loc_band": loc_band, "equip_band": out_band and not loc_band,
    }


def mission_context(ev: dict) -> dict:
    serious = ev["anomalies_by_severity"]["HIGH"] + ev["anomalies_by_severity"]["CRITICAL"]
    misleading = ev["reported_status"] == "COMPLETED" and (ev["actions_failed"] > 0 or serious > 0)
    return {"ev": ev, "serious": serious, "misleading": misleading}


def _asset(c: dict) -> str:
    a = c["ev"]["asset"]
    return "%s (%s, %s criticality)" % (a["asset_name"], a["asset_id"], a["criticality"])


def _anom(c: dict) -> str:
    return "%s (%s) on %s" % (_h(c["atype"]), c["an"]["severity"], _asset(c))


def _reading(c: dict) -> str:
    r = c["ev"]["reading"]
    return "%s = %g %s (quality %s)" % (_h(r["measurement_type"]), r["value"], r["unit"], r["quality"])


B_CRIT, B_LOW, B_WATCH = P.BATTERY_CRITICAL, P.BATTERY_LOW, P.BATTERY_WATCH
CRITICAL_ASSET = "an asset of HIGH or CRITICAL criticality"

RULES: List[Rule] = [
    # ── action events: P1 ────────────────────────────────────────────────────────────────────
    Rule("anomaly_critical", "action", "P1", "Critical anomaly",
         "Any anomaly with severity CRITICAL is priority P1 and is escalated to System 2 immediately, whatever "
         "the asset's criticality. Category: equipment if the anomaly is an equipment anomaly (abnormal vibration, "
         "abnormal temperature, gauge out of range, visual defect).",
         lambda c: c["sev"] == 4, lambda c: "CRITICAL anomaly: " + _anom(c)),
    Rule("anomaly_high_on_critical_asset", "action", "P1", "High-severity anomaly on a critical asset",
         "An anomaly with severity HIGH on %s is priority P1 and is escalated. Consequence (asset criticality) "
         "times urgency (anomaly severity), as in ISA-18.2 alarm rationalization." % CRITICAL_ASSET,
         lambda c: c["sev"] == 3 and c["crit"] >= 3, lambda c: "HIGH anomaly on a critical asset: " + _anom(c)),
    Rule("failed_at_critical_battery", "action", "P1", "Action failed at critical battery",
         "An action that FAILED while SPOT's battery was at or below %d%% is priority P1 and is escalated: the "
         "robot may not make it back to the dock. Kit evidence: action success drops to about 33%% at or below "
         "%d%% battery versus 80-90%% above it (the battery cliff)." % (B_CRIT, B_LOW),
         lambda c: c["failed"] and c["batt"] <= B_CRIT,
         lambda c: "action failed at %d%% battery (critical <= %d%%)" % (c["batt"], B_CRIT)),
    Rule("comms_loss_low_battery", "action", "P1", "Communication loss at low battery",
         "A COMMUNICATION_LOSS failure while battery is at or below %d%% is priority P1 and is escalated "
         "(category robot_health): the operator can neither see nor recover the robot." % B_LOW,
         lambda c: c["ft"] in P.COMMS_FAILURES and c["batt"] <= B_LOW,
         lambda c: "communication loss at %d%% battery (low <= %d%%)" % (c["batt"], B_LOW)),
    # ── action events: P2 ────────────────────────────────────────────────────────────────────
    Rule("anomaly_high", "action", "P2", "High-severity anomaly",
         "Any anomaly with severity HIGH is at least priority P2 and is escalated to System 2. On %s it "
         "becomes P1 (rule anomaly_high_on_critical_asset)." % CRITICAL_ASSET,
         lambda c: c["sev"] == 3, lambda c: "HIGH anomaly: " + _anom(c)),
    Rule("anomaly_medium_on_critical_asset", "action", "P2", "Medium anomaly on a critical asset",
         "An anomaly with severity MEDIUM on %s is priority P2 and is escalated." % CRITICAL_ASSET,
         lambda c: c["sev"] == 2 and c["crit"] >= 3, lambda c: "MEDIUM anomaly on a critical asset: " + _anom(c)),
    Rule("failed_on_critical_asset", "action", "P2", "Failed action on a critical asset",
         "Any FAILED action (navigation, data or communication failure) on %s is priority P2 and is escalated: "
         "a critical asset went uninspected." % CRITICAL_ASSET,
         lambda c: c["failed"] and c["crit"] >= 3,
         lambda c: "%s failed (%s) on %s" % (_h(c["ev"]["action_type"]), _h(c["ft"] or "unknown"), _asset(c))),
    Rule("battery_low", "action", "P2", "Low battery",
         "Any action with battery at or below %d%% is at least priority P2 and is escalated (the battery cliff: "
         "kit action success is about 33%% at or below %d%%, 80-90%% above). At or below %d%% a failure becomes "
         "P1 (failed_at_critical_battery)." % (B_LOW, B_LOW, B_CRIT),
         lambda c: c["batt"] <= B_LOW,
         lambda c: "battery %d%% (low <= %d%%; kit: ~33%% action success at <= %d%%)" % (c["batt"], B_LOW, B_LOW)),
    Rule("equipment_reading_out_of_band", "action", "P2", "Trusted equipment reading out of its safe band",
         "A trusted reading (quality GOOD, action succeeded, physically plausible) outside its safe operating band "
         "on an asset of MEDIUM or higher criticality is priority P2 and is escalated (category equipment). "
         "Applies to temperature, pressure, sound and visual-score readings; localization confidence is a "
         "navigation signal instead (see safe_bands).",
         lambda c: c["equip_band"] and c["crit"] >= 2,
         lambda c: "reading out of safe band on %s: %s" % (_asset(c), _reading(c))),
    # ── action events: P3 (logged, not escalated) ────────────────────────────────────────────
    Rule("anomaly_present", "action", "P3", "Anomaly raised",
         "Any anomaly (LOW or MEDIUM included) makes an action at least priority P3: shown to the operator, "
         "not escalated to System 2 unless a P1/P2 rule also fires.",
         lambda c: c["sev"] >= 1, lambda c: "anomaly: " + _anom(c)),
    Rule("action_failed", "action", "P3", "Action failed",
         "Any FAILED action is at least priority P3. Failure modes: navigation (localization failure, obstacle "
         "detection, path blocked), data_quality (sensor timeout, reading unreliable, signal noise, target not "
         "detected), robot_health (communication loss).",
         lambda c: c["failed"],
         lambda c: "%s failed: %s" % (_h(c["ev"]["action_type"]), _h(c["ft"] or "unknown"))),
    Rule("reading_untrusted", "action", "P3", "Untrusted reading",
         "A reading is untrusted if its quality is not GOOD, if the action FAILED, or if the value is physically "
         "implausible (see reading_trust). An untrusted reading makes the action at least P3 (category "
         "data_quality) and must not be treated as a real equipment value.",
         lambda c: c["trust"] == "untrusted", lambda c: "untrusted reading: " + _reading(c)),
    Rule("battery_watch", "action", "P3", "Battery on watch",
         "Battery at or below %d%% (but above %d%%) makes an action at least P3 (category robot_health if nothing "
         "else applies): plan the return to dock." % (B_WATCH, B_LOW),
         lambda c: c["batt"] <= B_WATCH, lambda c: "battery %d%% (watch <= %d%%)" % (c["batt"], B_WATCH)),
    Rule("reading_out_of_band", "action", "P3", "Trusted reading out of its safe band",
         "Any trusted reading outside its safe band is at least P3. Localization confidence below its band means "
         "category navigation; other measurements mean category equipment (P2 on MEDIUM+ criticality assets).",
         lambda c: c["out_band"], lambda c: "reading out of safe band: " + _reading(c)),
    # ── mission events ───────────────────────────────────────────────────────────────────────
    Rule("mission_reported_failed", "mission", "P2", "Mission reported FAILED",
         "A mission whose reported status is FAILED is priority P2 and is escalated.",
         lambda c: c["ev"]["reported_status"] == "FAILED",
         lambda c: "mission reported FAILED (%d of %d actions failed)" % (c["ev"]["actions_failed"],
                                                                       c["ev"]["actions_total"])),
    Rule("mission_misleading_serious", "mission", "P2", "COMPLETED mission hides serious anomalies",
         "A mission reported COMPLETED that had failed actions or HIGH/CRITICAL anomalies is 'misleading'. If it "
         "had at least one HIGH or CRITICAL anomaly it is priority P2 and is escalated. Kit evidence: 21 of 26 "
         "COMPLETED missions hide failures.",
         lambda c: c["misleading"] and c["serious"] > 0,
         lambda c: "reported COMPLETED but had %d HIGH/CRITICAL anomalies and %d failed actions" % (
             c["serious"], c["ev"]["actions_failed"])),
    Rule("mission_misleading", "mission", "P3", "COMPLETED mission hides failures",
         "A mission reported COMPLETED with failed actions (but no HIGH/CRITICAL anomaly) is misleading and "
         "priority P3: shown to the operator, not escalated.",
         lambda c: c["misleading"],
         lambda c: "reported COMPLETED but %d of %d actions failed" % (c["ev"]["actions_failed"],
                                                                      c["ev"]["actions_total"])),
    Rule("mission_end_battery_low", "mission", "P3", "Mission ended at low battery",
         "A mission that ended with battery at or below %d%% is at least P3." % B_LOW,
         lambda c: c["ev"]["end_battery_pct"] <= B_LOW,
         lambda c: "mission ended at %d%% battery (low <= %d%%)" % (c["ev"]["end_battery_pct"], B_LOW)),
]

REFERENCE: List[Rule] = [
    Rule("escalation", "reference", None, "Priorities and escalation",
         "System 1 assigns every action and mission event a priority. P1 and P2 are escalated to System 2 (the "
         "AMD-hosted LLM) for an explanation and a recommended action; P3 is shown to the operator but not "
         "escalated; P4 means nothing to report. An event's priority is the highest priority of the rules that "
         "fire. Modelled on ISA-18.2 alarm rationalization (consequence x urgency). Policy version %s."
         % P.POLICY_VERSION),
    Rule("safe_bands", "reference", None, "Safe operating bands for readings",
         "Safe bands for trusted (GOOD-quality) readings, set at about the 5th/95th percentile of the kit's GOOD "
         "readings: temperature %s C; pressure %s psi; sound %s dB; visual score %s (out of 100); localization "
         "confidence %s %%. A trusted reading outside its band is out_of_band (rules reading_out_of_band and "
         "equipment_reading_out_of_band)." % (_band("TEMPERATURE_C"), _band("PRESSURE_PSI"), _band("SOUND_DB"),
                                               _band("VISUAL_SCORE"), _band("LOCALIZATION_CONFIDENCE_PCT"))),
    Rule("reading_trust", "reference", None, "When a reading can be trusted",
         "A reading is trusted only if its quality is GOOD, the action succeeded, and the value is physically "
         "plausible: temperature %g to %g C, pressure %g to %g psi (the gauge face reads 0-300 psi), sound %g to "
         "%g dB, visual score %g to %g, localization confidence %g to %g %%. Anything else is untrusted: a sensor "
         "or capture problem, never a real equipment value." % (
             P.PLAUSIBLE["TEMPERATURE_C"] + P.PLAUSIBLE["PRESSURE_PSI"] + P.PLAUSIBLE["SOUND_DB"]
             + P.PLAUSIBLE["VISUAL_SCORE"] + P.PLAUSIBLE["LOCALIZATION_CONFIDENCE_PCT"])),
    Rule("category_assignment", "reference", None, "How a flag's category is chosen",
         "Categories are checked in order: equipment if the anomaly is abnormal vibration, abnormal temperature, "
         "gauge out of range or visual defect; robot_health if battery is at or below %d%% or the failure is a "
         "communication loss; navigation for localization failure, obstacle detection, path blocked, a navigation "
         "obstruction or localization issue anomaly, or localization confidence below its band; data_quality for "
         "sensor timeout, reading unreliable, signal noise, target not detected, signal degradation, or an "
         "untrusted reading; robot_health if battery is at or below %d%%; equipment for any other trusted reading "
         "out of band; otherwise none (P4)." % (B_CRIT, B_WATCH)),
    Rule("battery_thresholds", "reference", None, "Battery thresholds (the battery cliff)",
         "Battery thresholds: critical at or below %d%%, low at or below %d%%, watch at or below %d%%. In the "
         "kit, action success is about 33%% at or below %d%% battery versus 80-90%% above, and about 60%% of the "
         "V2 configuration's improvement comes from battery." % (B_CRIT, B_LOW, B_WATCH, B_LOW)),
]

ALL_RULES = RULES + REFERENCE
BY_NAME: Dict[str, Rule] = {r.name: r for r in ALL_RULES}


def evaluate(ev: dict) -> dict:
    """Rules that fire for a System 1 event, plus the implied priority, severity and score."""
    if ev["kind"] == "action":
        c, scope = action_context(ev), "action"
    elif ev["kind"] == "mission":
        c, scope = mission_context(ev), "mission"
    else:
        raise ValueError("only action and mission events are triaged, got %r" % ev["kind"])
    fired = [r for r in RULES if r.scope == scope and r.when(c)]
    fired.sort(key=lambda r: PRIO_ORDER[r.priority])
    priority = fired[0].priority if fired else "P4"
    reasons = [{"rule": r.name, "detail": r.detail(c), "weight": WEIGHT[r.priority], "priority": r.priority}
               for r in fired]
    # = backend validator.combine() with Laya unavailable: base + 9 * min(1, sum(weights) / 6), capped at 99.
    p = min(1.0, sum(WEIGHT[r.priority] for r in fired) / 6.0)
    score = min(99.0, BASE_SCORE[priority] + round(9 * p, 1))
    return {"priority": priority, "severity": FLAG_SEVERITY[priority], "score": score, "reasons": reasons}


def check_against_policy(ev: dict, result: dict) -> None:
    want = (P.label_action(ev) if ev["kind"] == "action" else P.label_mission(ev))["priority"]
    if result["priority"] != want:
        raise AssertionError("policy_rules drifted from policy.py on %s: rules say %s, policy says %s"
                             % (ev["event_id"], result["priority"], want))
