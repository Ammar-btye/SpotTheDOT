"""Committed JSON Schemas (amd/system2/schema/) must match analyst/contract.py exactly, in contract property order.

Run: uv run --no-project --with-requirements amd/system2/requirements.txt python -m pytest amd/system2/tests -q
"""
import json
import re
import subprocess
import sys
import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyst.contract import CONTRACT_VERSION, EXPLANATION_ORDER, NAIVE_ISO, AssessRequest  # noqa: E402
from analyst.backend_contract import BACKEND_CONTRACT_VERSION, BackendAssessRequest, BackendAssessResponse  # noqa: E402
from analyst.api import create_app, KEY_HEADER  # noqa: E402
from scripts.export_schema import SCHEMAS, export, render  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schema"


def _load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def test_committed_schemas_current():
    assert export(SCHEMA_DIR, check=True) == []


def test_check_cli_exits_zero():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_schema.py"), "--check"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "%d schemas up to date" % len(SCHEMAS) in r.stdout


def test_check_flags_drift(tmp_path):
    export(tmp_path, check=False)
    p = tmp_path / SCHEMAS[0][0]
    p.write_text(p.read_text(encoding="utf-8").replace("Flag", "Flg", 1), encoding="utf-8")
    assert export(tmp_path, check=True) == [SCHEMAS[0][0]]


def test_response_schema_orders_explanation():
    props = _load("assess_response.schema.json")["properties"]
    assert tuple(props)[:6] == EXPLANATION_ORDER


def test_schemas_forbid_extra():
    for name, _, _, _ in SCHEMAS:
        if name == "assess_request.schema.json":
            assert _load(name).get("additionalProperties") is not False
            continue
        assert _load(name)["additionalProperties"] is False, name


def test_timestamp_schema_matches_runtime():
    ts = _load("flag.schema.json")["properties"]["timestamp"]
    assert ts["type"] == "string" and ts["pattern"] == NAIVE_ISO and "format" not in ts
    for p in sorted((ROOT / "fixtures").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        assert re.fullmatch(ts["pattern"], d["request"]["flag"]["timestamp"]), p.stem
        assert AssessRequest.model_validate_json(json.dumps(d["request"])) == AssessRequest.model_validate(d["request"])


def test_schemas_carry_generated_marker():
    for name, model, mode, version in SCHEMAS:
        d = _load(name)
        assert next(iter(d)) == "$comment", name
        assert version in d["$comment"], name
        expected_version = BACKEND_CONTRACT_VERSION if name.startswith("assess_") else CONTRACT_VERSION
        assert version == expected_version
        assert render(model, mode, version) == (SCHEMA_DIR / name).read_text(encoding="utf-8"), name


def test_equipment_http_matches_published_models():
    pair = json.loads((ROOT / "fixtures/backend/equipment.json").read_text(encoding="utf-8"))
    BackendAssessRequest.model_validate(pair["request"])
    key = "schema-test-key-0123456789abcdef"
    with TestClient(create_app(api_key=key)) as client:
        response = client.post("/v1/assess", json=pair["request"], headers={KEY_HEADER: key})
    assert response.status_code == 200, response.text
    BackendAssessResponse.model_validate(response.json())
    for filename, model, mode in (("assess_request.schema.json", BackendAssessRequest, "validation"),
                                  ("assess_response.schema.json", BackendAssessResponse, "serialization")):
        schema = _load(filename)
        schema.pop("$comment")
        assert schema == model.model_json_schema(mode=mode)
