"""Contract invariant tests: schema field order, citations exist, action allowed, insufficient_context honest.

Every negative test starts from the real equipment fixture and breaks exactly one thing.
Run: uv run --no-project --with-requirements amd/system2/requirements.txt python -m pytest amd/system2/tests -q
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from analyst.api import FIXTURES  # noqa: E402
from analyst.contract import (EXPLANATION_ORDER, AssessRequest, AssessResponse, ContextPacket,  # noqa: E402
                              Explanation, Flag, Meta)

EQUIP = json.loads((FIXTURES / "equipment.json").read_text(encoding="utf-8"))
FORBIDDEN = {"severity", "severity_assessment", "priority", "escalate", "category"}


def _resp() -> dict:
    return copy.deepcopy(EQUIP["response"])


def _flag() -> dict:
    return copy.deepcopy(EQUIP["request"]["flag"])


def _bad(model, d):
    with pytest.raises(ValidationError):
        model.model_validate(d)


# ── schema shape ─────────────────────────────────────────────────────────────

def test_fixture_valid():
    AssessRequest.model_validate(EQUIP["request"])
    AssessResponse.model_validate(EQUIP["response"])


def test_models_export_json_schema():
    for m in (Flag, ContextPacket, Explanation, AssessRequest, AssessResponse):
        s = m.model_json_schema()
        assert isinstance(s, dict) and s.get("properties"), m.__name__


def test_explanation_field_order():
    assert tuple(Explanation.model_json_schema()["properties"]) == EXPLANATION_ORDER


def test_no_reprioritize_fields():
    for m in (Explanation, Meta, AssessResponse):
        assert not FORBIDDEN & set(m.model_json_schema()["properties"]), m.__name__


def test_ids_order():
    p = ContextPacket.model_validate(_resp()["packet"])
    assert p.ids() == ["E1", "E2", "E3", "F1", "F2", "F3", "S1", "S2", "W1", "W2", "I1", "I2", "I3"]


# ── AssessResponse ───────────────────────────────────────────────────────────

def test_unknown_citation_rejected():
    d = _resp()
    d["explanation"]["evidence"][0]["ids"] = ["F9"]
    _bad(AssessResponse, d)


def test_action_not_allowed_rejected():
    d = _resp()
    d["explanation"]["recommended_action"] = "recharge_robot"
    _bad(AssessResponse, d)


def test_insufficient_true_without_missing_rejected():
    d = _resp()
    d["explanation"].update(insufficient_context=True, recommended_action="manual_review")
    _bad(AssessResponse, d)


def test_insufficient_false_with_missing_rejected():
    d = _resp()
    d["packet"]["incidents"] = []
    d["packet"]["missing"] = ["incidents"]
    _bad(AssessResponse, d)


def test_insufficient_consistent_accepted():
    d = _resp()
    d["packet"]["incidents"] = []
    d["packet"]["missing"] = ["incidents"]
    d["explanation"].update(evidence=[], insufficient_context=True, recommended_action="manual_review")
    AssessResponse.model_validate(d)


def test_response_flag_id_mismatch_rejected():
    d = _resp()
    d["flag_id"] = "flag:act-A0010"
    _bad(AssessResponse, d)


# ── Explanation ──────────────────────────────────────────────────────────────

def test_insufficient_requires_manual_review():
    e = _resp()["explanation"]
    e.update(evidence=[], insufficient_context=True)          # still dispatch_technician
    _bad(Explanation, e)


def test_sufficient_requires_evidence():
    e = _resp()["explanation"]
    e["evidence"] = []
    _bad(Explanation, e)


# ── ContextPacket ────────────────────────────────────────────────────────────

def test_row_in_wrong_section_rejected():
    p = _resp()["packet"]
    p["facts"].append(copy.deepcopy(p["asset"][0]))           # S1 under facts
    _bad(ContextPacket, p)


def test_duplicate_row_id_rejected():
    p = _resp()["packet"]
    p["facts"].append(dict(p["facts"][0], text="another F1"))
    _bad(ContextPacket, p)


def test_allowed_actions_not_subset_rejected():
    p = _resp()["packet"]
    p["allowed_actions"].append("recharge_robot")
    _bad(ContextPacket, p)


def test_allowed_actions_duplicate_rejected():
    p = _resp()["packet"]
    p["allowed_actions"].append("monitor")
    _bad(ContextPacket, p)


def test_allowed_actions_require_manual_review():
    p = _resp()["packet"]
    p["allowed_actions"].remove("manual_review")
    _bad(ContextPacket, p)
    p["allowed_actions"] = ["dispatch_technician"]
    _bad(ContextPacket, p)


def test_allowed_actions_monitor_optional():
    p = _resp()["packet"]
    p["allowed_actions"].remove("monitor")
    ContextPacket.model_validate(p)


def test_fixtures_offer_manual_review():
    for path in sorted(FIXTURES.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        assert "manual_review" in d["response"]["packet"]["allowed_actions"], path.stem


def test_validator_action_outside_allowed_rejected():
    p = _resp()["packet"]
    p["allowed_actions"].remove("dispatch_technician")
    _bad(ContextPacket, p)


def test_missing_section_with_rows_rejected():
    p = _resp()["packet"]
    p["missing"] = ["asset"]
    _bad(ContextPacket, p)


def test_missing_duplicate_rejected():
    p = _resp()["packet"]
    p["incidents"] = []
    p["missing"] = ["incidents", "incidents"]
    _bad(ContextPacket, p)


# ── Flag ─────────────────────────────────────────────────────────────────────

def test_action_flag_needs_action_id():
    f = _flag()
    f["action_id"] = None
    _bad(Flag, f)


def test_mission_flag_rejects_action_id():
    f = _flag()
    f.update(kind="mission", category="mission_health", event_id="mis-M001")
    _bad(Flag, f)


def test_mission_flag_needs_mission_health():
    f = _flag()
    f.update(kind="mission", action_id=None, event_id="mis-M001")    # category stays equipment
    _bad(Flag, f)


def test_action_flag_rejects_mission_health():
    f = _flag()
    f["category"] = "mission_health"
    _bad(Flag, f)


def test_mission_flag_accepted():
    f = _flag()
    f.update(kind="mission", category="mission_health", action_id=None, event_id="mis-M001")
    Flag.model_validate(f)
