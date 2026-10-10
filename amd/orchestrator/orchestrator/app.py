"""FastAPI app: POST /v1/assess, POST /v1/ask, GET /v1/graph, GET /health (docs/orchestrator-contract.md).

create_app(settings, http=..., chat=...) lets tests inject an httpx client (MockTransport fakes) and a chat model;
in production both are built from the environment. Auth is an X-API-Key middleware that runs before parsing, like
System 2; the app refuses to start without a key unless ORCHESTRATOR_ALLOW_NO_AUTH=1.
"""
from __future__ import annotations

import hmac
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from .ask import AskRunner
from .assess import Deps, build_assess_graph, clean_b64, run_assess
from .clients import GatewayClient, MCPClient, System2Client, VisionClient
from .config import CONTRACT_VERSION, MAX_TOOL_CALLS, Settings

log = logging.getLogger("orchestrator")
KEY_HEADER = "X-API-Key"
OPEN_PATHS = frozenset({"/health", "/v1/graph"})
# The vision service's `kind` values (docs/vision-contract.md); anything else is a 422 here, not at the vision service.
ImageKind = Literal["auto", "thermal", "gauge", "acoustic_imager", "spectrogram", "orbit_screenshot", "visual"]


class AssessBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    flag_id: int = Field(ge=1)
    request_id: Optional[str] = Field(default=None, max_length=128)
    image_b64: Optional[str] = None
    image_kind: Optional[ImageKind] = None
    action_type: Optional[str] = Field(default=None, max_length=64)
    refresh: bool = False
    return_image: bool = False
    context: Optional[dict] = None


class AskBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    question: str = Field(min_length=2, max_length=2000)
    flag_id: Optional[int] = Field(default=None, ge=1)
    max_steps: Optional[int] = Field(default=None, ge=1, le=MAX_TOOL_CALLS)
    request_id: Optional[str] = Field(default=None, max_length=128)


def build_chat(s: Settings, http_async_client: Any = None):
    """ChatOpenAI pointed at the LiteLLM gateway (alias ASK_MODEL); None when GATEWAY_URL is unset."""
    if not s.gateway_url:
        return None
    from langchain_openai import ChatOpenAI
    kw = {"http_async_client": http_async_client} if http_async_client is not None else {}
    return ChatOpenAI(model=s.ask_model, base_url=s.gateway_url + "/v1", api_key=s.gateway_key or "no-key",
                      temperature=0.2, max_tokens=600, timeout=s.ask_deadline_s, max_retries=0, **kw)


def create_app(settings: Optional[Settings] = None, http: Optional[httpx.AsyncClient] = None,
               chat: Any = "env") -> FastAPI:
    s = settings or Settings.from_env()
    s.check_auth()
    expected = s.api_key.encode("ascii") if s.api_key else None
    if expected is None:
        log.warning("ORCHESTRATOR_ALLOW_NO_AUTH=1: every route is open (tests only)")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        own = http is None
        client = http or httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=3.0))
        deps = Deps(settings=s, mcp=MCPClient(s.mcp_url, client, s.mcp_auth_token),
                    gateway=GatewayClient(s.gateway_url, client, s.gateway_key, s.system1_alias),
                    vision=VisionClient(s.vision_url, client, s.vision_api_key),
                    system2=System2Client(s.system2_url, client, s.system2_api_key))
        app.state.deps = deps
        app.state.assess_graph = build_assess_graph(deps)
        app.state.ask = AskRunner(s, deps.mcp, build_chat(s) if chat == "env" else chat)
        try:
            yield
        finally:
            if own:
                await client.aclose()

    app = FastAPI(title="SPOT orchestrator (LangGraph)", version=CONTRACT_VERSION, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def key_first(request: Request, call_next):
        if expected is not None and request.url.path not in OPEN_PATHS:
            given = request.headers.get(KEY_HEADER)
            if given is None or not hmac.compare_digest(given.encode("latin-1"), expected):
                return JSONResponse({"detail": "missing or invalid X-API-Key"}, status_code=401)
        return await call_next(request)

    def _rid(request: Request, given: Optional[str]) -> str:
        return given or request.headers.get("x-request-id") or "o-%s" % uuid.uuid4().hex[:12]

    @app.post("/v1/assess")
    async def assess(body: AssessBody, request: Request) -> dict:
        req = body.model_dump()
        if body.image_b64:
            if len(body.image_b64) > s.max_image_b64:
                raise HTTPException(status_code=413, detail="image_b64 longer than ORCH_MAX_IMAGE_B64=%d"
                                    % s.max_image_b64)
            try:
                req["image_b64"] = clean_b64(body.image_b64)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        req["request_id"] = _rid(request, body.request_id)
        return await run_assess(app.state.assess_graph, app.state.deps, req)

    @app.post("/v1/ask")
    async def ask(body: AskBody, request: Request) -> dict:
        return await app.state.ask.run(body.question, body.flag_id, body.max_steps, _rid(request, body.request_id))

    @app.get("/v1/graph")
    async def graph(format: str = Query("json", pattern="^(json|text)$"),
                    which: str = Query("assess", alias="graph", pattern="^(assess|ask)$")):
        g = {"assess": app.state.assess_graph, "ask": app.state.ask.graph}
        if format == "text":
            return PlainTextResponse(g[which].get_graph().draw_mermaid())
        return {k: v.get_graph().draw_mermaid() for k, v in g.items()}

    @app.get("/health")
    async def health(deep: bool = False) -> dict:
        d: Deps = app.state.deps
        out = {"status": "ok", "auth": expected is not None, "contract_version": CONTRACT_VERSION,
               "config": {"mcp": "set" if s.mcp_url else "unset", "gateway": "set" if s.gateway_url else "unset",
                          "vision": "set" if s.vision_url else "unset",
                          "system2": "set" if s.system2_url else "unset"},
               "demo_images": s.demo_images, "deadline_s": s.deadline_s}
        if deep:
            out["deps"] = {"mcp": await d.mcp.health(), "gateway": await d.gateway.health(),
                           "vision": await d.vision.health(), "system2": await d.system2.health()}
        return out

    return app
