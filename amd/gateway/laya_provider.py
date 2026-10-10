"""LiteLLM custom provider `laya/…`: the gateway alias `system1` -> System 1 (Laya) POST /v1/predict.

Chat in, triage out. The LAST user message's content is a JSON object in one of two shapes:
    {"kind": "action", "event": {...}, "questions": [...], "id": "a-1"}   one event ("id"/"questions" optional)
    {"request_id": "...", "items": [{"id": ..., "kind": ..., "event": {...}, "questions": [...]}, ...]}
(the second is exactly the /v1/predict body, docs/backend-services-contract.md). Content may also be an OpenAI
content array; its text parts are joined. The System 1 response JSON becomes the assistant message content
(compact JSON, keys as Laya sent them), finish_reason "stop", usage all zeros: Laya is a classifier, not a
token generator. `stream: true` is accepted and yields that same content as a single chunk. Nothing is retried here (router num_retries 0); the caller decides what a failure means.

Errors (CustomLLMError -> the proxy's HTTP status): a message that is not that JSON, or any 4xx from Laya
(422 validation, 400) -> 400 with Laya's own "error" text; Laya 5xx or a non-JSON body -> 502; connect failure
-> 503; timeout -> 504. Config: api_base from config.yaml (os.environ/SYSTEM1_URL), else env SYSTEM1_URL;
timeout from the model's litellm_params, else env SYSTEM1_TIMEOUT_S (default 10 s: CPU Laya ~3-8 s/event).
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, AsyncIterator, Iterator, Optional, Tuple

import httpx
from litellm import CustomLLM
from litellm.llms.custom_llm import CustomLLMError
from litellm.types.utils import Choices, GenericStreamingChunk, Message, ModelResponse, Usage

DEFAULT_URL = "http://127.0.0.1:8082"
DEFAULT_TIMEOUT_S = 10.0
MAX_ERROR_CHARS = 500


# ── request / response shaping (pure; unit-tested without a proxy) ─────────────────────────────

def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):   # OpenAI content array: join the text parts, ignore anything else
        return "".join(p.get("text", "") for p in content
                       if isinstance(p, dict) and p.get("type") == "text" and isinstance(p.get("text"), str))
    return ""


def predict_body(messages: list) -> dict:
    """Last user message -> /v1/predict body; CustomLLMError(400) when it isn't one of the two JSON shapes."""
    users = [m for m in messages or [] if isinstance(m, dict) and m.get("role") == "user"]
    if not users:
        raise CustomLLMError(400, "system1: no user message; send the /v1/predict JSON as the last user message")
    raw = _text(users[-1].get("content")).strip()
    try:
        payload = json.loads(raw)
    except ValueError:
        raise CustomLLMError(400, "system1: last user message is not JSON; send "
                                  '{"kind": ..., "event": {...}, "questions": [...]} or {"items": [...]}') from None
    if not isinstance(payload, dict):
        raise CustomLLMError(400, "system1: last user message must be a JSON object")
    if "items" in payload:
        if not isinstance(payload["items"], list) or not payload["items"]:
            raise CustomLLMError(400, "system1: items must be a non-empty list")
        return payload
    if "kind" in payload and "event" in payload:
        item = {"id": str(payload.get("id") or "1"), "kind": payload["kind"], "event": payload["event"]}
        if payload.get("questions") is not None:
            item["questions"] = payload["questions"]
        body = {"items": [item]}
        if payload.get("request_id") is not None:
            body["request_id"] = payload["request_id"]
        return body
    raise CustomLLMError(400, 'system1: JSON needs "items" or both "kind" and "event"')


def _error_text(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        msg = (data.get("error") or data.get("detail")) if isinstance(data, dict) else None
        msg = msg if isinstance(msg, str) else json.dumps(data)
    except ValueError:
        msg = resp.text
    return (msg or "status %d" % resp.status_code)[:MAX_ERROR_CHARS]


def check_response(resp: httpx.Response) -> dict:
    """Laya HTTP response -> its JSON object; 4xx -> 400 (Laya's message), anything else wrong -> 502."""
    if 400 <= resp.status_code < 500:
        raise CustomLLMError(400, "system1 rejected the request (%d): %s" % (resp.status_code, _error_text(resp)))
    if resp.status_code != 200:
        raise CustomLLMError(502, "system1 error %d: %s" % (resp.status_code, _error_text(resp)))
    try:
        data = resp.json()
    except ValueError:
        raise CustomLLMError(502, "system1 returned non-JSON") from None
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise CustomLLMError(502, "system1 response has no items list")
    return data


def _content(data: dict) -> str:
    return json.dumps(data, separators=(",", ":"))


def fill_response(model_response: ModelResponse, data: dict, model: str) -> ModelResponse:
    model_response.choices = [Choices(index=0, finish_reason="stop",
                                      message=Message(role="assistant", content=_content(data)))]
    model_response.model = "laya/" + (data.get("model") if isinstance(data.get("model"), str) else model)
    model_response.created = int(time.time())
    setattr(model_response, "usage", Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0))
    return model_response


def one_chunk(data: dict) -> GenericStreamingChunk:
    return {"text": _content(data), "is_finished": True, "finish_reason": "stop", "index": 0, "tool_use": None,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}


def _target(api_base: Optional[str], timeout: Any) -> Tuple[str, float]:
    base = (api_base or os.environ.get("SYSTEM1_URL") or DEFAULT_URL).rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    if isinstance(timeout, httpx.Timeout):
        timeout = timeout.read
    try:
        t = float(timeout) if timeout is not None else float(os.environ.get("SYSTEM1_TIMEOUT_S", DEFAULT_TIMEOUT_S))
    except (TypeError, ValueError):
        t = DEFAULT_TIMEOUT_S
    return base + "/v1/predict", t if t > 0 else DEFAULT_TIMEOUT_S


def _transport_error(exc: Exception, url: str, t: float) -> CustomLLMError:
    if isinstance(exc, httpx.TimeoutException):
        return CustomLLMError(504, "system1 did not answer within %.1f s" % t)
    return CustomLLMError(503, "system1 unreachable at %s: %s" % (url, type(exc).__name__))


# ── the provider ─────────────────────────────────────────────────────────────────────────────

class LayaProvider(CustomLLM):
    """`stream: true` works but yields the whole answer as one chunk: Laya returns one JSON object."""

    def _call(self, messages, api_base, timeout) -> dict:
        body = predict_body(messages)
        url, t = _target(api_base, timeout)
        try:
            with httpx.Client(timeout=t, follow_redirects=False, trust_env=False) as http:
                resp = http.post(url, json=body)
        except httpx.HTTPError as exc:
            raise _transport_error(exc, url, t) from None
        return check_response(resp)

    async def _acall(self, messages, api_base, timeout) -> dict:
        body = predict_body(messages)
        url, t = _target(api_base, timeout)
        try:
            async with httpx.AsyncClient(timeout=t, follow_redirects=False, trust_env=False) as http:
                resp = await http.post(url, json=body)
        except httpx.HTTPError as exc:
            raise _transport_error(exc, url, t) from None
        return check_response(resp)

    def completion(self, model, messages, api_base, custom_prompt_dict, model_response, print_verbose, encoding,
                   api_key, logging_obj, optional_params, acompletion=None, litellm_params=None, logger_fn=None,
                   headers={}, timeout=None, client=None) -> ModelResponse:
        return fill_response(model_response, self._call(messages, api_base, timeout), model)

    async def acompletion(self, model, messages, api_base, custom_prompt_dict, model_response, print_verbose,
                          encoding, api_key, logging_obj, optional_params, acompletion=None, litellm_params=None,
                          logger_fn=None, headers={}, timeout=None, client=None) -> ModelResponse:
        return fill_response(model_response, await self._acall(messages, api_base, timeout), model)

    def streaming(self, model, messages, api_base, custom_prompt_dict, model_response, print_verbose, encoding,
                  api_key, logging_obj, optional_params, acompletion=None, litellm_params=None, logger_fn=None,
                  headers={}, timeout=None, client=None) -> Iterator[GenericStreamingChunk]:
        yield one_chunk(self._call(messages, api_base, timeout))

    async def astreaming(self, model, messages, api_base, custom_prompt_dict, model_response, print_verbose,
                         encoding, api_key, logging_obj, optional_params, acompletion=None, litellm_params=None,
                         logger_fn=None, headers={}, timeout=None, client=None) -> AsyncIterator[GenericStreamingChunk]:
        yield one_chunk(await self._acall(messages, api_base, timeout))


laya_provider = LayaProvider()   # referenced from config.yaml: custom_provider_map[].custom_handler
