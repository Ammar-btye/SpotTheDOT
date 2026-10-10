"""Backend transport tracer: authenticate first and assess only supplied evidence."""
import sys
import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyst.api import create_app

KEY = "backend-test-key-123456"


def request_body():
    return {"flag_id": 42, "flag": {"category": "equipment", "flag_id": 42},
            "event": {"event_id": "e-42"}, "reasons": ["Hot bearing", None],
            "context": {"facts": [{"id": "F1", "fact": "Bearing temperature is 94 C."}],
                        "manual": [{"id": "manual:cool", "text": "Inspect the bearing."}],
                        "policy": [{"id": "policy:hot", "text": "Dispatch for overheating."}],
                        "event": {"id": "action:A42", "status": "FAILED"},
                        "citation_ids": ["F1", "manual:cool", "policy:hot", "action:A42"],
                        "allowed_actions": {"DISPATCH_TECHNICIAN": "send technician"},
                        "suggested_action": "DISPATCH_TECHNICIAN", "question": "What needs attention?"}}


def test_backend_equipment_request():
    client = TestClient(create_app(api_key=KEY))
    r = client.post("/v1/assess", json=request_body(), headers={"X-API-Key": KEY})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["flag_id"] == 42
    assert out["answer"] == "Bearing temperature is 94 C."
    assert out["evidence"] == [{"claim": out["answer"], "ids": ["F1"]}]
    assert out["recommended_action"] == "DISPATCH_TECHNICIAN"
    assert out["model"] == "stub"
    assert "packet" not in out
    # Execute the actual pure backend normalizer without importing its DB client dependencies.
    source = Path(__file__).resolve().parents[3] / "backend/app/services/system2.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "normalize_assessment")
    namespace = {}
    exec("from __future__ import annotations\n" + ast.unparse(function), namespace)
    stored = namespace["normalize_assessment"](out)
    assert stored["answer"] == out["answer"]
    assert "F1" in stored["reasoning"]


@pytest.mark.parametrize("key", [None, "wrong"])
def test_key_precedes_parsing(key):
    c = TestClient(create_app(api_key=KEY))
    headers = {"X-API-Key": key} if key else {}
    assert c.post("/v1/assess", content="{", headers=headers).status_code == 401


@pytest.mark.parametrize("field,value", [("flag_id", True), ("flag_id", "42"), ("flag_id", 0),
                                        ("flag", []), ("context", []), ("reasons", [12]), ("event", "bad")])
def test_consumed_types(field, value):
    body = request_body()
    body[field] = value
    c = TestClient(create_app(api_key=KEY))
    assert c.post("/v1/assess", json=body, headers={"X-API-Key": KEY}).status_code == 422
