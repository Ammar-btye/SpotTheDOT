"""Committed JSON Schemas (amd/system2/schema/) must match analyst/contract.py exactly, in contract property order.

Run: uv run --no-project --with-requirements amd/system2/requirements.txt python -m pytest amd/system2/tests -q
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyst.contract import CONTRACT_VERSION, EXPLANATION_ORDER, NAIVE_ISO, AssessRequest  # noqa: E402
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
    props = _load("assess_response.schema.json")["$defs"]["Explanation"]["properties"]
    assert tuple(props) == EXPLANATION_ORDER


def test_schemas_forbid_extra():
    for name, _, _ in SCHEMAS:
        assert _load(name)["additionalProperties"] is False, name


def test_timestamp_schema_matches_runtime():
    ts = _load("flag.schema.json")["properties"]["timestamp"]
    assert ts["type"] == "string" and ts["pattern"] == NAIVE_ISO and "format" not in ts
    for p in sorted((ROOT / "fixtures").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        assert re.fullmatch(ts["pattern"], d["request"]["flag"]["timestamp"]), p.stem
        assert AssessRequest.model_validate_json(json.dumps(d["request"])) == AssessRequest.model_validate(d["request"])


def test_schemas_carry_generated_marker():
    for name, model, mode in SCHEMAS:
        d = _load(name)
        assert next(iter(d)) == "$comment", name
        assert CONTRACT_VERSION in d["$comment"], name
        assert render(model, mode) == (SCHEMA_DIR / name).read_text(encoding="utf-8"), name
