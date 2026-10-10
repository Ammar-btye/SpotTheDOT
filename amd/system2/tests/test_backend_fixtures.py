"""Representative backend packets are integration examples, not headline eval data."""
import ast
import copy
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analyst.api import create_app
from analyst.backend_contract import BackendAction, BackendAssessRequest, BackendAssessResponse
from analyst.packet import normalize_packet

FILES = sorted((ROOT / "fixtures/backend").glob("*.json"))
KEY = "backend-fixture-key-0123456789"


def test_backend_fixture_categories_present():
    assert {p.stem for p in FILES} >= {"equipment", "robot_health", "navigation"}


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_backend_pair_roundtrip(path):
    pair = json.loads(path.read_text())
    assert set(pair) == {"name", "description", "request", "response"}
    assert pair["name"] == path.stem
    assert "not headline" in pair["description"]
    request = BackendAssessRequest.model_validate(pair["request"])
    expected = BackendAssessResponse.model_validate(pair["response"])
    prepared = normalize_packet(request)
    for identifier in request.context.get("citation_ids", []):
        assert prepared.content.get(identifier), identifier
    client = TestClient(create_app(api_key=KEY))
    response = client.post("/v1/assess", json=pair["request"], headers={"X-API-Key": KEY})
    assert response.status_code == 200, response.text
    result = BackendAssessResponse.model_validate(response.json())
    assert result.flag_id == request.flag_id == expected.flag_id
    assert result.model == "stub"
    assert result.model_dump(exclude={"latency_ms"}) == expected.model_dump(exclude={"latency_ms"})
    assert result.recommended_action.value in prepared.allowed_actions
    for evidence in result.evidence:
        assert all(prepared.content.get(i) for i in evidence.ids)
        assert evidence.claim in [prepared.content[i] for i in evidence.ids]


def test_mcp_action_vocabulary_does_not_drift():
    # Read the authoritative constant without importing DB/MCP runtime dependencies.
    source = ROOT.parent / "mcp/spot_mcp/domain.py"
    tree = ast.parse(source.read_text())
    declaration = next(n for n in tree.body if isinstance(n, ast.AnnAssign)
                       and isinstance(n.target, ast.Name) and n.target.id == "ALLOWED_ACTIONS")
    categories = ast.literal_eval(declaration.value)
    codes = {code for actions in categories.values() for code in actions}
    assert {action.value for action in BackendAction} == codes | {"MANUAL_REVIEW"}
    for path in FILES:
        request = json.loads(path.read_text())["request"]
        if path.stem == "insufficient_context":
            continue
        actions = request["context"]["allowed_actions"]
        assert set(actions) == set(categories[request["flag"]["category"]])


@pytest.mark.parametrize("section", ["facts", "policy", "event"])
def test_equipment_cites_supplied_fact_document_and_event(section):
    pair = json.loads((ROOT / "fixtures/backend/equipment.json").read_text())
    request = copy.deepcopy(pair["request"])
    context = request["context"]
    # Make each original source the first available evidence in turn. The real
    # stub must cite doc_ids exactly as supplied, without prefix remapping.
    for name in ("facts", "policy", "event", "flag"):
        if name != section:
            context.pop(name, None)
    context.pop("citation_ids")
    prepared = normalize_packet(BackendAssessRequest.model_validate(request))
    identifier, content = next(iter(prepared.content.items()))
    client = TestClient(create_app(api_key=KEY))
    response = client.post("/v1/assess", json=request, headers={"X-API-Key": KEY})
    assert response.status_code == 200, response.text
    assert response.json()["evidence"] == [{"claim": content, "ids": [identifier]}]
    if section == "policy":
        assert identifier == "policy:anomaly_severity"
