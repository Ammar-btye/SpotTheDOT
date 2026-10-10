"""laya_provider: chat message -> /v1/predict body, Laya response/errors -> chat completion or CustomLLMError.

Offline: the HTTP tests run the stub Laya from tests/stubs.py on 127.0.0.1.
"""
import asyncio
import json
import socket
import sys
from pathlib import Path

import httpx
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import laya_provider as lp  # noqa: E402
from litellm.llms.custom_llm import CustomLLMError  # noqa: E402
from litellm.types.utils import ModelResponse  # noqa: E402
from stubs import LAYA_CRASH_MARKER, LAYA_REJECT_MARKER, ServerThread  # noqa: E402

EVENT = {"mission_id": "M-1", "action_id": "A-1"}


def user(content):
    return [{"role": "system", "content": "ignored"}, {"role": "user", "content": content}]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def laya():
    port = free_port()
    srv = ServerThread("laya", port).start()
    yield "http://127.0.0.1:%d" % port
    srv.stop()


# ── predict_body ──────────────────────────────────────────────────────────────────────────────

def test_single_event_is_wrapped_into_items():
    body = lp.predict_body(user(json.dumps({"kind": "action", "event": EVENT, "questions": ["risk"], "id": "a-1"})))
    assert body == {"items": [{"id": "a-1", "kind": "action", "event": EVENT, "questions": ["risk"]}]}


def test_single_event_defaults_id_and_omits_missing_questions():
    body = lp.predict_body(user(json.dumps({"kind": "mission", "event": EVENT, "request_id": "r1"})))
    assert body == {"request_id": "r1", "items": [{"id": "1", "kind": "mission", "event": EVENT}]}


def test_items_shape_passes_through_unchanged():
    payload = {"request_id": "r", "items": [{"id": "x", "kind": "action", "event": EVENT}]}
    assert lp.predict_body(user(json.dumps(payload))) == payload


def test_last_user_message_wins_and_content_arrays_are_joined():
    old = json.dumps({"kind": "action", "event": {"old": 1}})
    new = json.dumps({"kind": "action", "event": EVENT})
    msgs = [{"role": "user", "content": old}, {"role": "assistant", "content": "x"},
            {"role": "user", "content": [{"type": "text", "text": new[:10]}, {"type": "text", "text": new[10:]}]}]
    assert lp.predict_body(msgs)["items"][0]["event"] == EVENT


@pytest.mark.parametrize("messages", [
    [], [{"role": "system", "content": "{}"}], user("not json"), user("[1, 2]"), user('{"kind": "action"}'),
    user('{"items": []}'), user('{"items": {"id": 1}}'),
])
def test_bad_messages_are_400(messages):
    with pytest.raises(CustomLLMError) as err:
        lp.predict_body(messages)
    assert err.value.status_code == 400


# ── response / errors ────────────────────────────────────────────────────────────────────────

def _resp(status, payload):
    return httpx.Response(status, content=payload if isinstance(payload, bytes) else json.dumps(payload).encode())


def test_check_response_maps_status_codes():
    assert lp.check_response(_resp(200, {"items": []})) == {"items": []}
    for status, payload, want, text in [
        (422, {"error": "items.0.event.x: Field required"}, 400, "Field required"),
        (400, {"detail": "bad"}, 400, "bad"),
        (500, {"error": "inference failed"}, 502, "inference failed"),
        (200, b"not json", 502, "non-JSON"),
        (200, {"no": "items"}, 502, "no items"),
    ]:
        with pytest.raises(CustomLLMError) as err:
            lp.check_response(_resp(status, payload))
        assert err.value.status_code == want and text in err.value.message


def test_fill_response_puts_laya_json_in_the_assistant_message():
    data = {"model": "laya-ft", "items": [{"id": "1", "kind": "action", "answers": {}}]}
    out = lp.fill_response(ModelResponse(), data, "laya")
    assert json.loads(out.choices[0].message.content) == data
    assert out.choices[0].finish_reason == "stop" and out.model == "laya/laya-ft"
    assert (out.usage.prompt_tokens, out.usage.completion_tokens, out.usage.total_tokens) == (0, 0, 0)


def test_target_strips_v1_and_reads_timeout(monkeypatch):
    monkeypatch.setenv("SYSTEM1_TIMEOUT_S", "7")
    assert lp._target("http://laya:8082/v1/", None) == ("http://laya:8082/v1/predict", 7.0)
    assert lp._target("http://laya:8082", "3.0") == ("http://laya:8082/v1/predict", 3.0)
    assert lp._target("http://laya:8082", httpx.Timeout(4.0)) == ("http://laya:8082/v1/predict", 4.0)
    monkeypatch.setenv("SYSTEM1_URL", "http://env:1")
    assert lp._target(None, 1)[0] == "http://env:1/v1/predict"


# ── provider against the stub (sync + async + stream) ───────────────────────────────────────

def _call(provider_fn, laya, content, **kw):
    return provider_fn(model="laya", messages=user(content), api_base=laya, custom_prompt_dict={},
                       model_response=ModelResponse(), print_verbose=print, encoding=None, api_key=None,
                       logging_obj=None, optional_params={}, timeout=5, **kw)


def test_completion_and_acompletion_round_trip(laya):
    msg = json.dumps({"kind": "action", "event": EVENT, "id": "a-1"})
    sync = _call(lp.laya_provider.completion, laya, msg)
    asyn = asyncio.run(_call(lp.laya_provider.acompletion, laya, msg))
    for out in (sync, asyn):
        data = json.loads(out.choices[0].message.content)
        assert data["items"][0]["id"] == "a-1" and data["model"] == "laya-stub"


def test_streaming_yields_one_final_chunk(laya):
    msg = json.dumps({"kind": "action", "event": EVENT})
    chunks = list(_call(lp.laya_provider.streaming, laya, msg))

    async def collect():
        return [c async for c in _call(lp.laya_provider.astreaming, laya, msg)]

    for got in (chunks, asyncio.run(collect())):
        assert len(got) == 1 and got[0]["is_finished"] and got[0]["finish_reason"] == "stop"
        assert json.loads(got[0]["text"])["items"][0]["id"] == "1"


@pytest.mark.parametrize("marker,status", [(LAYA_REJECT_MARKER, 400), (LAYA_CRASH_MARKER, 502)])
def test_laya_errors_map(laya, marker, status):
    msg = json.dumps({"items": [{"id": marker, "kind": "action", "event": EVENT}]})
    with pytest.raises(CustomLLMError) as err:
        _call(lp.laya_provider.completion, laya, msg)
    assert err.value.status_code == status


def test_unreachable_laya_is_503():
    msg = json.dumps({"kind": "action", "event": EVENT})
    with pytest.raises(CustomLLMError) as err:
        _call(lp.laya_provider.completion, "http://127.0.0.1:%d" % free_port(), msg)
    assert err.value.status_code == 503
