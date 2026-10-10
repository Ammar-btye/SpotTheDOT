"""ORCHESTRATOR_URL set: /explain asks the LangGraph orchestrator first, else the existing path (contract
"Orchestrator path"); /ask proxies to it. The orchestrator is faked with respx."""
import asyncio
import base64
import json

import httpx
import pytest

from .conftest import EMBED, MCP, S2
from .test_fallbacks import _action_flag, _s2_ok, mcp_server

ORCH = "http://orchestrator.test"
KEY = "orch-key-0123456789"
JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 64).decode()


def orch_reply(fid, source="system2", context_source="mcp", answer="No, escalate.", **kw):
    out = {"flag_id": fid, "request_id": "r-1", "route": "full", "route_reasons": ["flag_escalated"],
           "source": source, "question": "Is it safe?", "answer": answer, "reasoning": "F1 [F1]",
           "recommended_action": "DISPATCH_TECHNICIAN", "recommended_action_code": "DISPATCH_TECHNICIAN",
           "severity_assessment": None, "confidence": 0.85, "model": {"system2": "qwen-test", "template": "template",
                                                                      "system1": "laya-test",
                                                                      "system2_template": "template"}[source],
           "latency_ms": 900, "tokens_per_sec": 30.5, "insufficient_context": False,
           "evidence": [{"claim": "c", "ids": ["F1", "V1"]}], "citations": ["F1", "V1"], "fallback_reason": None,
           "system2": {"path": "llm"} if source == "system2" else None,
           "system1": {"source": "packet", "model": None, "answers": []},
           "vision": {"pairing": "linked", "kind": "thermal", "rows": [{"id": "V1", "tool": "thermal_colorbar",
                                                                         "trust": "HIGH", "value": 99.8}]},
           "context_source": context_source, "graph": "assess", "contract_version": "2026-10-10.orchestrator.1",
           "deadline_s": 40, "elapsed_ms": 1200,
           "trace": [{"node": "load_context", "ms": 10, "status": "ok", "detail": ""},
                     {"node": "system2", "ms": 900, "status": "ok", "detail": "path llm"}]}
    out.update(kw)
    return out


def orch_route(mock, reply=None, calls=None, status=200, exc=None):
    def handler(request: httpx.Request):
        if calls is not None:
            calls.append({"body": json.loads(request.content), "headers": dict(request.headers)})
        if exc is not None:
            raise exc
        return httpx.Response(status, json=reply(json.loads(request.content)) if callable(reply) else reply)
    return mock.post(ORCH + "/v1/assess").mock(side_effect=handler)


def _harness(make_harness, **kw):
    return make_harness(orchestrator_url=ORCH, orchestrator_api_key=KEY, **kw)


async def test_explain_via_orchestrator_system2_is_done_and_indexed(make_harness, mock):
    h = _harness(make_harness, system2_url=S2)
    fid = await _action_flag(h, mock)
    calls = []
    orch_route(mock, lambda b: orch_reply(b["flag_id"]), calls)
    mcp = mock.post(MCP).mock(side_effect=httpx.ConnectError("must not be called"))
    s2 = mock.post(S2 + "/v1/assess").mock(side_effect=httpx.ConnectError("must not be called"))
    mock.post(EMBED + "/v1/embeddings").mock(return_value=httpx.Response(
        200, json={"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3, 0.4]}], "model": "m"}))
    r = await h.client.post("/api/v1/flags/%d/explain" % fid)
    body = r.json()
    assert r.status_code == 200 and body["source"] == "system2" and body["answer"] == "No, escalate."
    assert body["context_source"] == "mcp" and body["cached"] is False
    assert body["orchestrator"]["route"] == "full" and body["orchestrator"]["trace"][0]["node"] == "load_context"
    assert body["orchestrator"]["vision"]["rows"][0]["id"] == "V1" and body["citations"] == ["F1", "V1"]
    assert calls[0]["body"] == {"flag_id": fid, "request_id": calls[0]["body"]["request_id"], "refresh": False}
    assert calls[0]["headers"]["x-api-key"] == KEY
    assert not mcp.called and not s2.called
    assert h.repo.assessments[fid]["state"] == "DONE" and h.repo.assessments[fid]["model"] == "qwen-test"
    await h.sink.drain()
    assert "explanation:%d" % body["assessment_id"] in h.repo.documents
    call = next(c for c in h.sink.model_calls if c["endpoint"] == "orchestrator:/v1/assess")
    assert call["system"] == "system2" and call["ok"] and call["metadata"]["via"] == "orchestrator"
    assert call["metadata"]["system2_path"] == "llm" and call["tokens_per_sec"] == 30.5
    again = (await h.client.get("/api/v1/flags/%d/explain" % fid)).json()
    assert again["cached"] is True and again["source"] == "system2" and len(calls) == 1      # DONE is final


@pytest.mark.parametrize("source", ["template", "system1", "system2_template"])
async def test_explain_via_orchestrator_template_or_system1_is_not_final(make_harness, mock, source):
    h = _harness(make_harness)
    fid = await _action_flag(h, mock)
    calls = []
    orch_route(mock, lambda b: orch_reply(b["flag_id"], source=source,
                                          fallback_reason="System 2 was not called" if source == "template" else None),
               calls)
    emb = mock.post(EMBED + "/v1/embeddings").mock(side_effect=httpx.ConnectError("refused"))
    body = (await h.client.post("/api/v1/flags/%d/explain" % fid)).json()
    assert body["source"] == source and h.repo.assessments[fid]["state"] == "TEMPLATE"
    await h.sink.drain()
    assert not any(k.startswith("explanation:") for k in h.repo.documents) and not emb.called
    again = (await h.client.get("/api/v1/flags/%d/explain" % fid)).json()   # TEMPLATE is retried (orchestrator set)
    assert again["cached"] is False and len(calls) == 2


@pytest.mark.parametrize("how", ["connect", "http500", "no_context", "no_answer"])
async def test_explain_falls_back_to_existing_path(make_harness, mock, how):
    h = _harness(make_harness, system2_url=S2)
    fid = await _action_flag(h, mock)
    if how == "connect":
        orch_route(mock, exc=httpx.ConnectError("refused"))
    elif how == "http500":
        orch_route(mock, {"detail": "boom"}, status=500)
    elif how == "no_context":
        orch_route(mock, lambda b: orch_reply(b["flag_id"], source="template", context_source="none",
                                              fallback_reason="MCP unavailable: down"))
    else:
        orch_route(mock, lambda b: orch_reply(b["flag_id"], answer=""))
    mcp_server(mock, {"packet_version": "1", "question": "q?"})
    s2_calls, s2 = _s2_ok(mock)
    mock.post(S2 + "/v1/assess").mock(side_effect=s2)
    mock.post(EMBED + "/v1/embeddings").mock(side_effect=httpx.ConnectError("refused"))
    body = (await h.client.post("/api/v1/flags/%d/explain" % fid)).json()
    assert body["source"] == "system2" and body["context_source"] == "mcp" and s2_calls   # the existing path ran
    assert body["orchestrator"]["error"] and "route" not in body["orchestrator"]
    breaker_open = h.svc.orchestrator.breaker.state == "open"
    assert breaker_open == (how in ("connect", "http500"))


async def test_orchestrator_4xx_does_not_open_breaker(make_harness, mock):
    h = _harness(make_harness, breaker_cooldown_s=60.0)
    fid = await _action_flag(h, mock)
    orch_route(mock, {"detail": "image_b64 is not valid base64"}, status=422)
    mock.post(MCP).mock(side_effect=httpx.ConnectError("refused"))
    body = (await h.client.post("/api/v1/flags/%d/explain" % fid, json={"image_b64": JPEG})).json()
    assert body["source"] == "template" and "HTTP 422" in body["orchestrator"]["error"]
    assert h.svc.orchestrator.breaker.state == "closed"


async def test_orchestrator_deadline_leaves_the_existing_path_a_template(make_harness, mock):
    h = _harness(make_harness, request_deadline_s=1.0)
    fid = await _action_flag(h, mock)

    async def hang(request):
        await asyncio.sleep(5)
    mock.post(ORCH + "/v1/assess").mock(side_effect=hang)
    mock.post(MCP).mock(side_effect=httpx.ConnectError("refused"))
    t0 = asyncio.get_running_loop().time()
    r = await h.client.post("/api/v1/flags/%d/explain" % fid)
    assert asyncio.get_running_loop().time() - t0 < 3.0
    body = r.json()
    assert r.status_code == 200 and body["source"] == "template"
    assert body["orchestrator"]["error"].startswith("deadline:")


async def test_image_is_forwarded_and_bypasses_cache(make_harness, mock):
    h = _harness(make_harness)
    fid = await _action_flag(h, mock)
    calls = []
    orch_route(mock, lambda b: orch_reply(b["flag_id"]), calls)
    mock.post(EMBED + "/v1/embeddings").mock(side_effect=httpx.ConnectError("refused"))
    await h.client.post("/api/v1/flags/%d/explain" % fid)
    body = (await h.client.post("/api/v1/flags/%d/explain" % fid,
                                json={"image_b64": "data:image/jpeg;base64," + JPEG, "image_kind": "thermal"})).json()
    assert body["cached"] is False and len(calls) == 2
    assert calls[1]["body"]["image_b64"].endswith(JPEG) and calls[1]["body"]["image_kind"] == "thermal"


async def test_image_without_orchestrator_is_ignored_with_warning(make_harness, mock):
    h = make_harness()
    fid = await _action_flag(h, mock)
    mock.post(MCP).mock(side_effect=httpx.ConnectError("refused"))
    body = (await h.client.post("/api/v1/flags/%d/explain" % fid, json={"image_b64": JPEG})).json()
    assert body["source"] == "template" and body["warning"] == "image ignored: ORCHESTRATOR_URL is not set"
    assert "orchestrator" not in body


async def test_explain_rejects_bad_image(make_harness, mock):
    h = _harness(make_harness)
    fid = await _action_flag(h, mock)
    r = await h.client.post("/api/v1/flags/%d/explain" % fid, json={"image_b64": "not base64 !!"})
    assert r.status_code == 422
    r = await h.client.post("/api/v1/flags/%d/explain" % fid, json={"image_b64": JPEG, "image_kind": "xray"})
    assert r.status_code == 422


async def test_unset_orchestrator_keeps_existing_explain(make_harness, mock):
    h = make_harness(system2_url=S2)
    fid = await _action_flag(h, mock)
    orch = mock.post(ORCH + "/v1/assess").mock(return_value=httpx.Response(200, json={}))
    mcp_server(mock, {"packet_version": "1", "question": "q?"})
    _, s2 = _s2_ok(mock)
    mock.post(S2 + "/v1/assess").mock(side_effect=s2)
    mock.post(EMBED + "/v1/embeddings").mock(side_effect=httpx.ConnectError("refused"))
    body = (await h.client.post("/api/v1/flags/%d/explain" % fid)).json()
    assert body["source"] == "system2" and "orchestrator" not in body and not orch.called


# ── /api/v1/ask ─────────────────────────────────────────────────────────────────────────────────
async def test_ask_unset_is_503(h):
    r = await h.client.post("/api/v1/ask", json={"question": "How should Spot dock at low battery?"})
    assert r.status_code == 503 and r.json()["error"] == "orchestrator_unset"


async def test_ask_proxies_to_orchestrator(make_harness, mock):
    h = _harness(make_harness)
    seen = []
    reply = {"answer": "Dock first [manual:12]", "citations": ["manual:12"], "tool_calls": [], "model": "system2",
             "mode": "retrieval_fallback", "steps": 1, "latency_ms": 50, "request_id": "r-1", "max_tool_calls": 4,
             "error": None}

    def handler(request):
        seen.append({"body": json.loads(request.content), "headers": dict(request.headers)})
        return httpx.Response(200, json=reply)
    mock.post(ORCH + "/v1/ask").mock(side_effect=handler)
    r = await h.client.post("/api/v1/ask", json={"question": "How should Spot dock?", "flag_id": 3, "max_steps": 2})
    assert r.status_code == 200 and r.json() == reply
    assert seen[0]["body"]["question"] == "How should Spot dock?" and seen[0]["body"]["max_steps"] == 2
    assert seen[0]["body"]["flag_id"] == 3 and seen[0]["headers"]["x-api-key"] == KEY
    assert (await h.client.post("/api/v1/ask", json={"question": "x"})).status_code == 422


async def test_ask_down_is_503(make_harness, mock):
    h = _harness(make_harness)
    mock.post(ORCH + "/v1/ask").mock(side_effect=httpx.ConnectError("refused"))
    r = await h.client.post("/api/v1/ask", json={"question": "How should Spot dock?"})
    assert r.status_code == 503 and r.json()["error"] == "orchestrator_unavailable"


async def test_health_reports_orchestrator(make_harness, mock):
    h = _harness(make_harness)
    mock.get(ORCH + "/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    body = (await h.client.get("/health")).json()
    assert body["orchestrator"]["status"] == "up" and body["orchestrator"]["url"] == ORCH
    h2 = make_harness()
    assert (await h2.client.get("/health")).json()["orchestrator"]["status"] == "unset"


def test_orchestrator_settings_from_env(monkeypatch):
    from app.config import Settings
    monkeypatch.setenv("ORCHESTRATOR_URL", "http://orchestrator:8085/")
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", KEY)
    s = Settings.from_env()
    assert s.orchestrator_url == "http://orchestrator:8085" and s.orchestrator_api_key == KEY
    assert s.orchestrator_timeout_s == 42.0
    monkeypatch.setenv("ORCHESTRATOR_URL", "")
    assert Settings.from_env().orchestrator_url is None


# ── audit A-8 / P-5: System 2's own template is not a model answer (direct path, no orchestrator) ──────────
@pytest.mark.parametrize("reply,final", [
    ({"path": "fallback", "model": "template"}, False),
    ({"path": "insufficient_context", "model": "stub"}, False),
    ({"model": "template"}, False),
    ({"path": "llm", "model": "qwen-test"}, True),
    ({"path": "retry", "model": "qwen-test"}, True),
    ({"path": "stub", "model": "stub"}, True),          # stub rows stay DONE (P-5 stub case unchanged)
])
async def test_direct_system2_template_reply_is_not_final(make_harness, mock, reply, final):
    h = make_harness(system2_url=S2)
    fid = await _action_flag(h, mock)
    mcp_server(mock, {"packet_version": "1", "question": "q?"})
    calls = []

    def s2(request):
        calls.append(1)
        return httpx.Response(200, json={"question": "q?", "answer": "Checked template answer.", "evidence": [],
                                         "recommended_action": "MANUAL_REVIEW", "confidence": "low", **reply})
    mock.post(S2 + "/v1/assess").mock(side_effect=s2)
    emb = mock.post(EMBED + "/v1/embeddings").mock(return_value=httpx.Response(
        200, json={"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3, 0.4]}], "model": "m"}))
    body = (await h.client.post("/api/v1/flags/%d/explain" % fid)).json()
    await h.sink.drain()
    indexed = "explanation:%d" % body["assessment_id"] in h.repo.documents
    if final:
        assert body["source"] == "system2" and h.repo.assessments[fid]["state"] == "DONE" and indexed
    else:
        assert body["source"] == "system2_template" and "checked template" in body["fallback_reason"]
        assert h.repo.assessments[fid]["state"] == "TEMPLATE" and not indexed and not emb.called
        again = (await h.client.get("/api/v1/flags/%d/explain" % fid)).json()   # not final: System 2 is asked again
        assert again["cached"] is False and len(calls) == 2
