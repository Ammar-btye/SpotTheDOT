"""Client for the System 1 service (Laya), docs/backend-services-contract.md "System 1 service".

POST {SYSTEM1_URL}/v1/predict {"request_id", "items": [{"id", "kind", "event"}]} -> answers per item.
Logging (audit M2): the System 1 service logs every call it answers to app.model_calls (the true model latency),
so this client logs only FAILED calls (ok=false, metadata.caller='backend'), never a duplicate success row.
Load (audit H2): Laya serves one request at a time. Ingest calls pass `skip_if_busy=True`, so while an explicit
batch call (forecast, /system1/predict) is in flight they fail fast to rules-only instead of queueing behind it,
and they use the short `ingest_timeout_s`.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import httpx

from .calllog import LogSink
from .http import Breaker, ServiceUnavailable, short_error

MAX_ITEMS = 64


class System1Client:
    name = "system1"

    def __init__(self, base_url: str, http: httpx.AsyncClient, sink: LogSink, timeout_s: float = 5.0,
                 breaker: Optional[Breaker] = None, ingest_timeout_s: Optional[float] = None):
        self.base_url = base_url.rstrip("/")
        self.http = http
        self.sink = sink
        self.timeout_s = timeout_s
        self.ingest_timeout_s = ingest_timeout_s or timeout_s
        self.breaker = breaker or Breaker()
        self.batch_inflight = 0

    async def predict(self, items: List[Dict[str, Any]], request_id: Optional[str] = None,
                      action_id: Optional[str] = None, skip_if_busy: bool = False) -> Dict[str, Any]:
        """Call /v1/predict (batches of <= 64 items). Raises ServiceUnavailable on any failure.
        `skip_if_busy=True` (the ingest path): short timeout, and fail fast while a batch call holds Laya."""
        if not self.base_url:
            raise ServiceUnavailable(self.name, "SYSTEM1_URL is not set")
        if not self.breaker.allow():
            raise ServiceUnavailable(self.name, "circuit open after: %s" % self.breaker.last_error)
        if skip_if_busy and self.batch_inflight:
            raise ServiceUnavailable(self.name, "busy: a forecast/batch call holds Laya; rules-only")
        if skip_if_busy:
            return await self._predict(items, request_id, action_id, self.ingest_timeout_s)
        self.batch_inflight += 1
        try:
            return await self._predict(items, request_id, action_id, self.timeout_s)
        finally:
            self.batch_inflight -= 1

    async def _predict(self, items: List[Dict[str, Any]], request_id: Optional[str], action_id: Optional[str],
                       timeout_s: float) -> Dict[str, Any]:
        out: Dict[str, Any] = {"items": []}
        for i in range(0, len(items), MAX_ITEMS):
            chunk = items[i:i + MAX_ITEMS]
            t0 = time.perf_counter()
            try:
                r = await self.http.post(self.base_url + "/v1/predict",
                                         json={"request_id": request_id, "items": chunk},
                                         headers={"X-Request-ID": request_id or ""}, timeout=timeout_s)
                ms = int((time.perf_counter() - t0) * 1000)
                if r.status_code != 200:
                    raise ServiceUnavailable(self.name, "HTTP %d: %s" % (r.status_code, r.text[:200]))
                body = r.json()
            except ServiceUnavailable as exc:
                self.breaker.failure(exc.reason)
                self.sink.model_call(system=self.name, ok=False, endpoint="/v1/predict", request_id=request_id,
                                     action_id=action_id, latency_ms=int((time.perf_counter() - t0) * 1000),
                                     error=exc.reason, metadata={"items": len(chunk)})
                raise
            except (httpx.HTTPError, ValueError) as exc:
                err = short_error(exc)
                self.breaker.failure(err)
                self.sink.model_call(system=self.name, ok=False, endpoint="/v1/predict", request_id=request_id,
                                     action_id=action_id, latency_ms=int((time.perf_counter() - t0) * 1000),
                                     error=err, metadata={"items": len(chunk)})
                raise ServiceUnavailable(self.name, err) from exc
            self.breaker.success()   # success is logged by the System 1 service itself (audit M2)
            for k in ("model", "fine_tuned", "device"):
                out.setdefault(k, body.get(k))
            out["latency_ms"] = out.get("latency_ms", 0) + ms
            out["items"].extend(body.get("items") or [])
        return out

    async def get(self, path: str) -> Dict[str, Any]:
        if not self.base_url:
            raise ServiceUnavailable(self.name, "SYSTEM1_URL is not set")
        try:
            r = await self.http.get(self.base_url + path, timeout=min(self.timeout_s, 3.0))
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ServiceUnavailable(self.name, short_error(exc)) from exc

    async def health(self) -> Dict[str, Any]:
        try:
            body = await self.get("/health")
            return {"status": "up" if body.get("ok", True) else "degraded", **body}
        except ServiceUnavailable as exc:
            return {"status": "down", "error": exc.reason}
