"""Turn an event into the `state` Laya reads, in three renderings.

- json  : a compact dict (Laya serializes dicts with json.dumps). Closest to what the app sends.
- log   : a one-line machine log, the format robot telemetry usually arrives in.
- prose : an operator-style note with varied phrasing (seeded), to test reading beyond fixed formats.

Every rendering carries the same decision-relevant facts, so labels never depend on the rendering.
Renderings must fit Laya's state budget (~320 tokens on the English checkpoint); build_data checks this.
"""
import random
from typing import Any

RENDERINGS = ("json", "log", "prose")


def _h(s: str) -> str:
    """ACOUSTIC_INSPECTION -> acoustic inspection."""
    return s.replace("_", " ").lower()


UNIT_TXT = {"C": " C", "psi": " psi", "dB": " dB", "pct": "%", "score": "/100"}


def _reading_txt(r: dict) -> str:
    unit = UNIT_TXT.get(r["unit"], " " + r["unit"])
    return "%s %s%s (quality %s)" % (_h(r["measurement_type"]), _fmt(r["value"]), unit, r["quality"])


def _fmt(v: float) -> str:
    return ("%.1f" % v).rstrip("0").rstrip(".")


# ── json ─────────────────────────────────────────────────────────────────────────────────────
def render_json(ev: dict) -> dict:
    loc, asset = ev.get("location"), ev.get("asset")
    if ev["kind"] == "mission":
        d = {k: ev[k] for k in ("mission_id", "configuration_version", "timestamp", "reported_status",
                                "duration_min", "start_battery_pct", "end_battery_pct", "actions_total",
                                "actions_failed", "failure_types", "anomalies_by_severity")}
        d["event"] = "MISSION_COMPLETED"
        if ev["worst_anomaly"]:
            d["worst_anomaly"] = ev["worst_anomaly"]
        return d
    d = {
        "event": "ACTION_PLANNED" if ev["kind"] == "pre_action" else "ACTION_RESULT",
        "mission_id": ev["mission_id"], "configuration_version": ev["configuration_version"],
        "timestamp": ev["timestamp"], "step": ev["sequence"], "action_type": ev["action_type"],
        "battery_pct": ev["battery_pct"],
        "waypoint": {"id": loc["location_id"], "name": loc["location_name"], "zone": loc["zone_type"],
                     "environment": loc["environment"]},
        "asset": {"id": asset["asset_id"], "name": asset["asset_name"], "type": asset["asset_type"],
                  "criticality": asset["criticality"]},
    }
    if ev["kind"] == "pre_action":
        d["mission_so_far"] = ev["mission_so_far"]
        return d
    d["status"] = ev["status"]
    if ev["failure_type"]:
        d["failure_type"] = ev["failure_type"]
    if ev["reading"]:
        d["reading"] = ev["reading"]
    if ev["anomaly"]:
        d["anomaly"] = ev["anomaly"]
    return d


# ── log ──────────────────────────────────────────────────────────────────────────────────────
def render_log(ev: dict) -> str:
    if ev["kind"] == "mission":
        s = ev["anomalies_by_severity"]
        parts = ["%s MISSION_COMPLETED %s/%s status=%s" % (ev["timestamp"], ev["mission_id"],
                                                          ev["configuration_version"], ev["reported_status"]),
                 "dur=%dmin batt=%d%%->%d%%" % (ev["duration_min"], ev["start_battery_pct"], ev["end_battery_pct"]),
                 "actions=%d failed=%d" % (ev["actions_total"], ev["actions_failed"])]
        if ev["failure_types"]:
            parts.append("failure_types=" + ",".join(ev["failure_types"]))
        parts.append("anomalies L%d M%d H%d C%d" % (s["LOW"], s["MEDIUM"], s["HIGH"], s["CRITICAL"]))
        if ev["worst_anomaly"]:
            w = ev["worst_anomaly"]
            parts.append("worst=%s/%s on %s crit=%s" % (w["anomaly_type"], w["severity"], w["asset_name"],
                                                       w["asset_criticality"]))
        return " ".join(parts)
    loc, asset = ev["location"], ev["asset"]
    head = "%s %s %s/%s #%d %s %s [%s/%s] %s %s crit=%s %s batt=%d%%" % (
        ev["timestamp"], "PLAN" if ev["kind"] == "pre_action" else "RESULT", ev["mission_id"],
        ev["configuration_version"], ev["sequence"], loc["location_id"], loc["location_name"], loc["zone_type"],
        loc["environment"], asset["asset_id"], asset["asset_type"], asset["criticality"], ev["action_type"],
        ev["battery_pct"])
    if ev["kind"] == "pre_action":
        m = ev["mission_so_far"]
        tail = "done=%d fails_so_far=%d last=%s" % (m["actions_done"], m["failures_so_far"],
                                                    (m["last_status"] or "NONE") +
                                                    (":" + m["last_failure_type"] if m["last_failure_type"] else ""))
        return head + " " + tail
    parts = [head, ev["status"] + (" " + ev["failure_type"] if ev["failure_type"] else "")]
    if ev["reading"]:
        r = ev["reading"]
        parts.append("reading %s=%s%s q=%s" % (r["measurement_type"], _fmt(r["value"]), r["unit"], r["quality"]))
    if ev["anomaly"]:
        a = ev["anomaly"]
        parts.append("anomaly %s sev=%s \"%s\"" % (a["anomaly_type"], a["severity"], a["description"]))
    return " ".join(parts)


# ── prose ────────────────────────────────────────────────────────────────────────────────────
def render_prose(ev: dict, rng: random.Random) -> str:
    pick = rng.choice
    if ev["kind"] == "mission":
        s = ev["anomalies_by_severity"]
        txt = "%s %s (config %s) %s at %s with status %s after %d minutes; battery went from %d%% to %d%%. " % (
            pick(["Mission", "Autowalk mission", "SPOT mission"]), ev["mission_id"], ev["configuration_version"],
            pick(["ended", "finished", "wrapped up"]), ev["timestamp"], ev["reported_status"],
            ev["duration_min"], ev["start_battery_pct"], ev["end_battery_pct"])
        txt += "%d of %d actions failed" % (ev["actions_failed"], ev["actions_total"])
        txt += (" (%s). " % ", ".join(_h(f) for f in ev["failure_types"])) if ev["failure_types"] else ". "
        txt += "Anomalies: %d low, %d medium, %d high, %d critical." % (s["LOW"], s["MEDIUM"], s["HIGH"], s["CRITICAL"])
        if ev["worst_anomaly"]:
            w = ev["worst_anomaly"]
            txt += " Worst was %s (%s) on %s, a %s-criticality asset." % (
                _h(w["anomaly_type"]), w["severity"], w["asset_name"], w["asset_criticality"].lower())
        return txt
    loc, asset = ev["location"], ev["asset"]
    where = "%s (%s, %s zone, %s environment)" % (loc["location_name"], loc["location_id"], _h(loc["zone_type"]),
                                                   _h(loc["environment"]))
    prep = "to" if ev["action_type"] == "NAVIGATION" else "of"
    what = "%s %s %s (%s, %s criticality)" % (_h(ev["action_type"]), prep, asset["asset_name"], asset["asset_id"],
                                              asset["criticality"].lower())
    if ev["kind"] == "pre_action":
        m = ev["mission_so_far"]
        txt = "%s Mission %s (config %s), step %d at %s: SPOT is about to run a %s in %s. Battery is %d%%. " % (
            pick(["Planned:", "Up next:", "Queued:"]), ev["mission_id"], ev["configuration_version"],
            ev["sequence"], ev["timestamp"], what, where, ev["battery_pct"])
        if m["actions_done"] == 0:
            txt += "This is the first action of the mission."
        else:
            txt += "So far %d of %d actions failed" % (m["failures_so_far"], m["actions_done"])
            txt += "; the last one %s." % ("failed (" + _h(m["last_failure_type"]) + ")"
                                         if m["last_status"] == "FAILED" else "succeeded")
        return txt
    verb = {"SUCCESS": pick(["completed", "succeeded at", "finished"]), "FAILED": pick(["failed", "could not complete"])}
    txt = "Mission %s (config %s), step %d at %s: SPOT %s a %s in %s with %d%% battery." % (
        ev["mission_id"], ev["configuration_version"], ev["sequence"], ev["timestamp"], verb[ev["status"]], what,
        where, ev["battery_pct"])
    if ev["failure_type"]:
        txt += " Failure: %s." % _h(ev["failure_type"])
    txt += (" Reading: %s." % _reading_txt(ev["reading"])) if ev["reading"] else " No reading was recorded."
    if ev["anomaly"]:
        a = ev["anomaly"]
        txt += " Anomaly flagged: %s, severity %s (\"%s\")." % (_h(a["anomaly_type"]), a["severity"], a["description"])
    return txt


def render(ev: dict, how: str, rng: random.Random) -> Any:
    if how == "json":
        return render_json(ev)
    if how == "log":
        return render_log(ev)
    if how == "prose":
        return render_prose(ev, rng)
    raise ValueError("unknown rendering %r" % how)
