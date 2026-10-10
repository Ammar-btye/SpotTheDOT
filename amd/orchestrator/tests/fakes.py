"""Offline fakes: one in-process "world" that answers MCP (JSON-RPC), the LiteLLM gateway (system1 + system2 chat),
the vision service and System 2, behind httpx / httpx2 MockTransports. Every call is recorded in `world.calls`."""
from __future__ import annotations

import asyncio
import base64
import copy
import json
from typing import Any, Callable, Dict, List, Optional

import httpx
import httpx2

# A 1x1 JPEG (valid signature, decodable base64).
TINY_JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 60 + b"\xff\xd9").decode("ascii")

ESCALATED_PACKET: Dict[str, Any] = {
    "packet_version": "1",
    "flag": {"id": "flag:42", "title": "Bearing temperature above safe band", "severity": "HIGH", "status": "OPEN",
             "escalated": True, "priority": "P2", "category": "equipment", "mission_id": "M014",
             "action_id": "A0136", "asset_id": "PUMP-101", "location_id": "WP07",
             "reasons": [{"rule": "laya_verdict", "detail": "Laya: escalate (0.83)"},
                         {"rule": "rules_verdict", "detail": "Laya: escalate (0.83) · rules: confirmed"},
                         {"rule": "reading_above_safe_band", "detail": "TEMPERATURE_C 83.5 above 80"}]},
    "event": {"id": "action:A0136", "mission_id": "M014", "sequence": 6, "timestamp": "2026-09-06T02:15:36",
              "action_type": "THERMAL_INSPECTION", "status": "SUCCESS", "battery_pct": 62.0, "battery_status": "OK",
              "duration_sec": 41, "configuration_version": "V2",
              "asset": {"id": "asset:PUMP-101", "name": "Pump 101", "type": "PUMP", "criticality": "HIGH"},
              "location": {"id": "location:WP07", "name": "Pump Bay", "zone": "MECH", "environment": "NORMAL"},
              "readings": [{"id": "reading:R0042", "measurement_type": "TEMPERATURE_C", "value": 83.5, "unit": "C",
                            "quality": "GOOD", "safe_band": [None, 80], "trust": "trusted",
                            "assessment": "above safe band"}],
              "anomalies": [{"id": "anomaly:N7", "anomaly_type": "OVERHEATING", "severity": "HIGH",
                             "description": "Bearing hot"}],
              "validator": {"escalate": "A", "priority": "P2", "category": "equipment", "reading_trust": "A",
                            "suggested_action": "SCHEDULE_MAINTENANCE", "policy": "policy.py"}},
    "system1": [{"id": "s1:9", "when": "action", "q": "escalate", "answer": "A",
                 "meaning": "yes, escalate: it needs operator attention", "p": 0.83},
                {"id": "s1:10", "when": "action", "q": "priority", "answer": "P2", "p": 0.7}],
    "facts": [{"id": "F1", "fact": "Validator (policy.py): priority P2, category equipment, escalate=yes."},
              {"id": "F2", "fact": "Reading TEMPERATURE_C 83.5 C (quality GOOD) vs safe band -inf..80: above."}],
    "manual": [{"id": "manual:12", "kind": "manual", "sim": 0.61, "title": "Thermal inspections",
                "text": "Thermal payload readings above the configured band should be re-checked."}],
    "allowed_actions": {"DISPATCH_TECHNICIAN": "send a technician", "SCHEDULE_MAINTENANCE": "work order",
                        "REINSPECT_NEXT_ROUTE": "re-check next route", "ESCALATE_TO_SUPERVISOR": "notify"},
    "suggested_action": "SCHEDULE_MAINTENANCE",
    "insufficient_context": False,
    "citation_ids": ["flag:42", "action:A0136", "reading:R0042", "F1", "F2", "s1:9", "manual:12"],
    "question": "Flag 42 \"Bearing temperature above safe band\": what is wrong with Pump 101 (PUMP-101)?",
}


def routine_packet() -> Dict[str, Any]:
    p = copy.deepcopy(ESCALATED_PACKET)
    p["flag"].update(escalated=False, priority="P4", severity="LOW", title="Routine thermal check")
    p["flag"]["reasons"] = [{"rule": "laya_verdict", "detail": "Laya: log only (0.91)"},
                            {"rule": "rules_verdict", "detail": "Laya: routine · rules: both_routine"}]
    p["event"]["validator"].update(escalate="B", priority="P4", suggested_action="REINSPECT_NEXT_ROUTE")
    p["system1"] = [{"id": "s1:9", "when": "action", "q": "escalate", "answer": "B", "p": 0.91},
                    {"id": "s1:10", "when": "action", "q": "priority", "answer": "P4", "p": 0.8}]
    p["suggested_action"] = "REINSPECT_NEXT_ROUTE"
    return p


def no_s1_packet() -> Dict[str, Any]:
    p = routine_packet()
    del p["system1"]
    return p


MCP_TOOLS = [
    {"name": "get_flag_context", "description": "START HERE.", "annotations": {"readOnlyHint": True},
     "inputSchema": {"type": "object", "properties": {"flag_id": {"type": "integer"}}, "required": ["flag_id"]}},
    {"name": "search_spot_manual", "description": "Spot manual passages.", "annotations": {"readOnlyHint": True},
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer"}},
                     "required": ["query"]}},
    {"name": "search_policy", "description": "Policy rules.", "annotations": {"readOnlyHint": True},
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "search_similar_incidents", "description": "Past incidents.", "annotations": {"readOnlyHint": True},
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}},
    {"name": "list_allowed_actions", "description": "Actions.", "annotations": {"readOnlyHint": True},
     "inputSchema": {"type": "object", "properties": {"category": {"type": "string"}}}},
    {"name": "delete_everything", "description": "not read-only", "annotations": {"readOnlyHint": False},
     "inputSchema": {"type": "object", "properties": {}}},
]


def search_result(prefix: str, query: str) -> Dict[str, Any]:
    return {"query": query, "results": [{"id": "%s:1" % prefix, "kind": prefix, "sim": 0.7, "title": "%s one" % prefix,
                                         "text": "Text about %s." % query}], "result_count": 1}


VISION_THERMAL = {
    "media_id": "thermal_pump_bearing_01", "kind": "thermal",
    "router": {"label": "thermal", "method": "action_type", "confidence": 1.0},
    "ocr": [{"text": "100", "bbox": [1, 2, 3, 4], "conf": 0.99}, {"text": "20", "bbox": [1, 2, 3, 4], "conf": 0.95},
            {"text": "noise", "bbox": [1, 2, 3, 4], "conf": 0.2}],
    "readings": [{"id": "V1", "quantity": "max_temperature", "value": 99.8, "unit": "°C", "confidence": 0.8,
                  "method": "colorbar_lut", "flags": ["CLIPPED"]},
                 {"id": "V2", "quantity": "delta_t", "value": 58.0, "unit": "°C", "confidence": 0.3,
                  "method": "colorbar_lut", "flags": []}],
    "key_results": [{"name": "Max Temperature", "units": "°C", "value": 99.8}],
    "comparison": {"logged_id": "R0042", "logged_value": 83.5, "logged_unit": "°C", "vision_id": "V1",
                   "vision_value": 99.8, "delta": 16.3, "tolerance": 4.0, "agrees": False, "flags": []},
    "alert": {"title": "Thermal hotspot 99.8 °C", "severity": 4, "source": "vision.thermal"},
    "flags": [], "annotated_image_b64": TINY_JPEG, "annotated_mime": "image/jpeg", "latency_ms": 41,
    "version": {"service": "0.1.0", "contract": "2026-10-10.vision.1"},
}

SYSTEM2_OK = {"evidence": [{"claim": "Bearing reading 83.5 C is above the safe band.", "ids": ["F2"]},
                           {"claim": "Vision reads 99.8 C at the hotspot.", "ids": ["V1"]}],
              "answer": "Yes. The bearing is running hot; schedule maintenance.", "question": "Flag 42 ...",
              "recommended_action": "SCHEDULE_MAINTENANCE", "confidence": "high", "insufficient_context": False,
              "flag_id": 42, "model": "qwen3.5-9b", "latency_ms": 7900, "tokens_per_sec": 35.6, "path": "llm"}


def chat_reply(content: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None,
               model: str = "qwen3.5-9b") -> Dict[str, Any]:
    msg: Dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = [{"id": "call_%d" % i, "type": "function",
                              "function": {"name": tc["name"], "arguments": json.dumps(tc.get("args") or {})}}
                             for i, tc in enumerate(tool_calls)]
    return {"id": "chatcmpl-1", "object": "chat.completion", "created": 0, "model": model,
            "choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls" if tool_calls else "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


class World:
    """Configurable fake dependencies. Set attributes, then pass `world.http()` / `world.http2()` to the app."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.packet: Optional[Dict[str, Any]] = copy.deepcopy(ESCALATED_PACKET)
        self.mcp_down = False
        self.mcp_delay = 0.0
        self.system1_reply: Any = {"model": "laya-ft", "fine_tuned": True, "items": [
            {"id": "x", "kind": "action", "answers": {
                "escalate": {"answer": "B", "probs": {"A": 0.1, "B": 0.9}, "confidence": 0.9},
                "priority": {"answer": "P4", "probs": {"P4": 0.8}, "confidence": 0.8}}}]}
        self.system1_status = 200
        self.vision_reply: Any = copy.deepcopy(VISION_THERMAL)
        self.vision_status = 200
        self.vision_delay = 0.0
        self.system2_reply: Any = copy.deepcopy(SYSTEM2_OK)
        self.system2_status = 200
        self.system2_delay = 0.0
        self.system2_handler: Optional[Callable[[Dict[str, Any]], Any]] = None   # e.g. the real System 2 app
        self.chat: Callable[[Dict[str, Any]], Any] = lambda body: (200, chat_reply("Plain answer [manual:1]."))

    def of(self, kind: str) -> List[Dict[str, Any]]:
        return [c for c in self.calls if c["kind"] == kind]

    # ── dispatch ──
    async def handle(self, method: str, url: str, headers: Dict[str, str], body: Any):
        path = url.split("://", 1)[-1].split("/", 1)[-1]
        path = "/" + path.split("?")[0]
        host = url.split("://", 1)[-1].split("/")[0]
        if host.startswith("mcp"):
            return await self._mcp(method, path, headers, body)
        if host.startswith("gateway"):
            return await self._gateway(path, headers, body)
        if host.startswith("vision"):
            self.calls.append({"kind": "vision", "path": path, "body": body, "headers": headers})
            if path == "/health":
                return 200, {"status": "ok"}, {}
            if self.vision_delay:
                await asyncio.sleep(self.vision_delay)
            return self.vision_status, self.vision_reply, {}
        if host.startswith("system2"):
            if path == "/health":
                return 200, {"status": "ok"}, {}
            self.calls.append({"kind": "system2", "path": path, "body": body, "headers": headers})
            if self.system2_delay:
                await asyncio.sleep(self.system2_delay)
            if self.system2_handler:
                return await self.system2_handler(body, headers)
            return self.system2_status, self.system2_reply, {}
        return 404, {"error": "unknown host %s" % host}, {}

    async def _mcp(self, method, path, headers, body):
        if path == "/healthz":
            return 200, {"ok": True}, {}
        if self.mcp_down:
            raise httpx.ConnectError("connection refused")
        if method == "DELETE":
            return 200, {}, {}
        m = body.get("method")
        if m == "initialize":
            return 200, {"jsonrpc": "2.0", "id": body["id"], "result": {"protocolVersion": "2025-06-18"}}, \
                {"mcp-session-id": "s-1"}
        if m == "notifications/initialized":
            return 202, {}, {}
        if m == "tools/list":
            return 200, {"jsonrpc": "2.0", "id": body["id"], "result": {"tools": MCP_TOOLS}}, {}
        if m == "tools/call":
            name, args = body["params"]["name"], body["params"]["arguments"]
            self.calls.append({"kind": "mcp", "tool": name, "args": args, "headers": headers})
            if self.mcp_delay:
                await asyncio.sleep(self.mcp_delay)
            if name == "get_flag_context":
                if self.packet is None:
                    res = {"isError": True, "content": [{"type": "text", "text": "no flag"}]}
                else:
                    res = {"structuredContent": copy.deepcopy(self.packet), "content": []}
            elif name.startswith("search_"):
                prefix = {"search_spot_manual": "manual", "search_policy": "policy"}.get(name, "incident")
                res = {"structuredContent": search_result(prefix, args.get("query") or args.get("text") or "")}
            else:
                res = {"structuredContent": {"result_count": 0}}
            return 200, {"jsonrpc": "2.0", "id": body["id"], "result": res}, {}
        return 400, {"error": "bad method"}, {}

    async def _gateway(self, path, headers, body):
        if path.startswith("/health"):
            return 200, {"status": "ok"}, {}
        model = body.get("model")
        self.calls.append({"kind": "gateway:%s" % model, "body": body, "headers": headers})
        if model == "system1":
            if self.system1_status != 200:
                return self.system1_status, {"error": "system1 down"}, {}
            return 200, chat_reply(json.dumps(self.system1_reply), model="system1"), {}
        res = self.chat(body)
        if asyncio.iscoroutine(res):
            res = await res
        status, reply = res
        return status, reply, {}

    # ── transports ──
    def http(self) -> httpx.AsyncClient:
        async def h(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content) if request.content else None
            status, data, hdrs = await self.handle(request.method, str(request.url), dict(request.headers), body)
            return httpx.Response(status, json=data, headers=hdrs)
        return httpx.AsyncClient(transport=httpx.MockTransport(h))

    def http2(self) -> "httpx2.AsyncClient":
        async def h(request):
            body = json.loads(request.content) if request.content else None
            status, data, hdrs = await self.handle(request.method, str(request.url), dict(request.headers), body)
            return httpx2.Response(status, json=data, headers=hdrs)
        return httpx2.AsyncClient(transport=httpx2.MockTransport(h))


def settings_env(**over) -> Dict[str, str]:
    env = {"ORCHESTRATOR_API_KEY": "test-key-0123456789", "MCP_URL": "http://mcp:8090/mcp",
           "GATEWAY_URL": "http://gateway:4000", "GATEWAY_KEY": "sk-test", "VISION_URL": "http://vision:8084",
           "SYSTEM2_URL": "http://system2:8083", "SYSTEM2_API_KEY": "s2-key-0123456789", "ORCH_DEADLINE_S": "10"}
    env.update({k: str(v) for k, v in over.items()})
    return env
