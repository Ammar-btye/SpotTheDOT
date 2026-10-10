"""Query embeddings through the OpenAI-compatible /v1/embeddings API (contract §1)."""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Protocol

from .db import LogSink, NullLogSink


class EmbeddingError(RuntimeError):
    pass


class Embedder(Protocol):
    async def embed_queries(self, texts: List[str], request_id: Optional[str] = None) -> List[List[float]]: ...
    async def close(self) -> None: ...


class HttpEmbedder:
    """Prepends EMBED_QUERY_PREFIX, batches inputs, checks the dimension and caches recent queries."""

    def __init__(self, url: str, model: str, dim: int, query_prefix: str = "", timeout_s: float = 10.0,
                 sink: Optional[LogSink] = None, cache_size: int = 256, transport: Any = None):
        import httpx2

        self.url = url.rstrip("/") + "/v1/embeddings"
        self.model, self.dim, self.prefix = model, dim, query_prefix
        self._sink = sink or NullLogSink()
        self._cache: "OrderedDict[str, List[float]]" = OrderedDict()
        self._cache_size = cache_size
        self._client = httpx2.AsyncClient(timeout=timeout_s, transport=transport)

    async def embed_queries(self, texts: List[str], request_id: Optional[str] = None) -> List[List[float]]:
        out: Dict[int, List[float]] = {}
        todo = []
        for i, t in enumerate(texts):
            hit = self._cache.get(t)
            if hit is not None:
                self._cache.move_to_end(t)
                out[i] = hit
            else:
                todo.append(i)
        if todo:
            vecs = await self._post([self.prefix + texts[i] for i in todo], request_id)
            for i, v in zip(todo, vecs):
                out[i] = v
                self._cache[texts[i]] = v
                if len(self._cache) > self._cache_size:
                    self._cache.popitem(last=False)
        return [out[i] for i in range(len(texts))]

    async def _post(self, inputs: List[str], request_id: Optional[str]) -> List[List[float]]:
        t0 = time.perf_counter()
        err: Optional[str] = None
        usage: Dict[str, Any] = {}
        try:
            r = await self._client.post(self.url, json={"model": self.model, "input": inputs})
            if r.status_code != 200:
                raise EmbeddingError("embedding service returned HTTP %d: %s" % (r.status_code, r.text[:200]))
            body = r.json()
            usage = body.get("usage") or {}
            data = sorted(body["data"], key=lambda d: d.get("index", 0))
            vecs = [d["embedding"] for d in data]
            if len(vecs) != len(inputs):
                raise EmbeddingError("embedding service returned %d vectors for %d inputs" % (len(vecs), len(inputs)))
            for v in vecs:
                if len(v) != self.dim:
                    raise EmbeddingError("embedding dimension %d != EMBED_DIM %d (wrong EMBED_MODEL?)" % (len(v), self.dim))
            return vecs
        except EmbeddingError as exc:
            err = str(exc)
            raise
        except Exception as exc:  # network errors, bad JSON
            err = "%s: %s" % (type(exc).__name__, exc)
            raise EmbeddingError("embedding service unreachable at %s (%s)" % (self.url, err)) from exc
        finally:
            self._sink.model_call({
                "request_id": request_id, "system": "embed", "model": self.model, "endpoint": self.url,
                "input_tokens": usage.get("prompt_tokens") or usage.get("total_tokens"),
                "latency_ms": int((time.perf_counter() - t0) * 1000), "ok": err is None, "error": err,
                "metadata": {"n_inputs": len(inputs), "caller": "spot-mcp"},
            })

    async def close(self) -> None:
        await self._client.aclose()
