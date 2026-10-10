"""Configuration from environment variables (names follow docs/system2-rag-contract.md)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

DEFAULT_QUERY_PREFIX = ("Instruct: Given an operator question about a SPOT robot inspection, retrieve relevant "
                        "inspection events, anomaly notes, operator notes, and Spot manual passages\nQuery:")


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def _unescape(s: str) -> str:
    # `docker --env-file` keeps quotes literally, and .env files carry "\n" literally; the contract wants a real newline.
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
    return s.replace("\\n", "\n")


@dataclass(frozen=True)
class Settings:
    database_url: Optional[str]
    logs_database_url: Optional[str]
    embed_url: str
    embed_model: str
    embed_dim: int
    embed_query_prefix: str
    embed_timeout_s: float
    min_similarity: float
    packet_token_budget: int
    statement_timeout_ms: int
    pool_max: int
    log_calls: bool
    # Graph RAG (contract §7)
    graph_token_budget: int = 300            # the packet's `graph` section
    graph_min_similarity: Optional[float] = None   # vector entry nodes; None -> min_similarity
    graph_text_min_score: float = 0.5        # name/id entry nodes (exact = 1.0; junk trigram hits ~0.3)

    @classmethod
    def from_env(cls) -> "Settings":
        db = _env("DATABASE_URL")
        prefix = os.environ.get("EMBED_QUERY_PREFIX")
        return cls(
            database_url=db,
            logs_database_url=_env("LOGS_DATABASE_URL", db),
            embed_url=(_env("EMBED_URL", "http://localhost:8081") or "").rstrip("/"),
            embed_model=_env("EMBED_MODEL", "Qwen/Qwen3-Embedding-0.6B") or "",
            embed_dim=int(_env("EMBED_DIM", "1024") or 1024),
            # Unset -> the Qwen3 instruction; set-but-empty -> no prefix (other models).
            embed_query_prefix=_unescape(prefix) if prefix is not None else DEFAULT_QUERY_PREFIX,
            embed_timeout_s=float(_env("EMBED_TIMEOUT_S", "10") or 10),
            min_similarity=float(_env("MCP_MIN_SIMILARITY", "0.40") or 0.40),
            packet_token_budget=int(_env("MCP_PACKET_TOKEN_BUDGET", "1500") or 1500),
            statement_timeout_ms=int(_env("MCP_STATEMENT_TIMEOUT_MS", "5000") or 5000),
            pool_max=int(_env("MCP_POOL_MAX", "4") or 4),
            log_calls=(_env("MCP_LOG_CALLS", "1") or "1") not in ("0", "false", "no"),
            graph_token_budget=int(_env("MCP_GRAPH_TOKEN_BUDGET", "300") or 300),
            graph_min_similarity=float(g) if (g := _env("MCP_GRAPH_MIN_SIMILARITY")) else None,
            graph_text_min_score=float(_env("MCP_GRAPH_TEXT_MIN_SCORE", "0.5") or 0.5),
        )
