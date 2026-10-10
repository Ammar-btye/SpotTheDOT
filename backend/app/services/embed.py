"""Client for the embedding service (OpenAI-compatible, docs/system2-rag-contract.md §1).

POST {EMBED_URL}/v1/embeddings {"model", "input": [...]} -> {"data": [{"index", "embedding"}]}.
Queries get EMBED_QUERY_PREFIX, documents get EMBED_DOC_PREFIX (the stored `content` never includes it).
"""
from __future__ import annotations

import time
from typing import List, Optional

import httpx

from .calllog import LogSink
from .http import Breaker, ServiceUnavailable, short_error


def vec_literal(vec: List[float]) -> str:
    return "[" + ",".join("%.7g" % float(x) for x in vec) + "]"


class EmbedClient:
    name = "embed"

    def __init__(self, base_url: str, model: str, dim: int, query_prefix: str, doc_prefix: str,
                 http: httpx.AsyncClient, sink: LogSink, timeout_s: float = 5.0, breaker: Optional[Breaker] = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dim = dim
        self.query_prefix = query_prefix
        self.doc_prefix = doc_prefix
        self.http = http
        self.sink = sink
        self.timeout_s = timeout_s
        self.breaker = breaker or Breaker()

    def _query_text(self, q: str) -> str:
        if not self.query_prefix:
            return q
        sep = "" if self.query_prefix.endswith((" ", "\n")) else " "
        return self.query_prefix + sep + q

    async def embed_query(self, text: str, request_id: Optional[str] = None,
                          timeout_s: Optional[float] = None) -> List[float]:
        return (await self._embed([self._query_text(text)], request_id, "query", timeout_s))[0]

    async def embed_documents(self, texts: List[str], request_id: Optional[str] = None) -> List[List[float]]:
        return await self._embed([self.doc_prefix + t for t in texts], request_id, "document")

    async def _embed(self, inputs: List[str], request_id: Optional[str], purpose: str,
                     timeout_s: Optional[float] = None) -> List[List[float]]:
        if not self.base_url:
            raise ServiceUnavailable(self.name, "EMBED_URL is not set")
        if not self.breaker.allow():
            raise ServiceUnavailable(self.name, "circuit open after: %s" % self.breaker.last_error)
        t0 = time.perf_counter()
        try:
            r = await self.http.post(self.base_url + "/v1/embeddings", json={"model": self.model, "input": inputs},
                                     headers={"X-Request-ID": request_id or ""},
                                     timeout=timeout_s or self.timeout_s)
            if r.status_code != 200:
                raise ServiceUnavailable(self.name, "HTTP %d: %s" % (r.status_code, r.text[:200]))
            body = r.json()
            data = sorted(body["data"], key=lambda d: d.get("index", 0))
            vecs = [d["embedding"] for d in data]
            if len(vecs) != len(inputs):
                raise ServiceUnavailable(self.name, "expected %d embeddings, got %d" % (len(inputs), len(vecs)))
            bad = [len(v) for v in vecs if len(v) != self.dim]
            if bad:
                raise ServiceUnavailable(self.name, "embedding dim %d != EMBED_DIM %d" % (bad[0], self.dim))
        except ServiceUnavailable as exc:
            self._fail(exc.reason, t0, request_id, purpose, len(inputs))
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            err = short_error(exc)
            self._fail(err, t0, request_id, purpose, len(inputs))
            raise ServiceUnavailable(self.name, err) from exc
        ms = int((time.perf_counter() - t0) * 1000)
        self.breaker.success()
        usage = body.get("usage") or {}
        tokens = usage.get("prompt_tokens") or usage.get("total_tokens")
        self.sink.model_call(system=self.name, ok=True, endpoint="/v1/embeddings", request_id=request_id,
                             model=body.get("model") or self.model, latency_ms=ms, input_tokens=tokens,
                             tokens_per_sec=(round(tokens / (ms / 1000.0), 1) if tokens and ms else None),
                             metadata={"purpose": purpose, "inputs": len(inputs)})
        return vecs

    def _fail(self, err: str, t0: float, request_id: Optional[str], purpose: str, n: int) -> None:
        self.breaker.failure(err)
        self.sink.model_call(system=self.name, ok=False, endpoint="/v1/embeddings", request_id=request_id,
                             model=self.model, latency_ms=int((time.perf_counter() - t0) * 1000), error=err,
                             metadata={"purpose": purpose, "inputs": n})

    async def health(self) -> dict:
        if not self.base_url:
            return {"status": "unset"}
        try:
            r = await self.http.get(self.base_url + "/health", timeout=2.0)
            if r.status_code == 404:  # server without /health (e.g. plain llama-server builds): reachable is enough
                return {"status": "up"}
            return {"status": "up" if r.status_code == 200 else "degraded", "http": r.status_code}
        except httpx.HTTPError as exc:
            return {"status": "down", "error": short_error(exc)}
