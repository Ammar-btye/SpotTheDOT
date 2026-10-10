"""Offline stand-ins for the gateway's upstreams: llama-server (text or vision), Laya /v1/predict, embed.

Each stub records every request it receives (GET /_requests) so tests can assert what the gateway forwarded.
    python tests/stubs.py llama 18080 [name]     # or: laya 18082, embed 18081  (scripts/smoke.sh uses this)
"""
from __future__ import annotations

import asyncio
import sys
import threading
import time
from typing import List

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ENVELOPE_JSON = '{"answer":"ok"}'
LAYA_REJECT_MARKER = "reject-me"
LAYA_CRASH_MARKER = "crash-me"
LAYA_SLOW_MARKER = "slow-me"     # sleeps 4 s


def create_app(role: str, name: str = "") -> FastAPI:
    name = name or role
    app = FastAPI()
    seen: List[dict] = []

    @app.get("/_requests")
    def requests():
        return seen

    @app.get("/health")
    def health():
        return {"status": "ok", "role": role, "name": name}

    if role == "llama":
        reply = {"content": ENVELOPE_JSON, "delay": 0.0}

        @app.post("/_reply")
        async def set_reply(request: Request):
            """Script the next completions: {"content": str, "delay": seconds}."""
            reply.update(await request.json())
            return reply

        @app.post("/v1/chat/completions")
        async def chat(request: Request):
            body = await request.json()
            seen.append({"path": "/v1/chat/completions", "auth": request.headers.get("authorization"),
                         "body": body})
            if body.get("stream"):
                return JSONResponse({"error": "stub does not stream"}, status_code=400)
            if reply["delay"]:
                await asyncio.sleep(float(reply["delay"]))
            if body.get("tools") and body["messages"][-1].get("role") == "user":   # llama-server --jinja tool call
                fn = body["tools"][0]["function"]["name"]
                return {"id": "chatcmpl-tool", "object": "chat.completion", "created": int(time.time()),
                        "model": "stub-%s" % name,
                        "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
                            "role": "assistant", "content": None, "tool_calls": [{
                                "id": "call_1", "type": "function",
                                "function": {"name": fn, "arguments": '{"flag_id": 7}'}}]}}],
                        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}}
            # llama-server's envelope, including its non-OpenAI `timings` block
            return {"id": "chatcmpl-stub", "object": "chat.completion", "created": int(time.time()),
                    "model": "stub-%s" % name,
                    "choices": [{"index": 0, "finish_reason": "stop",
                                 "message": {"role": "assistant", "content": reply["content"]}}],
                    "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
                    "timings": {"prompt_n": 11, "predicted_n": 7, "predicted_per_second": 42.5}}

    elif role == "laya":
        @app.post("/v1/predict")
        async def predict(request: Request):
            body = await request.json()
            seen.append({"path": "/v1/predict", "body": body})
            text = str(body)
            if LAYA_REJECT_MARKER in text:
                return JSONResponse({"error": "items.0.event.battery_pct: Field required", "detail": []},
                                    status_code=422)
            if LAYA_SLOW_MARKER in text:
                await asyncio.sleep(4)
            if LAYA_CRASH_MARKER in text:
                return JSONResponse({"error": "inference failed: RuntimeError"}, status_code=500)
            return {"request_id": body.get("request_id"), "model": "laya-stub", "fine_tuned": False,
                    "device": "cpu", "latency_ms": 3,
                    "items": [{"id": it["id"], "kind": it["kind"],
                               "answers": {"risk": {"answer": "LOW", "probs": {"LOW": 0.9, "HIGH": 0.1},
                                                    "confidence": 0.9}}} for it in body["items"]]}

    elif role == "embed":
        @app.post("/v1/embeddings")
        async def embeddings(request: Request):
            body = await request.json()
            seen.append({"path": "/v1/embeddings", "auth": request.headers.get("authorization"), "body": body})
            if body.get("encoding_format") not in (None, "float"):   # same rule as amd/embed/server.py
                return JSONResponse({"detail": "only encoding_format=float is supported"}, status_code=400)
            texts = [body["input"]] if isinstance(body["input"], str) else body["input"]
            return {"object": "list", "model": "stub-embed",
                    "data": [{"object": "embedding", "index": i, "embedding": [0.1, 0.2, 0.3]}
                             for i, _ in enumerate(texts)],
                    "usage": {"prompt_tokens": 2, "total_tokens": 2}}
    else:
        raise ValueError("unknown stub role %r" % role)
    return app


class ServerThread:
    """Run a stub on 127.0.0.1:port in a daemon thread (tests)."""

    def __init__(self, role: str, port: int, name: str = ""):
        self.server = uvicorn.Server(uvicorn.Config(create_app(role, name), host="127.0.0.1", port=port,
                                                    log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self) -> "ServerThread":
        self.thread.start()
        deadline = time.monotonic() + 10
        while not self.server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("stub did not start")
            time.sleep(0.05)
        return self

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)


if __name__ == "__main__":
    uvicorn.run(create_app(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else ""), host="127.0.0.1", port=int(sys.argv[2]), log_level="warning")
