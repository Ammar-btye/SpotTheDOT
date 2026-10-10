"""Auth, startup checks, /health, /v1/graph."""
import pytest

from fakes import settings_env
from orchestrator.app import create_app
from orchestrator.config import Settings


def test_auth_required_except_open_paths(make_client):
    c = make_client()
    assert c.post("/v1/assess", json={"flag_id": 42}, headers={"X-API-Key": ""}).status_code == 401
    assert c.post("/v1/ask", json={"question": "hi"}, headers={"X-API-Key": "wrong-key-0123456789"}).status_code == 401
    assert c.post("/v1/assess", json={"flag_id": 42}).status_code == 200      # client default header has the key
    assert c.get("/health", headers={"X-API-Key": ""}).status_code == 200
    assert c.get("/v1/graph", headers={"X-API-Key": ""}).status_code == 200


def test_refuses_to_start_without_a_usable_key():
    env = settings_env()
    del env["ORCHESTRATOR_API_KEY"]
    with pytest.raises(RuntimeError, match="ORCHESTRATOR_API_KEY is not set"):
        create_app(Settings.from_env(env))
    with pytest.raises(RuntimeError, match="fewer than 16"):
        create_app(Settings.from_env({**env, "ORCHESTRATOR_API_KEY": "short"}))
    with pytest.raises(RuntimeError, match="whitespace"):
        create_app(Settings.from_env({**env, "ORCHESTRATOR_API_KEY": " padded-key-0123456789 "}))
    create_app(Settings.from_env({**env, "ORCHESTRATOR_ALLOW_NO_AUTH": "1"}))    # tests only


def test_no_auth_mode_is_open(world):
    from fastapi.testclient import TestClient
    env = settings_env(ORCHESTRATOR_ALLOW_NO_AUTH=1)
    del env["ORCHESTRATOR_API_KEY"]
    with TestClient(create_app(Settings.from_env(env), http=world.http(), chat=None)) as c:
        assert c.post("/v1/assess", json={"flag_id": 42}).status_code == 200
        assert c.get("/health").json()["auth"] is False


def test_graph_mermaid(make_client):
    g = make_client().get("/v1/graph").json()
    for node in ("load_context", "system1", "route", "vision", "system2", "finalize"):
        assert node in g["assess"]
    assert "system1_only" in g["assess"] and "fallback_retrieve" in g["ask"]
    txt = make_client().get("/v1/graph", params={"format": "text", "graph": "ask"}).text
    assert txt.lstrip().startswith("---") and "agent" in txt


def test_health_shallow_and_deep(make_client):
    c = make_client(VISION_URL="")
    h = c.get("/health").json()
    assert h["status"] == "ok" and h["config"]["vision"] == "unset" and "deps" not in h
    deep = c.get("/health", params={"deep": "true"}).json()["deps"]
    assert deep["mcp"]["status"] == "up" and deep["system2"]["status"] == "up" and deep["vision"]["status"] == "unset"


def test_settings_defaults():
    s = Settings.from_env({"GATEWAY_URL": "http://gw:4000/v1/", "ASK_MAX_TOOL_CALLS": "9", "LITELLM_MASTER_KEY": "sk"})
    assert s.gateway_url == "http://gw:4000" and s.ask_max_tool_calls == 4 and s.gateway_key == "sk"
    assert s.deadline_s == 40.0 and s.port == 8085 and s.ask_tool_allowlist == ("search_*", "get_*")
    assert Settings.from_env({"SYSTEM2_URL": ""}).system2_url is None
