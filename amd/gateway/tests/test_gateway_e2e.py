"""The real LiteLLM proxy (python serve.py, subprocess) against offline stubs for all four upstreams.

Asserts routing for system2 / system2-vision / system1 / embed, master-key auth, json_schema and
chat_template_kwargs passthrough, image content-array passthrough, tools/tool_calls passthrough, Laya error mapping,
the per-alias timeout with no retry, and that System 2's real LlamaGenerator + parse_envelope work through the
gateway. ~12 s (proxy start).
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

HERE = Path(__file__).resolve().parent
GATEWAY = HERE.parent
REPO = GATEWAY.parents[1]
sys.path.insert(0, str(HERE))
from stubs import LAYA_CRASH_MARKER, LAYA_REJECT_MARKER, LAYA_SLOW_MARKER, ServerThread  # noqa: E402

KEY = "sk-gateway-e2e-key-000001"
AUTH = {"Authorization": "Bearer " + KEY}
TIMEOUT_S = 2      # SYSTEM2_TIMEOUT_S for this run, so the timeout test is quick
PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5E"
       "rkJggg==")
SCHEMA = {"type": "json_schema", "json_schema": {"name": "assessment", "schema": {
    "type": "object", "properties": {"answer": {"type": "string", "minLength": 1, "maxLength": 40, "enum": ["ok"]},
                                     "ids": {"type": "array", "items": {"type": "string", "enum": ["E1", "DOC-2"]},
                                             "minItems": 1, "maxItems": 8}},
    "required": ["answer", "ids"], "additionalProperties": False}}}
EVENT = {"mission_id": "M-1", "action_id": "A-1"}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    ports = {name: free_port() for name in ("text", "vision", "laya", "embed", "gateway")}
    stubs = [ServerThread("llama", ports["text"], "text").start(),
             ServerThread("llama", ports["vision"], "vision").start(),
             ServerThread("laya", ports["laya"]).start(),
             ServerThread("embed", ports["embed"]).start()]
    url = {k: "http://127.0.0.1:%d" % p for k, p in ports.items()}
    env = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "VISION_LLAMA_URL")}
    env.update({"LITELLM_MASTER_KEY": KEY, "LLAMA_URL": url["text"], "VISION_LLAMA_URL": url["vision"],
                "SYSTEM1_URL": url["laya"], "EMBED_URL": url["embed"], "SYSTEM2_TIMEOUT_S": str(TIMEOUT_S),
                "SYSTEM1_TIMEOUT_S": str(TIMEOUT_S),
                "GATEWAY_HOST": "127.0.0.1", "GATEWAY_PORT": str(ports["gateway"]),
                "NO_PROXY": "*", "no_proxy": "*"})
    log = tmp_path_factory.mktemp("gw") / "gateway.log"
    with open(log, "wb") as fh:
        proc = subprocess.Popen([sys.executable, str(GATEWAY / "serve.py")], env=env, stdout=fh,
                                stderr=subprocess.STDOUT, cwd=str(GATEWAY))
    try:
        deadline = time.monotonic() + 120
        while True:
            if proc.poll() is not None:
                pytest.fail("gateway exited (%s):\n%s" % (proc.returncode, log.read_text()[-3000:]))
            try:
                if httpx.get(url["gateway"] + "/health/liveliness", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() > deadline:
                pytest.fail("gateway did not come up:\n" + log.read_text()[-3000:])
            time.sleep(0.5)
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        for s in stubs:
            s.stop()


def seen(url):
    return httpx.get(url + "/_requests").json()


def chat(stack, body, headers=AUTH):
    return httpx.post(stack["gateway"] + "/v1/chat/completions", json=body, headers=headers, timeout=30)


# ── auth / discovery ──────────────────────────────────────────────────────────────────────────

def test_liveliness_is_public_and_models_lists_the_four_aliases(stack):
    assert httpx.get(stack["gateway"] + "/health/liveliness").status_code == 200
    models = httpx.get(stack["gateway"] + "/v1/models", headers=AUTH).json()
    assert sorted(m["id"] for m in models["data"]) == ["embed", "system1", "system2", "system2-vision"]


def test_no_key_is_401_and_wrong_key_is_rejected(stack):
    body = {"model": "system2", "messages": [{"role": "user", "content": "hi"}]}
    before = len(seen(stack["text"]))
    assert chat(stack, body, headers={}).status_code == 401
    # without a DB LiteLLM answers a non-master key with 400 "No connected db." (still rejected, never forwarded)
    assert chat(stack, body, headers={"Authorization": "Bearer sk-not-the-master-key"}).status_code in (400, 401)
    assert len(seen(stack["text"])) == before


def test_unknown_model_is_400_not_a_fallback(stack):
    r = chat(stack, {"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 400


# ── system2 / system2-vision ─────────────────────────────────────────────────────────────────

def test_system2_routes_to_text_llama_with_json_schema_unchanged(stack):
    nv = len(seen(stack["vision"]))
    body = {"model": "system2", "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "q"}],
            "temperature": 0, "max_tokens": 350, "stream": False, "response_format": SCHEMA,
            "chat_template_kwargs": {"enable_thinking": False}}
    r = chat(stack, body)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["choices"][0]["message"]["content"] == '{"answer":"ok"}'
    assert out["choices"][0]["finish_reason"] == "stop"
    assert out["model"] == "system2"                                   # the alias, not llama-server's name
    assert out["timings"]["predicted_per_second"] == 42.5               # llama-server extras survive
    assert out["usage"]["completion_tokens"] == 7
    sent = seen(stack["text"])[-1]
    assert sent["body"]["response_format"] == SCHEMA                    # byte-for-byte the same schema
    assert sent["body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert (sent["body"]["temperature"], sent["body"]["max_tokens"]) == (0, 350)
    assert sent["body"]["messages"] == body["messages"]
    assert len(seen(stack["vision"])) == nv


def test_served_model_name_is_a_hidden_alias_of_system2(stack):
    """System 2 can keep SYSTEM2_MODEL=qwen3.5-9b-q4km: same upstream, and `model` (its cache key) is unchanged."""
    before = len(seen(stack["text"]))
    r = chat(stack, {"model": "qwen3.5-9b-q4km", "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200 and r.json()["model"] == "qwen3.5-9b-q4km"
    assert len(seen(stack["text"])) == before + 1


def test_system2_vision_routes_to_vision_llama_with_image_array_unchanged(stack):
    nt = len(seen(stack["text"]))
    content = [{"type": "image_url", "image_url": {"url": PNG}}, {"type": "text", "text": "read the gauge"}]
    r = chat(stack, {"model": "system2-vision", "messages": [{"role": "user", "content": content}],
                     "response_format": SCHEMA})
    assert r.status_code == 200, r.text
    sent = seen(stack["vision"])[-1]["body"]
    assert sent["messages"][0]["content"] == content and sent["response_format"] == SCHEMA
    assert r.json()["model"] == "system2-vision"
    assert len(seen(stack["text"])) == nt


def test_system2_timeout_is_enforced_once_without_retry(stack):
    httpx.post(stack["text"] + "/_reply", json={"delay": TIMEOUT_S + 2})
    try:
        before = len(seen(stack["text"]))
        t0 = time.monotonic()
        r = chat(stack, {"model": "system2", "messages": [{"role": "user", "content": "slow"}]})
        took = time.monotonic() - t0
    finally:
        httpx.post(stack["text"] + "/_reply", json={"delay": 0})
    assert r.status_code == 408, r.text
    assert took < TIMEOUT_S + 1.5
    assert len(seen(stack["text"])) == before + 1                      # exactly one upstream attempt


# ── system1 (Laya custom provider) ──────────────────────────────────────────────────────────

def test_system1_single_event(stack):
    msg = json.dumps({"kind": "action", "event": EVENT, "questions": ["risk"], "id": "a-1"})
    r = chat(stack, {"model": "system1", "messages": [{"role": "user", "content": msg}]})
    assert r.status_code == 200, r.text
    data = json.loads(r.json()["choices"][0]["message"]["content"])
    assert data["model"] == "laya-stub" and data["items"][0]["id"] == "a-1"
    assert r.json()["usage"]["total_tokens"] == 0
    assert seen(stack["laya"])[-1]["body"] == {"items": [{"id": "a-1", "kind": "action", "event": EVENT,
                                                          "questions": ["risk"]}]}


def test_system1_items_batch_and_stream(stack):
    payload = {"request_id": "r-9", "items": [{"id": "x", "kind": "action", "event": EVENT},
                                              {"id": "y", "kind": "mission", "event": EVENT}]}
    r = chat(stack, {"model": "system1", "messages": [{"role": "user", "content": json.dumps(payload)}]})
    assert [i["id"] for i in json.loads(r.json()["choices"][0]["message"]["content"])["items"]] == ["x", "y"]
    assert seen(stack["laya"])[-1]["body"] == payload
    s = chat(stack, {"model": "system1", "stream": True, "messages": [{"role": "user", "content": json.dumps(payload)}]})
    assert s.status_code == 200 and "data: [DONE]" in s.text


@pytest.mark.parametrize("content,status,text", [
    (json.dumps({"items": [{"id": LAYA_REJECT_MARKER, "kind": "action", "event": {}}]}), 400, "Field required"),
    (json.dumps({"items": [{"id": LAYA_CRASH_MARKER, "kind": "action", "event": {}}]}), 502, "inference failed"),
    ("not json", 400, "not JSON"),
])
def test_system1_errors_map(stack, content, status, text):
    r = chat(stack, {"model": "system1", "messages": [{"role": "user", "content": content}]})
    assert r.status_code == status and text in r.json()["error"]["message"]


def test_system1_timeout(stack):
    t0 = time.monotonic()
    r = chat(stack, {"model": "system1", "messages": [{"role": "user", "content": json.dumps(
        {"items": [{"id": LAYA_SLOW_MARKER, "kind": "action", "event": {}}]})}]})
    assert r.status_code == 504, r.text              # laya_provider raises 504 before LiteLLM's own 408
    assert time.monotonic() - t0 < TIMEOUT_S + 1.5


# ── embed ───────────────────────────────────────────────────────────────────────────────────

def test_embed_routes_with_float_encoding(stack):
    r = httpx.post(stack["gateway"] + "/v1/embeddings", json={"model": "embed", "input": ["pump too hot", "x"]},
                   headers=AUTH, timeout=30)
    assert r.status_code == 200, r.text
    assert [d["embedding"] for d in r.json()["data"]] == [[0.1, 0.2, 0.3]] * 2
    sent = seen(stack["embed"])[-1]["body"]
    assert sent["input"] == ["pump too hot", "x"] and sent["encoding_format"] == "float"


# ── System 2's real client through the gateway ────────────────────────────────────────────────

def test_system2_llama_generator_and_parse_envelope_through_gateway(stack):
    sys.path.insert(0, str(REPO / "amd/system2"))
    try:
        from analyst.dataset import load_dataset
        from analyst.pipeline import run_pipeline
        from analyst.prompts import example_output
        import analyst.generation as g
    except Exception as exc:   # amd/system2 is edited in parallel; don't fail the gateway suite on its imports
        pytest.skip("amd/system2 not importable here: %r" % exc)
    case = next(c for c in load_dataset(REPO / "amd/system2/data/dev_packets.json") if c.case_id == "kit-equipment")
    valid = example_output(case.prepared)
    httpx.post(stack["text"] + "/_reply", json={"content": json.dumps(valid, ensure_ascii=False), "delay": 0})
    try:
        run = run_pipeline(case.request, g.LlamaGenerator(stack["gateway"], model="system2", api_key=KEY))
        sent = seen(stack["text"])[-1]["body"]
        no_key = run_pipeline(case.request, g.LlamaGenerator(stack["gateway"], model="system2"))
    finally:
        httpx.post(stack["text"] + "/_reply", json={"content": '{"answer":"ok"}'})
    assert run.path == "llm" and run.assessment == valid
    assert run.model == "system2"                       # gateway reports the alias
    assert (run.prompt_tokens, run.completion_tokens, run.tokens_per_sec) == (11, 7, 42.5)
    assert sent["response_format"]["json_schema"]["schema"] == g.response_schema(case.prepared)
    assert sent["chat_template_kwargs"] == {"enable_thinking": False}
    assert no_key.path == "fallback"                    # 401 -> GenerationError -> checked template


# ── tool calling (orchestrator /v1/ask drives Qwen through the gateway) ─────────────────────

def test_tools_and_tool_calls_pass_through(stack):
    tools = [{"type": "function", "function": {"name": "get_flag_context", "description": "flag context",
                                               "parameters": {"type": "object",
                                                              "properties": {"flag_id": {"type": "integer"}},
                                                              "required": ["flag_id"]}}}]
    msgs = [{"role": "user", "content": "why is flag 7 up?"}]
    r = chat(stack, {"model": "system2", "messages": msgs, "tools": tools, "tool_choice": "auto"})
    assert r.status_code == 200, r.text
    choice = r.json()["choices"][0]
    assert choice["finish_reason"] == "tool_calls"
    call = choice["message"]["tool_calls"][0]
    assert call["function"]["name"] == "get_flag_context" and json.loads(call["function"]["arguments"]) == {"flag_id": 7}
    sent = seen(stack["text"])[-1]["body"]
    assert sent["tools"] == tools and sent["tool_choice"] == "auto"
    # the follow-up turn with the tool result is forwarded as-is
    follow = msgs + [choice["message"], {"role": "tool", "tool_call_id": call["id"], "content": '{"flag": 7}'}]
    r2 = chat(stack, {"model": "system2", "messages": follow, "tools": tools})
    assert r2.status_code == 200 and r2.json()["choices"][0]["message"]["content"] == '{"answer":"ok"}'
    assert seen(stack["text"])[-1]["body"]["messages"][-1] == follow[-1]
