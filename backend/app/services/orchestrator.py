"""Orchestrator client (amd/orchestrator, LangGraph, docs/orchestrator-contract.md).

Optional: only used when ORCHESTRATOR_URL is set. `/flags/{id}/explain` then asks `POST /v1/assess` first and falls
back to the backend's own MCP -> System 2 -> template path when the orchestrator is down or had no context packet
(services/flags.py). `POST /api/v1/ask` proxies to `POST /v1/ask`.

Same pattern as System2Client: one breaker, no retries, every failure is ServiceUnavailable. Calls are logged to
`app.model_calls` as `system='system2'` (the table's CHECK allows system1/system2/embed only; the orchestrator's
assess path ends in System 2) with `endpoint='orchestrator:/v1/assess'` and `metadata.via='orchestrator'`.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

import httpx

from .calllog import LogSink
from .http import Breaker, ServiceUnavailable, short_error


class OrchestratorClient:
    name = "orchestrator"

    def __init__(self, base_url: Optional[str], http: httpx.AsyncClient, sink: LogSink, api_key: Optional[str] = None,
                 timeout_s: float = 42.0, breaker: Optional[Breaker] = None):
        self.base_url = (base_url or "").rstrip("/") or None
        self.http = http
        self.sink = sink
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.breaker = breaker or Breaker()

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    async def _post(self, path: str, body: Dict[str, Any], request_id: Optional[str], flag_id: Optional[int] = None,
                    action_id: Optional[str] = None, timeout_s: Optional[float] = None) -> Dict[str, Any]:
        if not self.base_url:
            raise ServiceUnavailable(self.name, "ORCHESTRATOR_URL is not set")
        if not self.breaker.allow():
            raise ServiceUnavailable(self.name, "circuit open after: %s" % self.breaker.last_error)
        headers = {"X-Request-ID": request_id or ""}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        timeout = self.timeout_s if timeout_s is None else min(self.timeout_s, timeout_s)
        t0 = time.perf_counter()
        try:
            payload = json.loads(json.dumps(body, default=str))
            r = await self.http.post(self.base_url + path, json=payload, headers=headers, timeout=timeout)
            if r.status_code != 200:
                err = ServiceUnavailable(self.name, "HTTP %d: %s" % (r.status_code, r.text[:200]))
                # A 4xx is about this request (e.g. a 422 image), not the service's health: don't open the breaker.
                err.client_error = 400 <= r.status_code < 500 and r.status_code not in (401, 403)  # type: ignore
                raise err
            out = r.json()
            if not isinstance(out, dict):
                raise ServiceUnavailable(self.name, "response is not a JSON object")
        except ServiceUnavailable as exc:
            self._log(False, path, t0, request_id, flag_id, action_id, error=exc.reason)
            if not getattr(exc, "client_error", False):
                self.breaker.failure(exc.reason)
            raise
        except (httpx.HTTPError, ValueError) as exc:
            err = short_error(exc)
            self._log(False, path, t0, request_id, flag_id, action_id, error=err)
            self.breaker.failure(err)
            raise ServiceUnavailable(self.name, err) from exc
        self.breaker.success()
        self._log(True, path, t0, request_id, flag_id, action_id, out=out)
        return out

    def _log(self, ok: bool, path: str, t0: float, request_id, flag_id, action_id, error=None, out=None) -> None:
        out = out or {}
        s2 = out.get("system2") if isinstance(out.get("system2"), dict) else {}
        meta = {"via": "orchestrator"}
        if out:
            meta.update({k: out.get(k) for k in ("route", "source", "context_source", "fallback_reason", "mode",
                                                 "elapsed_ms") if out.get(k) is not None})
            if s2.get("path"):
                meta["system2_path"] = s2.get("path")
        self.sink.model_call(
            system="system2", ok=ok, endpoint="orchestrator:" + path, request_id=request_id, flag_id=flag_id,
            action_id=action_id, model=out.get("model"), latency_ms=int((time.perf_counter() - t0) * 1000),
            error=error, tokens_per_sec=out.get("tokens_per_sec"), metadata=meta)

    async def assess(self, body: Dict[str, Any], request_id: Optional[str], flag_id: Optional[int],
                     action_id: Optional[str], timeout_s: Optional[float] = None) -> Dict[str, Any]:
        return await self._post("/v1/assess", body, request_id, flag_id, action_id, timeout_s)

    async def ask(self, body: Dict[str, Any], request_id: Optional[str],
                  timeout_s: Optional[float] = None) -> Dict[str, Any]:
        return await self._post("/v1/ask", body, request_id, body.get("flag_id"), None, timeout_s)

    async def health(self) -> dict:
        if not self.base_url:
            return {"status": "unset"}
        try:
            r = await self.http.get(self.base_url + "/health", timeout=2.0)
            return {"status": "up" if r.status_code == 200 else "degraded", "http": r.status_code}
        except httpx.HTTPError as exc:
            return {"status": "down", "error": short_error(exc)}
