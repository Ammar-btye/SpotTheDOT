"""Fixture-set tests: every fixtures/*.json pair is contract-valid, grounded in its own packet, drawn from a training
mission only (T-01-08). Public HTTP round trips live in test_backend_fixtures.py.

Grounding (T-01-09): fixtures model grounded output. Numbers are matched only against packet row values (`Row.data`)
and row text, never the flag, `ref`, timestamps, dates/policy versions or IDs (A0009, M015, HX-208, WP03, act-...),
whose digits would otherwise "ground" almost any small number. Each claim's numbers must come from the rows it cites;
the answer and question may use any row. A number written as a percent must match a percent in the rows (row text
"22%" or a `*pct*` data field), a step number must match a step/sequence, and signs count (-5 is not 5). Asset names
with numbers ("Heat Exchanger 08") must appear in the rows verbatim. test_grounding_catches_ungrounded proves the
checker rejects, e.g., "battery at 9%" on the equipment fixture (9 appears there only as step 9 and inside IDs).

Run: uv run --no-project --with-requirements amd/system2/requirements.txt python -m pytest amd/system2/tests -q
"""
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from analyst.api import FIXTURES  # noqa: E402
from analyst.contract import CATEGORIES, CONTRACT_VERSION, SECTIONS, AssessRequest, AssessResponse  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]                         # amd/system2
MANIFEST = ROOT.parent / "system1" / "data" / "manifest.json"      # System 1's mission-level split

FIXTURE_FILES = sorted(FIXTURES.glob("*.json"))
ROW_ID = re.compile(r"\b[EFSWI][1-9][0-9]?\b")
STEP = re.compile(r"\bstep[- ]?(\d+)", re.I)                         # mission step = action sequence, an ordinal
NOISE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T[\d:.]+|\.\d+)?"           # dates, timestamps, policy 2026-10-10.1
                   r"|\b(?:act|mis|flag)[-:]\S+"                        # event and flag IDs
                   r"|\b[A-Z]{1,5}-?\d{2,4}\b")                         # kit IDs: A0009, M015, AN009, HX-208, WP03
NAME = re.compile(r"\b[A-Z][a-z]+ \d{2}\b(?!%|\.\d)")                     # asset/route names: (Heat) Exchanger 08
NUMBER = re.compile(r"(?<![\w.])(-?\d+(?:\.\d+)?)(%?)")                # "-" counts only as a sign, not in "HX-208"
ASSET_ID = re.compile(r"\b[A-Z]{2,5}-\d{3}\b")
WAYPOINT_ID = re.compile(r"\bWP\d{2}\b")


def _load(p: Path) -> dict:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _holdout() -> set:
    hold = set(_load(MANIFEST)["holdout_missions"])
    assert hold, "manifest %s lists no holdout_missions" % MANIFEST
    return hold


def _texts(expl: dict) -> list:
    return [ev["claim"] for ev in expl["evidence"]] + [expl["answer"], expl["question"]]


def _scan(text: str) -> tuple:
    """(numbers, percents, steps) in text, with row IDs, kit IDs, timestamps and asset names stripped first."""
    steps = {float(n) for n in STEP.findall(text)}
    t = NAME.sub(" ", NOISE.sub(" ", STEP.sub(" ", ROW_ID.sub(" ", text))))
    found = NUMBER.findall(t)
    return {float(n) for n, _ in found}, {float(n) for n, p in found if p}, steps


def _facts(rows) -> tuple:
    """(numbers, percents, steps, text) that packet rows ground: Row.data values and Row.text, never flag or ref."""
    nums, pct, steps, texts = set(), set(), set(), []
    for r in rows:
        strs = [r["text"]]
        for k, v in r.get("data", {}).items():
            if k == "sequence" and isinstance(v, int) and not isinstance(v, bool):
                steps.add(float(v))
            elif isinstance(v, bool) or v is None or k.endswith("_id"):
                continue
            elif isinstance(v, (int, float)):
                nums.add(float(v))
                if "pct" in k:
                    pct.add(float(v))
            else:
                strs.append(v)
        for s in strs:
            n, p, st = _scan(s)
            nums, pct, steps = nums | n, pct | p, steps | st
            texts.append(s)
    return nums, pct, steps, "\n".join(texts)


def _ungrounded(resp: dict) -> list:
    """[(where, kind, value)] for every explanation number, percent, step or asset name its packet rows lack."""
    pk, ex = resp["packet"], resp["explanation"]
    rows = {r["id"]: r for sec in SECTIONS for r in pk[sec]}
    every = _facts(rows.values())
    checks = [("claim %d" % i, ev["claim"], _facts([rows[j] for j in ev["ids"]]))
              for i, ev in enumerate(ex["evidence"])]
    checks += [("answer", ex["answer"], every), ("question", ex["question"], every)]
    out = []
    for where, text, (nums, pct, steps, _) in checks:
        n, p, st = _scan(text)
        out += [(where, "number", x) for x in sorted(n - nums)]
        out += [(where, "percent", x) for x in sorted(p - pct)]
        out += [(where, "step", x) for x in sorted(st - steps)]
        out += [(where, "name", m) for m in NAME.findall(STEP.sub(" ", text)) if m not in every[3]]
    return out


def test_fixture_files_present():
    assert FIXTURE_FILES, "no fixtures in %s" % FIXTURES


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.stem)
def test_pair_validates(path):
    d = _load(path)
    req = AssessRequest.model_validate(d["request"])
    resp = AssessResponse.model_validate(d["response"])
    assert d["name"] == path.stem
    assert resp.contract_version == CONTRACT_VERSION
    assert resp.packet.flag == req.flag
    assert d["response"]["packet"]["flag"] == d["request"]["flag"]


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.stem)
def test_training_missions_only(path):
    hold = _holdout()
    d = _load(path)
    flag = d["request"]["flag"]
    assert flag["split"] == "train", (path.stem, flag["split"])
    assert flag["mission_id"] not in hold, (path.stem, flag["mission_id"])
    for row in d["response"]["packet"]["incidents"]:
        assert row["data"].get("mission_id") not in hold, (path.stem, row["id"], row["data"].get("mission_id"))


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.stem)
def test_explanation_grounded(path):
    d = _load(path)
    assert not _ungrounded(d["response"]), (path.stem, _ungrounded(d["response"]))
    packet_text = json.dumps(d["response"]["packet"])
    for text in _texts(d["response"]["explanation"]):
        ids = ASSET_ID.findall(text) + WAYPOINT_ID.findall(text)
        absent = [i for i in ids if i not in packet_text]
        assert not absent, (path.stem, "asset/waypoint IDs not in packet", absent, text)


EQUIP_RESP = _load(FIXTURES / "equipment.json")["response"]


@pytest.mark.parametrize("where,text", [
    ("claim", "SPOT was at 9% battery when the inspection failed."),   # 9 only as step 9 and in A0009 / AN009
    ("answer", "Send a technician now: SPOT was at 9% battery."),
    ("claim", "The inspection ran at 61% battery."),                   # 61 is the duration in seconds, not a percent
    ("claim", "Battery changed by -22% before the inspection."),       # the packet has 22, not -22
    ("answer", "This has been the pattern since 2026."),               # 2026 only in timestamps / the policy version
    ("answer", "The defect recurred 40 times."),                       # 40 only inside the ID AN040
    ("claim", "Battery was 15% at the time."),                         # 15 is in W2 (11 of 15), not a cited row
    ("claim", "Step 7 failed with SENSOR_TIMEOUT at 22% battery."),    # the event is step 9
    ("answer", "Send a technician to Heat Exchanger 09."),             # the asset is Heat Exchanger 08
], ids=["pct9_claim", "pct9_answer", "duration_as_pct", "sign", "year", "id_digits", "uncited_row", "step",
        "asset_name"])
def test_grounding_catches_ungrounded(where, text):
    resp = copy.deepcopy(EQUIP_RESP)
    if where == "claim":
        resp["explanation"]["evidence"][2]["claim"] = text            # cites E1 (the action) and F2 (battery stats)
    else:
        resp["explanation"]["answer"] = text
    assert _ungrounded(resp), text


def test_grounding_accepts_grounded():
    resp = copy.deepcopy(EQUIP_RESP)
    resp["explanation"]["evidence"][2]["claim"] = "Step 9 ran at 22% battery for 61 s; at or below 25%, 8 of 24 passed."
    resp["explanation"]["answer"] = "Send a technician to Heat Exchanger 08 at WP03: 4 anomalies across 17 actions."
    assert _ungrounded(resp) == []


# ── coverage: what web can render ────────────────────────────────────────────

def _all() -> list:
    return [_load(p) for p in FIXTURE_FILES]


def test_one_fixture_per_category():
    cats = [d["request"]["flag"]["category"] for d in _all()
            if not d["response"]["explanation"]["insufficient_context"]]
    assert set(cats) == set(CATEGORIES), sorted(cats)
    assert len(cats) == len(set(cats)), sorted(cats)


def test_one_insufficient_fixture():
    ins = [d for d in _all() if d["response"]["explanation"]["insufficient_context"]]
    assert len(ins) == 1, [d["name"] for d in ins]
    resp = ins[0]["response"]
    assert resp["packet"]["missing"]
    assert resp["explanation"]["evidence"] == []
    assert resp["explanation"]["recommended_action"] == "manual_review"
    assert resp["meta"]["path"] == "insufficient_context"


def test_paths_cover_ui_states():
    assert {d["response"]["meta"]["path"] for d in _all()} == {"first_pass", "retry", "fallback", "insufficient_context"}
