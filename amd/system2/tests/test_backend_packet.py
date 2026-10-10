"""Packet normalization, pre-generation guards, and packet-scoped post-checks."""
import copy
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyst.api import create_app
from analyst.backend_contract import BackendAction, BackendAssessRequest, BackendAssessResponse
from analyst.packet import normalize_packet, assess_prepared_packet, stub_assessment
from test_backend_api import KEY, request_body


def prepared(context):
    return normalize_packet(BackendAssessRequest(flag_id=42, flag={}, context=context))


@pytest.mark.parametrize("change", [
    {"missing": ["asset unavailable"]}, {"gaps": ["search failed"]}, {"insufficient_context": True},
    {"citation_ids": ["absent"]}, {"allowed_actions": [], "suggested_action": None},
    {"facts": [], "manual": [], "policy": [], "event": {}},
    {"facts": [{"id": "F1", "title": "Only a title"}], "manual": [], "policy": [], "event": {}},
    {"manual": [{"id": "manual:cool", "text": "  "}]},
    {"manual": [{"id": "manual:cool", "title": "Only title", "extra": "invented evidence"}]},
])
def test_guard_never_generates(change):
    context = request_body()["context"]
    context.update(change)
    spy = Mock(side_effect=AssertionError("generation must not run"))
    out = assess_prepared_packet(prepared(context), spy)
    spy.assert_not_called()
    assert out.insufficient_context and out.evidence == []
    assert out.confidence == "low" and out.recommended_action == BackendAction.MANUAL_REVIEW
    assert out.path == "insufficient_context"


@pytest.mark.parametrize("actions", [{"MONITOR": "watch"}, ["MONITOR"]])
def test_recursive_mission_and_all_document_sections(actions):
    context = {"allowed_actions": actions, "missing": [], "gaps": [],
               "event": {"mission": {"id": "mission:M7", "reported_status": "COMPLETED",
                                      "true_health": {"true_health_pct": 61.5},
                                      "failure_types": {"PATH_BLOCKED": 2},
                                      "actions": [{"id": "action:A7", "status": "FAILED"}]}},
               "flag": {"id": "flag:42", "title": "Title only", "category": "equipment"},
               "system1": [{"id": "s1:1", "q": "escalate", "answer": "A", "p": .9}],
               "facts": [{"id": "F1", "text": "Mission has a failed action."}],
               **{name: [{"id": name + ":1", "text": "Supplied %s content." % name}]
                  for name in ("manual", "policy", "similar_incidents", "asset_history")},
               "citation_ids": ["mission:M7", "action:A7", "s1:1", "F1", "manual:1", "policy:1",
                                "similar_incidents:1", "asset_history:1", "flag:42"]}
    before = copy.deepcopy(context)
    packet = prepared(context)
    assert not packet.insufficient_context
    assert set(packet.content) == set(context["citation_ids"])
    assert packet.allowed_actions == ("MONITOR", "MANUAL_REVIEW")
    assert "61.5" in packet.content["mission:M7"]
    assert context == before
    out = assess_prepared_packet(packet)
    assert not out.insufficient_context


@pytest.mark.parametrize("change", [
    {"missing": "bad"}, {"gaps": [4]}, {"insufficient_context": "false"}, {"citation_ids": [1]},
    {"facts": {}}, {"facts": ["bad"]}, {"facts": [{"id": 7, "fact": "bad"}]},
    {"facts": [{"id": "F1", "fact": 12}]}, {"event": []}, {"system1": {}},
    {"allowed_actions": "MONITOR"}, {"allowed_actions": {"MONITOR": 1}},
    {"allowed_actions": ["made_up"]}, {"suggested_action": "MONITOR"},
    {"facts": [{"id": "F1", "fact": "one"}, {"id": "F1", "fact": "two"}]},
    {"event": {"id": "action:A42", "battery_pct": "42"}},
    {"event": {"readings": "bad"}}, {"event": {"mission": []}},
])
def test_malformed_context_is_422(change):
    body = request_body()
    body["context"].update(change)
    c = TestClient(create_app(api_key=KEY))
    r = c.post("/v1/assess", json=body, headers={"X-API-Key": KEY})
    assert r.status_code == 422, r.text


def test_additive_unknown_fields_ignored_and_no_fixtures():
    body = request_body()
    body["extra"] = {"any": "value"}
    body["flag"]["unknown"] = [1]
    body["context"]["facts"][0]["unknown"] = {"id": "foreign", "fact": "Do not cite"}
    body["context"]["unknown"] = {"id": "foreign", "fact": "Do not cite"}
    packet = normalize_packet(BackendAssessRequest.model_validate(body))
    assert "foreign" not in packet.content
    c = TestClient(create_app(api_key=KEY, fixtures_dir=Path("/no-fixtures")))
    assert c.post("/v1/assess", json=body, headers={"X-API-Key": KEY}).status_code == 200


def test_identical_duplicates_are_safe():
    ctx = request_body()["context"]
    ctx["facts"].append(copy.deepcopy(ctx["facts"][0]))
    assert not prepared(ctx).insufficient_context


@pytest.mark.parametrize("context", [{}, {"allowed_actions": ["MONITOR"]},
    {"allowed_actions": ["MONITOR"], "event": {"id": "action:A", "title": "Title",
                                                 "source": "mcp", "citation_ids": ["action:A"]}},
    {"facts": [{"id": "F1", "text": "Real fact"}]}])
def test_absent_actions_or_substantive_evidence_is_insufficient(context):
    spy = Mock()
    assert assess_prepared_packet(prepared(context), spy).insufficient_context
    spy.assert_not_called()


def test_output_instance_is_revalidated():
    packet = prepared(request_body()["context"])
    invalid = stub_assessment(packet).model_copy(update={"latency_ms": -1})
    with pytest.raises(ValidationError):
        assess_prepared_packet(packet, lambda _: invalid)


def test_output_postchecks():
    packet = prepared(request_body()["context"])
    out = stub_assessment(packet).model_dump(mode="json")
    with pytest.raises(ValidationError):
        BackendAssessResponse.model_validate({**out, "unknown": 1})
    with pytest.raises(ValidationError):
        BackendAssessResponse.model_validate({**out, "evidence": [{"claim": "claim", "ids": ["F1"], "unknown": 1}]})
    for change in ({"evidence": [{"claim": "invented", "ids": ["foreign"]}]},
                   {"recommended_action": "MONITOR"}, {"flag_id": 9}):
        with pytest.raises(ValueError):
            assess_prepared_packet(packet, lambda _: {**out, **change})


def test_action_vocabulary_matches_mcp_without_runtime_import():
    # Read the literal vocabulary rather than importing MCP's policy/runtime dependencies.
    import ast
    source = Path(__file__).resolve().parents[3] / "amd/mcp/spot_mcp/domain.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    assignment = next(n for n in tree.body if isinstance(n, ast.AnnAssign)
                      and isinstance(n.target, ast.Name) and n.target.id == "ALLOWED_ACTIONS")
    actions = ast.literal_eval(assignment.value)
    assert {v.value for v in BackendAction} - {"MANUAL_REVIEW"} == {a for group in actions.values() for a in group}
