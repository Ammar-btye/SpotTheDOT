"""How the llama.cpp-served System 2 model "uses" MCP: a minimal OpenAI-style tool-call loop.

    model (llama-server /v1/chat/completions) -> tool_calls -> MCP server -> tool result -> model -> ... -> final JSON

The final turn runs without tools and with a JSON schema whose `ids` enum is built from the citation ids the tools
returned (research R3), so the model cannot cite a row that doesn't exist. A small post-check (R4) follows.

Usage (from amd/mcp):
  python client_example.py --list-tools                                   # print OpenAI tools JSON, no LLM needed
  python client_example.py --flag-id 1                                    # MCP over stdio (spawns the server)
  MCP_URL=http://localhost:8090/mcp LLM_URL=http://localhost:8080 python client_example.py --flag-id 1
Env: LLM_URL (llama-server base URL), LLM_MODEL, MCP_URL (unset = stdio), MCP_AUTH_TOKEN.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

HERE = Path(__file__).resolve().parent

SYSTEM_PROMPT = """You explain SPOT robot inspection flags to power-plant operators, in the style of Orbit's AI
inspection: a question, a short answer, and the reasoning. Get context with the tools: call get_flag_context first;
call other tools only if its `gaps` show something is missing. Use only facts from tool results and cite their `id`s.
Never invent numbers or ids. If insufficient_context is true, say what is missing. Keep the answer under 80 words."""

FINAL_INSTRUCTION = """Now reply with the JSON object only: evidence (each claim with the ids that support it),
answer, reasoning, recommended_action (one of the allowed actions), confidence, insufficient_context, question."""

MAX_TOOL_RESULT_CHARS = 9000


# ── MCP tools -> OpenAI `tools` ─────────────────────────────────────────────────────────────────
def _clean_schema(s: Any) -> Any:
    """Simplify JSON Schema for llama.cpp's grammar converter and small models: no titles, Optional[X] -> X."""
    if isinstance(s, list):
        return [_clean_schema(x) for x in s]
    if not isinstance(s, dict):
        return s
    s = {k: v for k, v in s.items() if k != "title"}
    any_of = s.get("anyOf")
    if isinstance(any_of, list):
        non_null = [x for x in any_of if x.get("type") != "null"]
        if len(non_null) == 1 and len(any_of) == 2:
            merged = {**{k: v for k, v in s.items() if k != "anyOf"}, **non_null[0]}
            return _clean_schema(merged)
    return {k: _clean_schema(v) for k, v in s.items()}


def mcp_tools_to_openai(tools) -> List[Dict[str, Any]]:
    out = []
    for t in tools:
        params = _clean_schema(t.input_schema or {"type": "object", "properties": {}})
        params.setdefault("type", "object")
        params.setdefault("properties", {})
        out.append({"type": "function", "function": {"name": t.name, "description": (t.description or "").strip(),
                                                     "parameters": params}})
    return out


def final_schema(ids: List[str], allowed: List[str]) -> Dict[str, Any]:
    id_items = {"type": "string", "enum": ids} if ids else {"type": "string"}
    act = {"type": "string", "enum": allowed} if allowed else {"type": "string"}
    return {"type": "object", "additionalProperties": False,
            "required": ["evidence", "answer", "reasoning", "recommended_action", "confidence",
                         "insufficient_context", "question"],
            "properties": {
                "evidence": {"type": "array", "maxItems": 5, "items": {
                    "type": "object", "additionalProperties": False, "required": ["claim", "ids"],
                    "properties": {"claim": {"type": "string"},
                                   "ids": {"type": "array", "minItems": 1, "maxItems": 4, "items": id_items}}}},
                "answer": {"type": "string"}, "reasoning": {"type": "string"},
                "recommended_action": act, "confidence": {"type": "string", "enum": ["low", "med", "high"]},
                "insufficient_context": {"type": "boolean"}, "question": {"type": "string"}}}


def harvest(result: Any, ids: List[str], allowed: List[str]) -> None:
    """Collect citation ids and allowed actions from any tool result."""
    if isinstance(result, dict):
        if isinstance(result.get("id"), str) and result["id"] not in ids:
            ids.append(result["id"])
        aa = result.get("allowed_actions")
        if isinstance(aa, (dict, list)):
            for a in aa:
                if a not in allowed:
                    allowed.append(a)
        for k, v in result.items():
            if k != "allowed_actions":
                harvest(v, ids, allowed)
    elif isinstance(result, list):
        for v in result:
            harvest(v, ids, allowed)


def post_check(answer: Dict[str, Any], ids: List[str], allowed: List[str], tool_text: str) -> List[str]:
    """R4: ids exist, action allowed, every number in the prose appears in the tool results."""
    problems = []
    for ev in answer.get("evidence", []):
        problems += ["unknown id %s" % i for i in ev.get("ids", []) if i not in ids]
    if allowed and answer.get("recommended_action") not in allowed:
        problems.append("action %r not allowed" % answer.get("recommended_action"))
    prose = " ".join(str(answer.get(k, "")) for k in ("answer", "reasoning")) + " " + \
        " ".join(e.get("claim", "") for e in answer.get("evidence", []))
    for num in set(re.findall(r"\d+(?:\.\d+)?", prose)):
        if num not in tool_text and num.rstrip("0").rstrip(".") not in tool_text:
            problems.append("number %s not in context" % num)
    return problems


# ── the loop ────────────────────────────────────────────────────────────────────────────────────
LLMPost = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]


async def run_agent(mcp_client, llm_post: LLMPost, flag_id: int, model: str = "system2", max_steps: int = 4,
                    request_id: Optional[str] = None, prefetch: bool = False, verbose: bool = True) -> Dict[str, Any]:
    request_id = request_id or "req-" + uuid.uuid4().hex[:12]
    tools = mcp_tools_to_openai((await mcp_client.list_tools()).tools)
    ids: List[str] = []
    allowed: List[str] = []
    tool_texts: List[str] = []
    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT},
                                      {"role": "user", "content": "Explain flag %d for the operator." % flag_id}]

    async def call_mcp(name: str, args: Dict[str, Any]) -> str:
        r = await mcp_client.call_tool(name, args, meta={"request_id": request_id})
        if r.is_error:
            text = "ERROR: " + " ".join(getattr(c, "text", "") for c in r.content)
        else:
            data = r.structured_content
            harvest(data, ids, allowed)
            text = json.dumps(data, separators=(",", ":"), ensure_ascii=False) if data is not None else \
                " ".join(getattr(c, "text", "") for c in r.content)
        tool_texts.append(text)
        if verbose:
            print("  [mcp] %s(%s) -> %d chars%s" % (name, json.dumps(args), len(text),
                                                  " ERROR" if r.is_error else ""), file=sys.stderr)
        return text[:MAX_TOOL_RESULT_CHARS]

    if prefetch:  # skip one LLM round trip: hand the packet over as if the model had asked for it
        text = await call_mcp("get_flag_context", {"flag_id": flag_id})
        messages.append({"role": "assistant", "content": None, "tool_calls": [{
            "id": "call_0", "type": "function",
            "function": {"name": "get_flag_context", "arguments": json.dumps({"flag_id": flag_id})}}]})
        messages.append({"role": "tool", "tool_call_id": "call_0", "content": text})

    for step in range(max_steps):
        resp = await llm_post({"model": model, "messages": messages, "tools": tools, "tool_choice": "auto",
                               "temperature": 0.2, "max_tokens": 400,
                               "chat_template_kwargs": {"enable_thinking": False}})
        msg = resp["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        messages.append({"role": "assistant", "content": msg.get("content"), **({"tool_calls": calls} if calls else {})})
        if not calls:
            break
        for c in calls:
            fn = c["function"]
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = None
            text = await call_mcp(fn["name"], args) if isinstance(args, dict) else "ERROR: arguments were not JSON"
            messages.append({"role": "tool", "tool_call_id": c.get("id", "call_%d" % step), "content": text})

    # Final turn: no tools, grammar-constrained JSON with the ids enum (R3).
    messages.append({"role": "user", "content": FINAL_INSTRUCTION})
    schema = final_schema(ids, allowed)
    resp = await llm_post({"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 450,
                           "chat_template_kwargs": {"enable_thinking": False},
                           "response_format": {"type": "json_schema",
                                               "json_schema": {"name": "explanation", "schema": schema}}})
    raw = resp["choices"][0]["message"].get("content") or "{}"
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError:
        answer = {"answer": raw, "evidence": [], "insufficient_context": True}
    problems = post_check(answer, ids, allowed, " ".join(tool_texts))
    return {"request_id": request_id, "flag_id": flag_id, "explanation": answer, "post_check_problems": problems,
            "citation_ids": ids, "allowed_actions": allowed}


# ── wiring ──────────────────────────────────────────────────────────────────────────────────────
def make_mcp_client(mcp_url: Optional[str]):
    from mcp import Client
    if mcp_url:
        token = os.environ.get("MCP_AUTH_TOKEN")
        if not token:
            return Client(mcp_url)
        import httpx2
        from mcp.client.streamable_http import streamable_http_client
        http = httpx2.AsyncClient(headers={"Authorization": "Bearer " + token}, timeout=60)
        return Client(streamable_http_client(mcp_url, http_client=http))
    from mcp.client.stdio import StdioServerParameters
    return Client(StdioServerParameters(command=sys.executable, args=["-m", "spot_mcp"], cwd=str(HERE),
                                        env=dict(os.environ)))


def make_llm_post(llm_url: str, api_key: Optional[str] = None) -> LLMPost:
    import httpx2
    client = httpx2.AsyncClient(timeout=180, headers={"Authorization": "Bearer " + api_key} if api_key else {})

    async def post(payload: Dict[str, Any]) -> Dict[str, Any]:
        r = await client.post(llm_url.rstrip("/") + "/v1/chat/completions", json=payload)
        if r.status_code != 200:
            raise RuntimeError("llama-server HTTP %d: %s" % (r.status_code, r.text[:300]))
        return r.json()
    return post


async def amain(a) -> None:
    async with make_mcp_client(a.mcp_url) as client:
        if a.list_tools:
            print(json.dumps(mcp_tools_to_openai((await client.list_tools()).tools), indent=2))
            return
        out = await run_agent(client, make_llm_post(a.llm_url, os.environ.get("LLM_API_KEY")), a.flag_id,
                              model=a.model, max_steps=a.max_steps, prefetch=a.prefetch)
        print(json.dumps(out, indent=2, ensure_ascii=False))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--flag-id", type=int, default=1)
    p.add_argument("--mcp-url", default=os.environ.get("MCP_URL"), help="streamable HTTP URL; unset = stdio")
    p.add_argument("--llm-url", default=os.environ.get("LLM_URL", "http://localhost:8080"))
    p.add_argument("--model", default=os.environ.get("LLM_MODEL", "system2"))
    p.add_argument("--max-steps", type=int, default=4)
    p.add_argument("--prefetch", action="store_true", help="fetch get_flag_context before the first LLM call")
    p.add_argument("--list-tools", action="store_true")
    asyncio.run(amain(p.parse_args()))


if __name__ == "__main__":
    main()
