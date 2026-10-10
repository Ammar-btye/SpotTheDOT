"""Fixture-set tests: every fixtures/*.json pair is contract-valid, grounded in its own packet, drawn from a training
mission only (T-01-08), and served schema-valid by the stub (ROADMAP Phase 1 criteria 2 and 3).

Grounding (T-01-09): fixtures model grounded output, so every number and every asset/waypoint ID in the explanation's
claims, answer and question must appear in the fixture's own packet. Row IDs (E1, F2, ...) are stripped first.

Run: uv run --no-project --with-requirements amd/system2/requirements.txt python -m pytest amd/system2/tests -q
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from analyst.api import FIXTURES, KEY_HEADER, MIN_KEY_LEN, create_app  # noqa: E402
from analyst.contract import CONTRACT_VERSION, AssessRequest, AssessResponse  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]                         # amd/system2
MANIFEST = ROOT.parent / "system1" / "data" / "manifest.json"      # System 1's mission-level split
TEST_KEY = "fixture-test-key-0123456789abcdef"                       # 33 characters
assert len(TEST_KEY) >= MIN_KEY_LEN

FIXTURE_FILES = sorted(FIXTURES.glob("*.json"))
ROW_ID = re.compile(r"\b[EFSWI][1-9][0-9]?\b")
NUMBER = re.compile(r"\d+(?:\.\d+)?")
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


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(api_key=TEST_KEY))


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
    packet_text = json.dumps(d["response"]["packet"])
    packet_nums = {float(n) for n in NUMBER.findall(packet_text)}
    for text in _texts(d["response"]["explanation"]):
        stripped = ROW_ID.sub(" ", text)
        missing = [n for n in NUMBER.findall(stripped) if float(n) not in packet_nums]
        assert not missing, (path.stem, "numbers not in packet", missing, text)
        ids = ASSET_ID.findall(text) + WAYPOINT_ID.findall(text)
        absent = [i for i in ids if i not in packet_text]
        assert not absent, (path.stem, "asset/waypoint IDs not in packet", absent, text)


@pytest.mark.parametrize("path", FIXTURE_FILES, ids=lambda p: p.stem)
def test_stub_serves_fixture(client, path):
    d = _load(path)
    r = client.post("/v1/assess", json=d["request"], headers={KEY_HEADER: TEST_KEY})
    assert r.status_code == 200, (path.stem, r.text)
    body = AssessResponse.model_validate(r.json())
    assert body.explanation.model_dump(mode="json") == d["response"]["explanation"]
    assert body.meta.model == "stub"
