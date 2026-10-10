"""End-to-end tests for the stub /v1/assess through the real FastAPI stack: 200 / 401 / 422, auth before validation.

Run: uv run --no-project --with-requirements amd/system2/requirements.txt python -m pytest amd/system2/tests -q
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from analyst.api import FIXTURES, KEY_HEADER, create_app, load_fixtures  # noqa: E402
from analyst.backend_contract import BACKEND_CONTRACT_VERSION, BackendAssessResponse  # noqa: E402

TEST_KEY = "test-key-0123456789abcdef0123456"     # 32 characters
assert len(TEST_KEY) == 32
EQUIP = json.loads((FIXTURES / "backend/equipment.json").read_text(encoding="utf-8"))
LEGACY_EQUIP = json.loads((FIXTURES / "equipment.json").read_text(encoding="utf-8"))


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(api_key=TEST_KEY))


def _req() -> dict:
    return copy.deepcopy(EQUIP["request"])


def _h(key: str = TEST_KEY) -> dict:
    return {KEY_HEADER: key}


def test_assess_equipment_ok(client):
    r = client.post("/v1/assess", json=_req(), headers=_h())
    assert r.status_code == 200, r.text
    body = BackendAssessResponse.model_validate(r.json())
    assert body.flag_id == 9
    assert body.evidence[0].claim == _req()["context"]["facts"][0]["fact"]
    assert body.model == "stub"


def test_missing_key_401(client):
    r = client.post("/v1/assess", json=_req())
    assert r.status_code == 401
    assert r.json()["detail"] == "missing or invalid X-API-Key"


@pytest.mark.parametrize("bad", ["x" * len(TEST_KEY), "short-wrong-key", TEST_KEY + "x", "kéy-" + "x" * 28])
def test_wrong_key_401(client, bad):
    r = client.post("/v1/assess", json=_req(), headers={KEY_HEADER: bad.encode("utf-8")})
    assert r.status_code == 401


def test_auth_before_validation_401(client):
    r = client.post("/v1/assess", json={"flag": {"category": "bogus"}, "junk": 1})
    assert r.status_code == 401


@pytest.mark.parametrize("body", [b"{", b"{not json", b"", b"\xff\xfe"], ids=["brace", "garbage", "empty", "binary"])
def test_auth_before_body_parse_401(client, body):
    ct = {"content-type": "application/json"}
    for h in (ct, dict(ct, **_h("x" * len(TEST_KEY)))):
        r = client.post("/v1/assess", content=body, headers=h)
        assert r.status_code == 401, (h, r.status_code, r.text)
        assert r.json()["detail"] == "missing or invalid X-API-Key"
    assert client.post("/v1/assess", content=body, headers=dict(ct, **_h())).status_code == 422


def _no_flag_id(req):
    del req["flag_id"]


@pytest.mark.parametrize("mutate", [
    lambda req: req.__setitem__("flag", []),
    _no_flag_id,
    lambda req: req["context"].__setitem__("allowed_actions", {"BOGUS": "unknown"}),
    lambda req: req["context"].__setitem__("facts", "not a list"),
], ids=["flag_not_object", "missing_flag_id", "unknown_action", "facts_not_list"])
def test_malformed_flag_422(client, mutate):
    req = _req()
    mutate(req)
    r = client.post("/v1/assess", json=req, headers=_h())
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("field,value", [
    ("flag_id", True), ("flag_id", "9"), ("flag_id", 9.0), ("request_id", 42),
], ids=["bool_id", "string_id", "float_id", "integer_request_id"])
def test_lax_values_422(client, field, value):
    req = _req()
    req[field] = value
    r = client.post("/v1/assess", json=req, headers=_h())
    assert r.status_code == 422, r.text


def test_health_open_and_keyless(client):
    r = client.get("/health")
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"status", "mode", "contract_version"}
    assert (d["status"], d["mode"], d["contract_version"]) == ("ok", "stub", BACKEND_CONTRACT_VERSION)
    assert TEST_KEY not in r.text


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"])
def test_docs_routes_disabled(client, path):
    assert client.get(path).status_code == 401                 # keyless: never served
    assert client.get(path, headers=_h()).status_code == 404   # keyed: the route does not exist


def test_create_app_requires_key(monkeypatch):
    monkeypatch.delenv("AMD_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as e:
        create_app(api_key=None)
    with pytest.raises(RuntimeError) as e2:
        create_app(api_key="short")
    assert "short" not in str(e2.value) and "16" in str(e.value)


@pytest.mark.parametrize("bad", [
    " " * 16, " " * 40, "\t" * 20, " " + TEST_KEY, TEST_KEY + " ", TEST_KEY + "\n", "\t" + TEST_KEY,
    "clé-secrète-0123456789", TEST_KEY[:16] + "\x00" + TEST_KEY[16:], TEST_KEY[:16] + "\x7f" + TEST_KEY[16:],
    TEST_KEY[:16] + "\t" + TEST_KEY[16:],
], ids=["ws16", "ws40", "tabs", "lead_space", "trail_space", "trail_newline", "lead_tab", "non_ascii", "nul", "del",
        "inner_tab"])
def test_create_app_rejects_unusable_key(bad):
    with pytest.raises(RuntimeError) as e:
        create_app(api_key=bad)
    msg = str(e.value)
    assert "AMD_API_KEY" in msg and bad not in msg and repr(bad) not in msg
    assert not bad.strip() or bad.strip() not in msg           # whitespace-only keys have nothing to leak


def test_key_with_inner_space_works():
    key = "correct horse battery staple 42"
    c = TestClient(create_app(api_key=key))
    assert c.post("/v1/assess", json=_req(), headers=_h(key)).status_code == 200
    assert c.post("/v1/assess", json=_req(), headers=_h(key[:-1])).status_code == 401


# ── fixture index rules ──────────────────────────────────────────────────────

def _write_fixture(d: Path, name: str, flag_id: str = "flag:act-A0009") -> None:
    fx = copy.deepcopy(LEGACY_EQUIP)
    fx["name"] = name
    fx["request"]["flag"]["flag_id"] = flag_id
    fx["response"]["flag_id"] = flag_id
    fx["response"]["packet"]["flag"]["flag_id"] = flag_id
    (d / ("%s.json" % name)).write_text(json.dumps(fx), encoding="utf-8")


def test_unknown_flag_uses_its_own_packet(tmp_path):
    _write_fixture(tmp_path, "equipment")
    c = TestClient(create_app(api_key=TEST_KEY, fixtures_dir=tmp_path))
    req = _req()
    req["flag_id"] = 42
    req["flag"]["flag_id"] = 42
    req["context"]["facts"][0]["fact"] = "Caller supplied different inspection evidence."
    r = c.post("/v1/assess", json=req, headers=_h())
    assert r.status_code == 200, r.text
    assert r.json()["flag_id"] == 42
    assert r.json()["answer"] == req["context"]["facts"][0]["fact"]
    req["context"] = {"facts": [], "allowed_actions": {"MONITOR": "watch"}}
    r = c.post("/v1/assess", json=req, headers=_h())
    assert r.status_code == 200
    assert r.json()["evidence"] == [] and r.json()["insufficient_context"]


def test_startup_does_not_index_fixture_categories(tmp_path):
    _write_fixture(tmp_path, "equipment")
    _write_fixture(tmp_path, "equipment2", flag_id="flag:act-A0010")
    c = TestClient(create_app(api_key=TEST_KEY, fixtures_dir=tmp_path))
    assert c.post("/v1/assess", json=_req(), headers=_h()).status_code == 200


def test_empty_fixture_dir_does_not_block_startup(tmp_path):
    c = TestClient(create_app(api_key=TEST_KEY, fixtures_dir=tmp_path))
    assert c.post("/v1/assess", json=_req(), headers=_h()).status_code == 200


def test_fixtures_load_sorted(tmp_path):
    names = ["zeta", "alpha", "mid"]
    for i, n in enumerate(names):
        _write_fixture(tmp_path, n, flag_id="flag:act-A00%d0" % (i + 1))
    assert [n for n, _, _ in load_fixtures(tmp_path)] == sorted(names)


def test_no_fixture_mutation(tmp_path):
    _write_fixture(tmp_path, "equipment")
    app = create_app(api_key=TEST_KEY, fixtures_dir=tmp_path)
    c = TestClient(app)
    req = _req()
    req["flag_id"] = 101
    req["flag"]["flag_id"] = 101
    assert c.post("/v1/assess", json=req, headers=_h()).json()["flag_id"] == 101
    r = c.post("/v1/assess", json=_req(), headers=_h())
    assert r.json()["flag_id"] == 9
    _, freq, fresp = load_fixtures(tmp_path)[0]
    assert freq.flag.flag_id == fresp.flag_id == fresp.packet.flag.flag_id == "flag:act-A0009"
    assert fresp.meta.model == "fixture"


def test_stub_marks_model(client):
    for fid in (9, 1, 789):
        req = _req()
        req["flag_id"] = fid
        req["flag"]["flag_id"] = fid
        r = client.post("/v1/assess", json=req, headers=_h())
        assert r.status_code == 200 and r.json()["model"] == "stub", r.text
        assert r.json()["flag_id"] == fid
