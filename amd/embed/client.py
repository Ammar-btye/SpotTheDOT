"""Tiny client for the contract's OpenAI-compatible embedding API (contract §1).

    from client import embed
    vecs = embed(["pump bearing too hot"], kind="query")      # adds EMBED_QUERY_PREFIX
    vecs = embed(docs, kind="doc")                             # adds EMBED_DOC_PREFIX

Works against amd/embed/server.py, llama-server --embedding, TEI or Infinity. Vectors are returned as-is
(no client-side normalization; the search functions use cosine distance). `to_pgvector()` formats a vector
as a pgvector literal for `%s::vector` parameters.
"""
import os
import time
from typing import Callable, List, Optional, Sequence

import httpx


def _env_prefix(name: str) -> str:
    # .env files can't hold a real newline easily: accept a literal "\n" and turn it into one.
    return os.environ.get(name, "").replace("\\n", "\n")


class EmbedClient:
    def __init__(self, url: Optional[str] = None, model: Optional[str] = None, dim: Optional[int] = None,
                 query_prefix: Optional[str] = None, doc_prefix: Optional[str] = None, batch_size: int = 32,
                 timeout: float = 300.0, on_call: Optional[Callable[[dict], None]] = None):
        self.url = (url or os.environ.get("EMBED_URL", "http://localhost:8081")).rstrip("/")
        self.model = model or os.environ.get("EMBED_MODEL", "")
        self.dim = dim or int(os.environ.get("EMBED_DIM", "1024"))
        self.query_prefix = _env_prefix("EMBED_QUERY_PREFIX") if query_prefix is None else query_prefix
        self.doc_prefix = _env_prefix("EMBED_DOC_PREFIX") if doc_prefix is None else doc_prefix
        self.batch_size = int(os.environ.get("EMBED_CLIENT_BATCH", batch_size))
        self.on_call = on_call            # called once per HTTP batch with timing (for app.model_calls)
        self.http = httpx.Client(timeout=timeout)

    def health(self) -> dict:
        r = self.http.get(self.url + "/health")
        return r.json() if r.headers.get("content-type", "").startswith("application/json") else {"status": r.status_code}

    def wait_ready(self, timeout_s: float = 900) -> dict:
        t0 = time.time()
        while True:
            try:
                h = self.health()
                if h.get("status") == "ok":
                    return h
                if h.get("status") == "error":
                    raise RuntimeError("embedding server failed: %s" % h)
            except httpx.TransportError:
                pass
            if time.time() - t0 > timeout_s:
                raise TimeoutError("embedding server at %s not ready after %ds" % (self.url, timeout_s))
            time.sleep(2)

    def embed(self, texts: Sequence[str], kind: str = "doc") -> List[List[float]]:
        if kind not in ("query", "doc"):
            raise ValueError("kind must be 'query' or 'doc'")
        prefix = self.query_prefix if kind == "query" else self.doc_prefix
        out: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = [prefix + t for t in texts[i:i + self.batch_size]]
            t0 = time.perf_counter()
            r = self.http.post(self.url + "/v1/embeddings", json={"model": self.model, "input": batch})
            ms = (time.perf_counter() - t0) * 1000
            if r.status_code != 200:
                raise RuntimeError("embedding request failed (%d): %s" % (r.status_code, r.text[:500]))
            body = r.json()
            vecs = [d["embedding"] for d in sorted(body["data"], key=lambda d: d["index"])]
            if vecs and len(vecs[0]) != self.dim:
                raise ValueError("embedding has %d dims but EMBED_DIM=%d (model %s); fix EMBED_DIM or the model"
                                 % (len(vecs[0]), self.dim, body.get("model")))
            out.extend(vecs)
            if self.on_call:
                usage = body.get("usage") or {}
                timing = body.get("timing") or {}
                self.on_call({"model": body.get("model") or self.model, "endpoint": self.url + "/v1/embeddings",
                              "n": len(batch), "kind": kind, "latency_ms": int(ms),
                              "input_tokens": usage.get("prompt_tokens"), "server_ms": timing.get("ms"),
                              "device": timing.get("device"), "gpu": timing.get("gpu")})
        return out


_default: Optional[EmbedClient] = None


def embed(texts: Sequence[str], kind: str = "query") -> List[List[float]]:
    """Module-level convenience using env config. kind='query' adds EMBED_QUERY_PREFIX, 'doc' EMBED_DOC_PREFIX."""
    global _default
    if _default is None:
        _default = EmbedClient()
    return _default.embed(list(texts), kind=kind)


def to_pgvector(vec: Sequence[float]) -> str:
    return "[" + ",".join("%.7g" % x for x in vec) + "]"
