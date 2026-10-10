"""The ask graph: bounded tool loop, allowlist, retrieval fallback, degraded modes, deadline."""
import asyncio
import time

from fakes import chat_reply


def _tool_loop(name="search_spot_manual", args=None, n=1):
    """A model that calls `name` n times per turn while tools are offered, then answers."""
    def chat(body):
        if body.get("tools"):
            return 200, chat_reply(None, [{"name": name, "args": args or {"query": "docking low battery"}}] * n)
        return 200, chat_reply("Dock before 25 %% battery [manual:1].")
    return chat


def test_step_cap_is_enforced(make_client, world):
    world.chat = _tool_loop()
    out = make_client().post("/v1/ask", json={"question": "How should Spot dock at low battery?"}).json()
    assert len(world.of("mcp")) == 4 and [t["status"] for t in out["tool_calls"]] == ["ok"] * 4
    assert out["mode"] == "tools" and out["answer"].startswith("Dock before 25")
    assert out["citations"] == ["manual:1"] and out["model"] == "qwen3.5-9b" and out["steps"] == 5
    last = world.of("gateway:system2")[-1]["body"]
    assert "tools" not in last                                   # forced final turn has no tools
    assert "Tool budget used" in last["messages"][-1]["content"]
    offered = {t["function"]["name"] for t in world.of("gateway:system2")[0]["body"]["tools"]}
    assert offered == {"get_flag_context", "search_spot_manual", "search_policy", "search_similar_incidents"}


def test_max_steps_lowers_the_cap(make_client, world):
    world.chat = _tool_loop()
    out = make_client().post("/v1/ask", json={"question": "docking?", "max_steps": 2}).json()
    assert len(world.of("mcp")) == 2 and out["max_tool_calls"] == 2


def test_many_tool_calls_in_one_turn_are_capped(make_client, world):
    world.chat = _tool_loop(n=6)
    out = make_client().post("/v1/ask", json={"question": "docking?"}).json()
    assert len(world.of("mcp")) == 4
    assert [t["status"] for t in out["tool_calls"]] == ["ok"] * 4 + ["skipped_cap"] * 2


def test_disallowed_tool_is_refused_and_counted(make_client, world):
    world.chat = _tool_loop(name="delete_everything", args={})
    out = make_client().post("/v1/ask", json={"question": "wipe it"}).json()
    assert world.of("mcp") == [] and [t["status"] for t in out["tool_calls"]] == ["refused"] * 4
    assert out["citations"] == []


def test_no_tool_calls_triggers_one_retrieval_step(make_client, world):
    world.chat = lambda body: (200, chat_reply("Grounded answer about [manual:1] and [flag:42]."))
    out = make_client().post("/v1/ask", json={"question": "What is wrong with flag 42?", "flag_id": 42}).json()
    assert out["mode"] == "retrieval_fallback"
    assert sorted(t["name"] for t in out["tool_calls"]) == ["get_flag_context", "search_policy", "search_spot_manual"]
    assert all(t["by"] == "fallback" for t in out["tool_calls"])
    calls = world.of("gateway:system2")
    assert len(calls) == 2 and "tools" not in calls[1]["body"]
    assert "Retrieved context" in calls[1]["body"]["messages"][-1]["content"]
    assert sorted(out["citations"]) == ["flag:42", "manual:1"]


def test_tool_calling_unsupported_degrades(make_client, world):
    def chat(body):   # llama-server without --jinja rejects tools
        if body.get("tools"):
            return 400, {"error": {"message": "tools param requires --jinja flag", "type": "invalid_request_error"}}
        return 200, chat_reply("From the manual [manual:1].")
    world.chat = chat
    out = make_client().post("/v1/ask", json={"question": "docking?"}).json()
    assert out["mode"] == "retrieval_fallback" and out["answer"] == "From the manual [manual:1]."
    assert "search_similar_incidents" in [t["name"] for t in out["tool_calls"]]
    assert "model call failed" in out["error"]


def test_model_down_lists_sources(make_client, world):
    world.chat = lambda body: (500, {"error": {"message": "upstream down"}})
    out = make_client().post("/v1/ask", json={"question": "docking?"}).json()
    assert out["mode"] == "no_model" and out["model"] is None
    assert "[manual:1]" in out["answer"] and "manual:1" in out["citations"]


def test_mcp_down_gives_no_context(make_client, world):
    world.mcp_down = True
    out = make_client().post("/v1/ask", json={"question": "docking?"}).json()
    assert out["mode"] == "no_context" and out["answer"].startswith("No answer")
    assert world.of("gateway:system2") == []


def test_ask_deadline(make_client, world):
    async def slow(body):
        await asyncio.sleep(5)
        return 200, chat_reply("late")
    world.chat = slow
    t0 = time.perf_counter()
    out = make_client(ASK_DEADLINE_S=2).post("/v1/ask", json={"question": "docking?"}).json()
    assert time.perf_counter() - t0 < 3.5
    assert out["mode"] == "no_model" and "deadline" in out["error"]
