"""The service container (built once per app) and the FastAPI dependency that hands it to routers."""
from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import Request

from .config import Settings
from .db.pool import Database
from .db.queries import Repo
from .services.calllog import LogSink, request_id_var
from .services.embed import EmbedClient
from .services.flags import FlagService
from .services.http import Breaker
from .services.ingest import IngestPipeline
from .services.mcp import MCPClient
from .services.reference import Reference
from .services.replay import ReplayManager
from .services.system1 import System1Client
from .services.system2 import System2Client


@dataclass
class Services:
    settings: Settings
    db: Database
    logs_db: Database
    repo: Repo
    sink: LogSink
    http: httpx.AsyncClient
    ref: Reference
    system1: System1Client
    embed: EmbedClient
    mcp: MCPClient
    system2: System2Client
    pipeline: IngestPipeline
    replay: ReplayManager
    flags: FlagService

    async def open(self) -> None:
        await self.db.open()
        if self.logs_db is not self.db:
            await self.logs_db.open()

    async def close(self) -> None:
        await self.replay.stop()
        await self.sink.drain()
        await self.http.aclose()
        if self.logs_db is not self.db:
            await self.logs_db.close()
        await self.db.close()


def build_services(settings: Settings, *, repo: Optional[Repo] = None,
                   transport: Optional[httpx.AsyncBaseTransport] = None) -> Services:
    db = Database(settings.database_url, name="main", pool_max=settings.db_pool_max,
                  connect_timeout_s=settings.db_connect_timeout_s)
    logs_db = db if settings.logs_database_url in (None, settings.database_url) else Database(
        settings.logs_database_url, name="logs", pool_max=max(2, settings.db_pool_max // 2),
        connect_timeout_s=settings.db_connect_timeout_s)
    repo = repo or Repo(db, logs_db)
    sink = LogSink(logs_db)
    http = httpx.AsyncClient(transport=transport, timeout=10.0,
                             limits=httpx.Limits(max_connections=50, max_keepalive_connections=20))
    cd = settings.breaker_cooldown_s
    ref = Reference(settings.kit_dir)
    # Audit H1: a breaker that reopens before a hung call could time out stalls the replay once per cooldown,
    # so each breaker's cooldown is at least that client's timeout.
    system1 = System1Client(settings.system1_url, http, sink, settings.system1_timeout_s,
                            Breaker(max(cd, settings.system1_timeout_s)),
                            ingest_timeout_s=settings.system1_ingest_timeout_s)
    embed = EmbedClient(settings.embed_url, settings.embed_model, settings.embed_dim, settings.embed_query_prefix,
                        settings.embed_doc_prefix, http, sink, settings.embed_timeout_s,
                        Breaker(max(cd, settings.embed_timeout_s)))
    mcp = MCPClient(settings.mcp_url, http, settings.mcp_timeout_s, Breaker(max(cd, settings.mcp_timeout_s)),
                    settings.mcp_auth_token)
    system2 = System2Client(settings.system2_url, http, sink, settings.system2_api_key, settings.system2_timeout_s,
                            Breaker(max(cd, settings.system2_timeout_s)))
    pipeline = IngestPipeline(repo, ref, system1, sink, settings.triage_mode)
    replay = ReplayManager(pipeline, sink, ref.replay_path, settings.replay_speed, settings.replay_max_gap_s)
    flags = FlagService(repo, mcp, system2, embed, sink, deadline_s=settings.request_deadline_s)
    return Services(settings, db, logs_db, repo, sink, http, ref, system1, embed, mcp, system2, pipeline, replay,
                    flags)


def get_services(request: Request) -> Services:
    return request.app.state.svc


class AdminAuthError(Exception):
    """Raised by `require_admin`; main.py turns it into {"error", "detail", "request_id"} with `status`."""

    def __init__(self, status: int, code: str, detail: str):
        super().__init__(detail)
        self.status, self.code, self.detail = status, code, detail


def require_admin(request: Request) -> None:
    """Audit H3: /ops/*, /replay/* and POST /events* need `X-Admin-Token: <ADMIN_TOKEN>`. With ADMIN_TOKEN unset
    they are closed (503), never open; there is no bypass."""
    expected = request.app.state.svc.settings.admin_token
    if not expected:
        raise AdminAuthError(503, "admin_token_unset",
                             "ADMIN_TOKEN is not configured on the backend, so admin endpoints are disabled")
    got = request.headers.get("x-admin-token") or ""
    if not hmac.compare_digest(got.encode(), expected.encode()):
        raise AdminAuthError(401, "unauthorized", "missing or invalid X-Admin-Token header")


def current_request_id() -> Optional[str]:
    return request_id_var.get()
