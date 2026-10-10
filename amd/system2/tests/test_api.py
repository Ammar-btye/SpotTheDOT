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
from analyst.contract import AssessResponse  # noqa: E402

TEST_KEY = "test-key-0123456789abcdef0123456"     # 32 characters
assert len(TEST_KEY) == 32
EQUIP = json.loads((FIXTURES / "equipment.json").read_text(encoding="utf-8"))


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
    body = AssessResponse.model_validate(r.json())
    assert body.flag_id == "flag:act-A0009"
    assert body.packet.flag.flag_id == "flag:act-A0009"
    assert body.meta.model == "stub"


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
    del req["flag"]["flag_id"]


@pytest.mark.parametrize("mutate", [
    lambda req: req["flag"].__setitem__("category", "bogus"),
    _no_flag_id,
    lambda req: req["flag"].__setitem__("severity", "HIGH"),
    lambda req: req["flag"].__setitem__("reasons", []),
], ids=["bad_category", "missing_flag_id", "extra_field", "empty_reasons"])
def test_malformed_flag_422(client, mutate):
    req = _req()
    mutate(req)
    r = client.post("/v1/assess", json=req, headers=_h())
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("field,value", [
    ("escalate", "yes"), ("timestamp", 1700000000), ("timestamp", "2026-09-01T18:27:54Z"),
    ("timestamp", "2026-09-01T18:27:54+05:00"),
], ids=["bool_str", "ts_int", "ts_z", "ts_offset"])
def test_lax_values_422(client, field, value):
    req = _req()
    req["flag"][field] = value
    r = client.post("/v1/assess", json=req, headers=_h())
    assert r.status_code == 422, r.text


def test_health_open_and_keyless(client):
    r = client.get("/health")
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"status", "mode", "contract_version", "fixtures"}
    assert (d["status"], d["mode"], d["contract_version"]) == ("ok", "stub", "2026-10-10.1") and d["fixtures"] >= 1
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


# ── fixture index rules ──────────────────────────────────────────────────────

def _write_fixture(d: Path, name: str, flag_id: str = "flag:act-A0009") -> None:
    fx = copy.deepcopy(EQUIP)
    fx["name"] = name
    fx["request"]["flag"]["flag_id"] = flag_id
    fx["response"]["flag_id"] = flag_id
    fx["response"]["packet"]["flag"]["flag_id"] = flag_id
    (d / ("%s.json" % name)).write_text(json.dumps(fx), encoding="utf-8")


def test_flag_id_and_category_lookup(tmp_path):
    _write_fixture(tmp_path, "equipment")
    c = TestClient(create_app(api_key=TEST_KEY, fixtures_dir=tmp_path))
    req = _req()
    req["flag"]["flag_id"] = "flag:act-A0042"
    r = c.post("/v1/assess", json=req, headers=_h())
    assert r.status_code == 200, r.text
    assert r.json()["flag_id"] == "flag:act-A0042" and r.json()["packet"]["flag"]["flag_id"] == "flag:act-A0042"
    nav = _req()
    nav["flag"]["category"] = "navigation"            # same flag_id as the fixture, different category
    r = c.post("/v1/assess", json=nav, headers=_h())
    assert r.status_code == 501
    assert "navigation" in r.json()["detail"]


def test_duplicate_category_rejected(tmp_path):
    _write_fixture(tmp_path, "equipment")
    _write_fixture(tmp_path, "equipment2", flag_id="flag:act-A0010")
    with pytest.raises(ValueError) as e:
        create_app(api_key=TEST_KEY, fixtures_dir=tmp_path)
    assert "equipment" in str(e.value) and "equipment2" in str(e.value)


def test_empty_fixture_dir_rejected(tmp_path):
    with pytest.raises(ValueError):
        create_app(api_key=TEST_KEY, fixtures_dir=tmp_path)


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
    req["flag"]["flag_id"] = "flag:custom-1"
    assert c.post("/v1/assess", json=req, headers=_h()).json()["flag_id"] == "flag:custom-1"
    r = c.post("/v1/assess", json=_req(), headers=_h())
    assert r.json()["flag_id"] == "flag:act-A0009"
    assert r.json()["packet"]["flag"]["flag_id"] == "flag:act-A0009"
    _, freq, fresp = app.state.fixtures[0]
    assert freq.flag.flag_id == fresp.flag_id == fresp.packet.flag.flag_id == "flag:act-A0009"
    assert fresp.meta.model == "fixture"


def test_stub_marks_model(client):
    for fid in ("flag:act-A0009", "flag:act-A0001", "flag:other"):
        req = _req()
        req["flag"]["flag_id"] = fid
        r = client.post("/v1/assess", json=req, headers=_h())
        assert r.status_code == 200 and r.json()["meta"]["model"] == "stub", r.text
