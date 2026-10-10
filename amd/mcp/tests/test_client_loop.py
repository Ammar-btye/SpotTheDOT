"""The client adapter: MCP tools -> OpenAI tools JSON, and the model -> MCP -> model loop with a scripted fake LLM."""
from __future__ import annotations

import json

import pytest
from mcp import Client

import client_example as ce
from spot_mcp.server import build_server
from spot_mcp.service import ContextService

from fakes import FakeEmbedder, FakeRepo, FakeSink, settings

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def server(sink=None):
    return build_server(ContextService(FakeRepo(), FakeEmbedder(), settings(), sink or FakeSink()))


async def test_openai_tools_conversion():
    async with Client(server()) as c:
        tools = ce.mcp_tools_to_openai((await c.list_tools()).tools)
    by = {t["function"]["name"]: t["function"] for t in tools}
    assert len(by) == 15 and "get_flag_context" in by
    p = by["get_reliability_stats"]["parameters"]
    assert "title" not in json.dumps(p)
    assert p["properties"]["group_by"]["enum"] == ["action_type", "location_id", "configuration_version", "battery_band"]
    assert "anyOf" not in json.dumps(p)                     # Optional[X] flattened for llama.cpp grammars
    assert by["search_spot_manual"]["parameters"]["required"] == ["query"]


async def test_tool_loop_with_fake_llm():
    sink = FakeSink()
    seen = []

    async def llm(payload):
        seen.append(json.loads(json.dumps(payload)))  # snapshot: the loop mutates messages
        if len(seen) == 1:
            return {"choices": [{"message": {"content": None, "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {"name": "get_flag_context", "arguments": json.dumps({"flag_id": 1})}}]}}]}
        if len(seen) == 2:
            return {"choices": [{"message": {"content": "done"}}]}
        enum = payload["response_format"]["json_schema"]["schema"]["properties"]["evidence"]["items"]["properties"]["ids"]["items"]["enum"]
        assert "reading:R0002" in enum and "F2" in enum
        return {"choices": [{"message": {"content": json.dumps({
            "evidence": [{"claim": "Pressure 146.8 psi is above the 140 psi safe band", "ids": ["reading:R0002", "F2"]}],
            "answer": "HX-204 pressure is above its safe band.", "reasoning": "Trusted GOOD reading.",
            "recommended_action": "DISPATCH_TECHNICIAN", "confidence": "high", "insufficient_context": False,
            "question": "What is wrong?"})}}]}

    async with Client(server(sink)) as c:
        out = await ce.run_agent(c, llm, 1, request_id="req-x", verbose=False)
    assert out["post_check_problems"] == []
    assert out["explanation"]["recommended_action"] == "DISPATCH_TECHNICIAN"
    assert seen[1]["messages"][-1]["role"] == "tool" and "flag:1" in seen[1]["messages"][-1]["content"]
    assert "tools" not in seen[2]                            # final turn is grammar-only
    assert sink.tools[0]["request_id"] == "req-x"


def test_post_check_catches_bad_output():
    probs = ce.post_check({"evidence": [{"claim": "x", "ids": ["reading:FAKE"]}], "answer": "pressure 999 psi",
                           "recommended_action": "SELF_DESTRUCT"}, ["reading:R0002"], ["MONITOR"], "146.8")
    assert any("unknown id" in p for p in probs) and any("not allowed" in p for p in probs)
    assert any("999" in p for p in probs)
