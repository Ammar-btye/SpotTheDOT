"""HTTP clients for the orchestrator's dependencies: MCP (JSON-RPC over streamable HTTP), the LiteLLM gateway
(System 1 alias), the vision service and System 2.

Every failure becomes ServiceUnavailable(service, reason), so graph nodes can tolerate it in one `except`. Timeouts
are set per call by the caller (the node's remaining budget); clients never retry. The MCP client mirrors
backend/app/services/mcp.py (httpx only, plain JSON or SSE replies) and adds tools/list and a reusable session for
the /v1/ask loop.
"""
from __future__ import annotations

import fnmatch
import itertools
import json
import time
from typing import Any, Dict, List, Optional, Sequence

import httpx

PROTOCOL_VERSION = "2025-06-18"
_ids = itertools.count(1)


class ServiceUnavailable(RuntimeError):
    def __init__(self, service: str, reason: str):
        super().__init__("%s unavailable: %s" % (service, reason))
        self.service = service
        self.reason = reason


def short_error(exc: BaseException) -> str:
    name = type(exc).__name__
    msg = str(exc).strip()
    return ("%s: %s" % (name, msg))[:300] if msg else name


def _headers(request_id: Optional[str], extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    h = {"X-Request-ID": request_id or ""}
    h.update(extra or {})
    return h


# ── MCP ──────────────────────────────────────────────────────────────────────────────────────────
def _parse_rpc(r: httpx.Response, want_id: int) -> Dict[str, Any]:
    if "text/event-stream" in r.headers.get("content-type", ""):
        for line in r.text.splitlines():
            if line.startswith("data:"):
                try:
                    msg = json.loads(line[5:].strip())
                except ValueError:
                    continue
                if isinstance(msg, dict) and msg.get("id") == want_id:
                    return msg
        raise ServiceUnavailable("mcp", "no JSON-RPC response for id %d in SSE stream" % want_id)
    out = r.json()
    if not isinstance(out, dict):
        raise ServiceUnavailable("mcp", "JSON-RPC reply is not an object")
    return out


def tool_data(result: Dict[str, Any], tool: str) -> Dict[str, Any]:
    """A tools/call result -> its structured dict (structuredContent, else the JSON text content)."""
    if result.get("isError"):
        texts = [c.get("text", "") for c in result.get("content") or [] if isinstance(c, dict)]
        raise ServiceUnavailable("mcp", "tool %s failed: %s" % (tool, " ".join(texts)[:300]))
    data = result.get("structuredContent")
    if isinstance(data, dict) and set(data) == {"result"} and isinstance(data["result"], (dict, list)):
        data = data["result"]
    if data is None:
        for c in result.get("content") or []:
            if isinstance(c, dict) and c.get("type") == "text":
                try:
                    data = json.loads(c["text"])
                except ValueError:
                    data = {"text": c["text"]}
                break
    return data if isinstance(data, dict) else {"result": data}


class MCPSession:
    """One initialized MCP session (initialize -> notifications/initialized), reused for several calls."""

    def __init__(self, client: "MCPClient", request_id: Optional[str]):
        self.c = client
        self.request_id = request_id
        self.session: Optional[str] = None

    async def _rpc(self, method: str, params: Dict[str, Any], timeout: float, notify: bool = False):
        headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json",
                   "X-Request-ID": self.request_id or ""}
        if self.c.auth_token:
            headers["Authorization"] = "Bearer " + self.c.auth_token
        if self.session:
            headers["Mcp-Session-Id"] = self.session
            headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
        msg: Dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params}
        rid = None
        if not notify:
            rid = next(_ids)
            msg["id"] = rid
        try:
            r = await self.c.http.post(self.c.url, json=msg, headers=headers, timeout=timeout)
        except httpx.HTTPError as exc:
            raise ServiceUnavailable("mcp", short_error(exc)) from exc
        if r.status_code >= 400:
            raise ServiceUnavailable("mcp", "%s -> HTTP %d: %s" % (method, r.status_code, r.text[:200]))
        self.session = r.headers.get("mcp-session-id") or self.session
        if notify:
            return None
        try:
            body = _parse_rpc(r, rid)  # type: ignore[arg-type]
        except ValueError as exc:
            raise ServiceUnavailable("mcp", "bad JSON-RPC reply: %s" % short_error(exc)) from exc
        if "error" in body:
            raise ServiceUnavailable("mcp", "%s error: %s" % (method, body["error"]))
        return body.get("result") or {}

    async def __aenter__(self) -> "MCPSession":
        if not self.c.url:
            raise ServiceUnavailable("mcp", "MCP_URL is not set")
        await self._rpc("initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                                       "clientInfo": {"name": "spot-orchestrator", "version": "1.0"}},
                        self.c.timeout_s)
        await self._rpc("notifications/initialized", {}, self.c.timeout_s, notify=True)
        return self

    async def __aexit__(self, *exc) -> None:
        if self.session:
            try:
                await self.c.http.delete(self.c.url, headers={"Mcp-Session-Id": self.session}, timeout=2.0)
            except httpx.HTTPError:
                pass

    async def list_tools(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        cursor = None
        for _ in range(5):  # pagination guard
            res = await self._rpc("tools/list", {"cursor": cursor} if cursor else {}, self.c.timeout_s)
            out.extend(t for t in res.get("tools") or [] if isinstance(t, dict))
            cursor = res.get("nextCursor")
            if not cursor:
                break
        return out

    async def call_tool(self, tool: str, arguments: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]:
        t0 = time.perf_counter()
        result = await self._rpc("tools/call", {"name": tool, "arguments": arguments,
                                                "_meta": {"request_id": self.request_id}},
                                 timeout or self.c.timeout_s)
        data = tool_data(result or {}, tool)
        data.setdefault("_latency_ms", int((time.perf_counter() - t0) * 1000))
        return data


class MCPClient:
    name = "mcp"

    def __init__(self, url: Optional[str], http: httpx.AsyncClient, auth_token: Optional[str] = None,
                 timeout_s: float = 15.0):
        self.url = url
        self.http = http
        self.auth_token = auth_token
        self.timeout_s = timeout_s

    def session(self, request_id: Optional[str]) -> MCPSession:
        return MCPSession(self, request_id)

    async def call_tool(self, tool: str, arguments: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
        async with self.session(request_id) as s:
            return await s.call_tool(tool, arguments)

    async def health(self) -> dict:
        if not self.url:
            return {"status": "unset"}
        try:
            r = await self.http.get(str(httpx.URL(self.url).copy_with(path="/healthz", query=None)), timeout=2.0)
            return {"status": "up" if r.status_code == 200 else "degraded", "http": r.status_code}
        except httpx.HTTPError as exc:
            return {"status": "down", "error": short_error(exc)}


def allowed_tool(tool: Dict[str, Any], patterns: Sequence[str]) -> bool:
    """Allowlisted by name pattern and never a tool that declares itself non-read-only."""
    ann = tool.get("annotations") or {}
    if ann.get("readOnlyHint") is False or ann.get("destructiveHint") is True:
        return False
    return any(fnmatch.fnmatchcase(str(tool.get("name") or ""), p) for p in patterns)


def openai_tool(tool: Dict[str, Any]) -> Dict[str, Any]:
    """An MCP tool listing -> the OpenAI function-tool dict that ChatOpenAI.bind_tools accepts."""
    schema = dict(tool.get("inputSchema") or {"type": "object", "properties": {}})
    schema.setdefault("type", "object")
    schema.setdefault("properties", {})
    return {"type": "function", "function": {"name": tool["name"],
                                             "description": (tool.get("description") or "")[:1000],
                                             "parameters": schema}}


# ── simple JSON services ─────────────────────────────────────────────────────────────────────────
class _JsonService:
    name = "service"

    def __init__(self, base_url: Optional[str], http: httpx.AsyncClient, headers: Optional[Dict[str, str]] = None,
                 health_path: str = "/health"):
        self.base_url = base_url
        self.http = http
        self.auth_headers = headers or {}
        self.health_path = health_path

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    async def _post(self, path: str, body: Dict[str, Any], request_id: Optional[str], timeout: float) -> Dict[str, Any]:
        if not self.base_url:
            raise ServiceUnavailable(self.name, "%s_URL is not set" % self.name.upper())
        try:
            r = await self.http.post(self.base_url + path, json=body, headers=_headers(request_id, self.auth_headers),
                                     timeout=timeout)
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(self.name, short_error(exc)) from exc
        if r.status_code != 200:
            raise ServiceUnavailable(self.name, "HTTP %d: %s" % (r.status_code, r.text[:200]))
        try:
            out = r.json()
        except ValueError as exc:
            raise ServiceUnavailable(self.name, "response is not JSON") from exc
        if not isinstance(out, dict):
            raise ServiceUnavailable(self.name, "response is not a JSON object")
        return out

    async def health(self) -> dict:
        if not self.base_url:
            return {"status": "unset"}
        try:
            r = await self.http.get(self.base_url + self.health_path, headers=self.auth_headers, timeout=2.0)
            return {"status": "up" if r.status_code == 200 else "degraded", "http": r.status_code}
        except httpx.HTTPError as exc:
            return {"status": "down", "error": short_error(exc)}


class GatewayClient(_JsonService):
    """LiteLLM gateway. Only the `system1` alias is called here (plain HTTP); /v1/ask uses ChatOpenAI."""
    name = "gateway"

    def __init__(self, base_url: Optional[str], http: httpx.AsyncClient, key: Optional[str], system1_alias: str):
        super().__init__(base_url, http, {"Authorization": "Bearer " + key} if key else {},
                         health_path="/health/liveliness")
        self.system1_alias = system1_alias

    async def system1_predict(self, kind: str, event: Dict[str, Any], request_id: Optional[str],
                              timeout: float) -> Dict[str, Any]:
        """Laya answers via the gateway alias. Returns {"model", "answers": {q: {answer, probs, confidence}}}."""
        body = {"model": self.system1_alias, "temperature": 0,
                "messages": [{"role": "user", "content": json.dumps({"kind": kind, "event": event},
                                                                     separators=(",", ":"), default=str)}]}
        out = await self._post("/v1/chat/completions", body, request_id, timeout)
        try:
            content = out["choices"][0]["message"]["content"]
            pred = json.loads(content) if isinstance(content, str) else content
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ServiceUnavailable(self.name, "system1 reply is not /v1/predict JSON (%s)" % short_error(exc)) from exc
        if not isinstance(pred, dict):
            raise ServiceUnavailable(self.name, "system1 reply is not an object")
        answers = pred.get("answers")
        if answers is None and isinstance(pred.get("items"), list) and pred["items"]:
            answers = (pred["items"][0] or {}).get("answers")
        if not isinstance(answers, dict) or not answers:
            raise ServiceUnavailable(self.name, "system1 reply has no answers")
        return {"model": pred.get("model") or out.get("model"), "answers": answers}


class VisionClient(_JsonService):
    name = "vision"

    def __init__(self, base_url: Optional[str], http: httpx.AsyncClient, api_key: Optional[str] = None):
        super().__init__(base_url, http, {"X-API-Key": api_key} if api_key else {})

    async def analyze(self, body: Dict[str, Any], request_id: Optional[str], timeout: float) -> Dict[str, Any]:
        return await self._post("/v1/vision", body, request_id, timeout)


class System2Client(_JsonService):
    name = "system2"

    def __init__(self, base_url: Optional[str], http: httpx.AsyncClient, api_key: Optional[str] = None):
        super().__init__(base_url, http, {"X-API-Key": api_key} if api_key else {})

    async def assess(self, body: Dict[str, Any], request_id: Optional[str], timeout: float) -> Dict[str, Any]:
        payload = json.loads(json.dumps(body, default=str))  # dates/decimals -> strings, like the backend
        return await self._post("/v1/assess", payload, request_id, timeout)
