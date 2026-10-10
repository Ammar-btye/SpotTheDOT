"""Stub System 2 API for the Saturday-morning hand-off: web builds against the real contract before any model runs.

`POST /v1/assess` takes an `AssessRequest` (just the System 1 flag, decision A1) behind `X-API-Key` and answers with a
schema-valid `AssessResponse` copied from a fixture in fixtures/*.json, stamped with the caller's flag and
`meta.model = "stub"` so stub output can never pass for model output (T-01-07). Phase 3 replaces the fixture lookup
with the real packet -> LLM -> post-check pipeline behind the same `create_app` and route.

Fixture lookup: the fixture whose flag_id matches AND whose category matches the request; otherwise the category's
default fixture (one non-insufficient fixture per category); otherwise 501.
"""
import hmac
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader

from .contract import CONTRACT_VERSION, AssessRequest, AssessResponse

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
MIN_KEY_LEN = 16
KEY_HEADER = "X-API-Key"
FIXTURE_KEYS = {"name", "description", "request", "response"}

Fixture = Tuple[str, AssessRequest, AssessResponse]


def load_fixtures(fixtures_dir: Path = FIXTURES) -> List[Fixture]:
    """[(name, request, response)] in sorted filename order; ValueError on any malformed fixture."""
    paths = sorted(Path(fixtures_dir).glob("*.json"))
    if not paths:
        raise ValueError("no *.json fixtures in %r" % str(fixtures_dir))
    out = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict) or set(d) != FIXTURE_KEYS:
            raise ValueError("fixture %r: top-level keys must be %r, got %r"
                             % (p.name, sorted(FIXTURE_KEYS), sorted(d) if isinstance(d, dict) else type(d)))
        if d["name"] != p.stem:
            raise ValueError("fixture %r: name %r differs from file stem %r" % (p.name, d["name"], p.stem))
        req = AssessRequest.model_validate(d["request"])
        resp = AssessResponse.model_validate(d["response"])
        if resp.flag_id != req.flag.flag_id:
            raise ValueError("fixture %r: response.flag_id %r != request flag_id %r"
                             % (p.name, resp.flag_id, req.flag.flag_id))
        out.append((d["name"], req, resp))
    return out


def create_app(api_key: Optional[str] = None, fixtures_dir: Path = FIXTURES) -> FastAPI:
    key = api_key if api_key is not None else os.environ.get("AMD_API_KEY", "")
    if len(key) < MIN_KEY_LEN:
        raise RuntimeError("AMD_API_KEY must be set to a secret of at least %d characters" % MIN_KEY_LEN)
    expected = key.encode("utf-8")

    fixtures = load_fixtures(fixtures_dir)
    by_flag: Dict[str, Tuple[AssessRequest, AssessResponse]] = {}
    by_category: Dict[str, Tuple[str, AssessResponse]] = {}
    for name, req, resp in fixtures:
        fid = req.flag.flag_id
        if fid in by_flag:
            raise ValueError("duplicate fixture flag_id %r (fixture %r)" % (fid, name))
        by_flag[fid] = (req, resp)
        if resp.explanation.insufficient_context:
            continue
        cat = req.flag.category
        if cat in by_category:
            raise ValueError("fixtures %r and %r both default category %r" % (by_category[cat][0], name, cat))
        by_category[cat] = (name, resp)

    app = FastAPI(title="SPOTlight System 2 Analyst (stub)", version=CONTRACT_VERSION)
    app.state.fixtures = fixtures
    header = APIKeyHeader(name=KEY_HEADER, auto_error=False)

    def auth(given: Optional[str] = Security(header)) -> None:
        if given is None or not hmac.compare_digest(given.encode("utf-8"), expected):
            raise HTTPException(status_code=401, detail="missing or invalid X-API-Key")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "mode": "stub", "contract_version": CONTRACT_VERSION, "fixtures": len(fixtures)}

    @app.post("/v1/assess", response_model=AssessResponse, dependencies=[Depends(auth)])
    def assess(body: AssessRequest) -> AssessResponse:
        t0 = time.perf_counter()
        flag = body.flag
        hit = by_flag.get(flag.flag_id)
        if hit is not None and hit[0].flag.category == flag.category:
            resp = hit[1]
        elif flag.category in by_category:
            resp = by_category[flag.category][1]
        else:
            raise HTTPException(status_code=501, detail="no stub fixture for category %r" % flag.category)
        d = resp.model_dump(mode="json")          # fresh copy: the loaded fixture is never mutated
        d["flag_id"] = flag.flag_id
        d["packet"]["flag"] = flag.model_dump(mode="json")
        d["meta"]["model"] = "stub"
        d["meta"]["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        return AssessResponse.model_validate(d)

    return app
