"""Real System2Client HTTP and backend persistence path; FakeRepo replaces external DB only."""
import copy
import json
from pathlib import Path
import socket
import sys
import threading
import time

import httpx
import pytest
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "amd/system2"))
from analyst.api import create_app

from .conftest import EMBED
from .test_fallbacks import _action_flag, mcp_server

KEY = "integration-test-only-0123456789abcdef"
FIXTURE = Path(__file__).resolve().parents[2] / "amd/system2/fixtures/backend/equipment.json"


@pytest.fixture
def real_system2():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    base = "http://127.0.0.1:%d" % sock.getsockname()[1]
    app = create_app(KEY)
    seen = []

    @app.middleware("http")
    async def record(request, call_next):
        if request.url.path == "/v1/assess":
            seen.append({"body": await request.json(), "key": request.headers.get("X-API-Key")})
        return await call_next(request)

    server = uvicorn.Server(uvicorn.Config(app, log_level="error", ws="none"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started, "real System 2 server did not start"
        yield base, seen
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive(), "System 2 did not stop"


@pytest.mark.parametrize("mode", ["complete", "insufficient", "wrong_key"])
async def test_explain_real_system2_done_and_cache(make_harness, mock, real_system2, mode):
    base, seen = real_system2
    h = make_harness(system2_url=base, system2_api_key=KEY if mode != "wrong_key" else "wrong-test-key")
    # Only this route passes through respx: the actual client sends body/key over a real TCP socket.
    mock.post(base + "/v1/assess").pass_through()
    try:
        fid = await _action_flag(h, mock)
        packet = copy.deepcopy(json.loads(FIXTURE.read_text())["request"]["context"])
        packet["flag"]["id"] = "flag:%d" % fid
        packet["flag"]["flag_id"] = fid
        packet["citation_ids"] = ["flag:%d" % fid if x == "flag:9" else x for x in packet["citation_ids"]]
        # MCP _doc emits the database doc_id under `id`, alongside F# facts.
        if mode == "insufficient":
            packet["gaps"] = ["manual passage unavailable"]
            packet["insufficient_context"] = True
        mcp_server(mock, packet)
        mock.post(EMBED + "/v1/embeddings").mock(side_effect=httpx.ConnectError("test embed unavailable"))
        r = await h.client.post("/api/v1/flags/%d/explain" % fid)
        assert r.status_code == 200, r.text
        body = r.json()
        stored = h.repo.assessments[fid]
        calls = [c for c in h.sink.model_calls if c["system"] == "system2"]
        assert len(calls) == len(seen) == 1
        assert seen[0]["body"]["flag_id"] == fid
        assert all(seen[0]["body"]["context"][k] == v for k, v in packet.items())
        assert seen[0]["key"] == h.settings.system2_api_key
        if mode == "wrong_key":
            assert body["source"] == "template" and stored["state"] == "TEMPLATE"
            assert "HTTP 401" in body["fallback_reason"] and not calls[0]["ok"]
            return
        if mode == "insufficient":
            # Audit A-8/P-5: System 2's insufficient_context reply is its checked template, not a model answer:
            # returned as system2_template, stored TEMPLATE (not final) and asked again next time.
            assert body["source"] == "system2_template" and body["answer"] and body["assessment_id"]
            assert stored["state"] == "TEMPLATE" and stored["model"] == body["model"] == "stub"
            assert body["confidence"] == 0.35 and body["insufficient_context"] and body["evidence"] == []
            second = (await h.client.post("/api/v1/flags/%d/explain" % fid)).json()
            assert not second["cached"] and second["source"] == "system2_template" and len(seen) == 2
            return
        assert body["source"] == "system2" and body["answer"] and body["assessment_id"]
        assert stored["state"] == "DONE" and stored["model"] == body["model"] == "stub"
        # Existing persistence stores textual reasoning, action and numeric confidence;
        # evidence/insufficient_context are returned live but are not assessment columns.
        for field in ("answer", "reasoning", "recommended_action", "confidence"):
            assert stored[field] == body[field]
        assert body["recommended_action"].isupper() and calls[0]["ok"]
        if mode == "complete":
            assert body["confidence"] == 0.6 and not body["insufficient_context"]
            assert body["evidence"][0]["ids"] == ["F1"]
            assert body["reasoning"] == " ".join("%s [%s]" % (e["claim"], ", ".join(e["ids"])) for e in body["evidence"])
        else:
            assert body["confidence"] == 0.35 and body["insufficient_context"] and body["evidence"] == []
        second = (await h.client.post("/api/v1/flags/%d/explain" % fid)).json()
        assert second["cached"] and second["source"] == "system2"
        assert second["assessment_id"] == body["assessment_id"] and len(seen) == 1
        assert len([c for c in h.sink.model_calls if c["system"] == "system2"]) == 1
    finally:
        await h.client.aclose()
        await h.svc.close()
