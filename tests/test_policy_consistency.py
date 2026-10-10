"""Cross-service drift guard for the triage rules (integration log 2026-10-10, seam 2).

The validator's rules live in several places on purpose (each image is self-contained):
  1. amd/system1/triage/policy.py            canonical: thresholds + label_action / label_mission
  2. db/policy_rules.py                       named rules -> seeded flags.reasons + `policy:<rule>` RAG docs
  3. backend/app/services/validator.py        named rules -> live flags.reasons (restates the predicates)
  4. amd/mcp/spot_mcp/vendor/policy.py        vendored copy the MCP image loads, + domain.band_check (a mirror of
                                              policy.reading_state that the MCP tools quote to System 2)

This runs all of them over every kit action and mission event (297) and fails on any threshold or verdict drift.
Runs with only the standard library + pytest (no DB, no models): `make test-policy`.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "amd" / "system1" / "data" / "kit"
VENDOR_POLICY = ROOT / "amd" / "mcp" / "spot_mcp" / "vendor" / "policy.py"
MCP_DOMAIN = ROOT / "amd" / "mcp" / "spot_mcp" / "domain.py"

for p in (ROOT / "amd" / "system1", ROOT / "db", ROOT / "backend"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from triage import events as T_events  # noqa: E402
from triage import kit as T_kit  # noqa: E402
from triage import policy as canon  # noqa: E402

import policy_rules as PR  # noqa: E402  (db/)
from app.services import validator as BV  # noqa: E402  (backend/)


def _load(name: str, path: Path, env: dict | None = None):
    old = {k: os.environ.get(k) for k in (env or {})}
    os.environ.update(env or {})
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


vendor = _load("mcp_vendor_policy", VENDOR_POLICY)
# Load the MCP domain module the way the container does: with the vendored policy.
mcp_domain = _load("mcp_domain_under_test", MCP_DOMAIN, {"POLICY_PATH": str(VENDOR_POLICY)})

THRESHOLDS = ("POLICY_VERSION", "SEV", "CRIT", "BATTERY_CRITICAL", "BATTERY_LOW", "BATTERY_WATCH", "SAFE_BANDS",
              "PLAUSIBLE", "NAV_FAILURES", "DATA_FAILURES", "COMMS_FAILURES", "EQUIPMENT_ANOMALIES",
              "NAV_ANOMALIES", "DATA_ANOMALIES")


def kit_events():
    k = T_kit.load_kit(KIT)
    out = []
    for mid, m in k.missions.items():
        for e in T_events.mission_events(m, k.actions_of(mid), k.locations, k.assets, k.readings, k.anomalies, "kit"):
            if e["kind"] != "pre_action":
                out.append(e)
    return out


EVENTS = kit_events()


def test_kit_has_all_triaged_events():
    assert len(EVENTS) == 297


@pytest.mark.parametrize("name", THRESHOLDS)
def test_thresholds_identical(name):
    assert getattr(vendor, name) == getattr(canon, name), "vendored MCP policy.%s drifted" % name
    if name == "POLICY_VERSION":
        assert BV.POLICY_VERSION == canon.POLICY_VERSION
    # The MCP tools quote these to System 2.
    for attr in ("BATTERY_CRITICAL", "BATTERY_LOW", "BATTERY_WATCH", "SAFE_BANDS", "PLAUSIBLE"):
        assert getattr(mcp_domain, attr) == getattr(canon, attr), "mcp domain.%s drifted" % attr


def test_mcp_domain_loads_the_vendored_policy():
    assert mcp_domain.POLICY_SOURCE.startswith("vendored-policy.py@"), mcp_domain.POLICY_SOURCE


def test_flag_severity_maps_agree():
    """Seeded flags (db) and live flags (backend) must map a priority to the same flags.severity."""
    assert PR.FLAG_SEVERITY == BV.SEVERITY_OF


def test_verdicts_agree_on_every_kit_event():
    drift = []
    for e in EVENTS:
        eid, kind = e["event_id"], e["kind"]
        want = canon.label_action(e) if kind == "action" else canon.label_mission(e)
        # 4. MCP vendored copy: the full label dict
        got_v = vendor.label_action(e) if kind == "action" else vendor.label_mission(e)
        if got_v != want:
            drift.append((eid, "mcp-vendor", got_v, want))
        # 2. db/policy_rules: top rule's priority (and therefore escalate)
        pr = PR.evaluate(e)
        if pr["priority"] != want["priority"]:
            drift.append((eid, "db.policy_rules.priority", pr["priority"], want["priority"]))
        if (pr["priority"] in ("P1", "P2")) != (want["escalate"] == "A"):
            drift.append((eid, "db.policy_rules.escalate", pr["priority"], want["escalate"]))
        # 3. backend validator: escalate / priority / category, top tier, and the fired rule names vs db
        bv = BV.rules_verdict(kind, e)
        if bv["escalate"] != (want["escalate"] == "A") or bv["priority"] != want["priority"]:
            drift.append((eid, "backend.verdict", (bv["escalate"], bv["priority"]), want))
        if kind == "action" and bv["category"] != want["category"]:
            drift.append((eid, "backend.category", bv["category"], want["category"]))
        top = bv["rules"][0]["tier"] if bv["rules"] else "P4"
        if top != want["priority"]:
            drift.append((eid, "backend.top_rule", top, want["priority"]))
        names_b = sorted(r["rule"] for r in bv["rules"])
        names_d = sorted(r["rule"] for r in pr["reasons"])
        if names_b != names_d:
            drift.append((eid, "backend-vs-db.rule_names", names_b, names_d))
    assert not drift, "%d drifts, first: %s" % (len(drift), drift[:5])


def test_mcp_band_check_mirrors_reading_state():
    n = 0
    for e in EVENTS:
        r = e.get("reading") if e["kind"] == "action" else None
        if not r:
            continue
        trust, out_band = canon.reading_state(e)
        b = mcp_domain.band_check(r["measurement_type"], r["value"], r["quality"], e["status"])
        assert b["trust"] == trust, (e["event_id"], b, trust)
        if trust == "trusted":
            assert b["in_safe_band"] is (not out_band), (e["event_id"], b, out_band)
        n += 1
    assert n > 100


def test_seeded_and_live_flags_share_score_and_detail_texts():
    """Audit M11 + rule-detail drift: db/policy_rules.py (seeded flags) must give the same flags.score,
    flags.severity and per-rule detail text as the backend validator (live flags, canonical) when Laya is
    unavailable, for every kit event."""
    drift = []
    for e in EVENTS:
        kind = e["kind"]
        pr = PR.evaluate(e)
        bv = BV.rules_verdict(kind, e)
        for mode in ("serial", "parallel"):
            d = BV.combine(mode, None, bv, kind)
            if (float(pr["score"]), pr["severity"]) != (float(d["score"]), d["severity"]):
                drift.append((e["event_id"], mode, "score/severity", (pr["score"], pr["severity"]),
                              (d["score"], d["severity"])))
        db_details = {r["rule"]: r["detail"] for r in pr["reasons"]}
        be_details = {r["rule"]: r["detail"] for r in bv["rules"]}
        if db_details != be_details:
            diff = {k: (db_details.get(k), be_details.get(k)) for k in set(db_details) | set(be_details)
                    if db_details.get(k) != be_details.get(k)}
            drift.append((e["event_id"], "detail", diff))
    assert not drift, "%d drifts, first: %s" % (len(drift), drift[:3])


@pytest.mark.parametrize("quality", [None, "QUESTIONABLE", "POOR", ""])
def test_mcp_band_check_untrusted_unless_good(quality):
    """policy.reading_state: any quality other than GOOD (a missing one included) is untrusted."""
    ev = {"status": "SUCCESS", "reading": {"measurement_type": "PRESSURE_PSI", "value": 100.0, "quality": quality}}
    assert canon.reading_state(ev)[0] == "untrusted"
    assert mcp_domain.band_check("PRESSURE_PSI", 100.0, quality, "SUCCESS")["trust"] == "untrusted"


def test_mcp_battery_status_uses_policy_cliffs():
    f = mcp_domain.battery_status if hasattr(mcp_domain, "battery_status") else None
    if f is None:
        pytest.skip("mcp domain has no battery_status()")
    assert f(canon.BATTERY_CRITICAL) != f(canon.BATTERY_CRITICAL + 1)
    assert f(canon.BATTERY_LOW) != f(canon.BATTERY_LOW + 1)
    assert f(canon.BATTERY_WATCH) != f(canon.BATTERY_WATCH + 1)
    assert f(canon.BATTERY_WATCH + 1) == "OK"
