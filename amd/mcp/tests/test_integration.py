"""Integration test against a real Postgres + embedding service. Skipped unless DATABASE_URL and EMBED_URL are set.

    cd amd/mcp && set -a && . ./.env && set +a && python -m pytest -q tests/test_integration.py
"""
from __future__ import annotations

import asyncio
import os
import re

import pytest

from spot_mcp.service import est_tokens

pytestmark = [pytest.mark.anyio,
              pytest.mark.skipif(not (os.environ.get("DATABASE_URL") and os.environ.get("EMBED_URL")),
                                 reason="needs DATABASE_URL and EMBED_URL (a seeded DB + embedding service)")]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def svc():
    from spot_mcp.server import service_from_env
    s = service_from_env()
    yield s
    await s.sink.close()
    await s.repo.db.close()
    await s.embedder.close()


async def test_connection_is_read_only(svc):
    with pytest.raises(Exception, match="read-only"):
        await svc.repo.db.fetch("CREATE TABLE mcp_should_not_exist (x int)")


async def test_sql_tools(svc):
    db = svc.repo.db
    a = (await db.fetch("SELECT action_id, mission_id FROM actions ORDER BY action_id LIMIT 1"))[0]
    act = await svc.get_action(a["action_id"])
    assert act["id"] == "action:%s" % a["action_id"] and "asset" in act
    m = await svc.get_mission_summary(a["mission_id"])
    assert m["true_health"]["true_health_pct"] is not None
    rel = await svc.get_reliability_stats(group_by="battery_band")
    assert sum(r["n"] for r in rel["rows"]) > 0
    risk = await svc.get_battery_risk(20)
    assert risk["band"] == "<=25" and risk["this_band"]["n"] > 0
    try:
        raw = await svc.get_raw_event_log(a["mission_id"], limit=5)
    except Exception as exc:
        if "permission denied" in str(exc):
            pytest.skip("this role lacks SELECT on raw.spot_event_log (contract §6 asks the DB side to grant it)")
        raise
    assert raw["events"] and all(e["id"].startswith("log:") for e in raw["events"])


async def test_rag_tools(svc):
    out = await svc.search_spot_manual("How do I dock Spot to charge the battery?")
    assert out["results"] or out["no_relevant_results"]
    junk = await svc.search_spot_manual("recipe for sourdough bread with rye flour")
    print("junk top:", junk.get("message"), junk.get("top_similarity"))
    pol = await svc.search_policy("battery low priority")
    assert pol["results"], pol
    hist = await svc.search_asset_history((await svc.repo.db.fetch("SELECT asset_id FROM assets LIMIT 1"))[0]["asset_id"])
    assert hist["results"]


async def test_flag_context_packet(svc):
    rows = await svc.repo.db.fetch("SELECT flag_id FROM flags ORDER BY score DESC LIMIT 1")
    if not rows:
        pytest.skip("flags table is empty (no System 1 run yet)")
    fid = rows[0]["flag_id"]
    p = await svc.logged("get_flag_context", {"flag_id": fid},
                         lambda: svc.get_flag_context(fid, request_id="itest"), request_id="itest")
    assert list(p)[-1] == "question" and p["citation_ids"] and p["facts"]
    print("packet tokens ~", int(len(str(p)) / 3.6), "gaps:", p.get("gaps"))
    await asyncio.sleep(1.0)  # let the fire-and-forget log insert land
    has_app = await svc.repo.db.fetch("SELECT to_regclass('app.mcp_tool_calls') IS NOT NULL AS ok")
    if has_app[0]["ok"] and os.environ.get("MCP_LOG_CALLS", "1") != "0":
        try:
            logged = await svc.repo.db.fetch("SELECT count(*)::int AS n FROM app.mcp_tool_calls "
                                             "WHERE request_id = 'itest' AND tool = 'get_flag_context'")
        except Exception as exc:  # spot_mcp_reader may INSERT but not SELECT app.*
            pytest.skip("can't read app.mcp_tool_calls with this role: %s" % exc)
        assert logged[0]["n"] >= 1


# ── Graph RAG (contract §7) ─────────────────────────────────────────────────────────────────────
async def _graph_or_skip(db):
    ok = await db.fetch("SELECT to_regclass('public.kg_edges') IS NOT NULL AS ok")
    if not ok[0]["ok"]:
        pytest.skip("no knowledge graph in this DB (migration 009 + db/job.sh graph)")
    n = await db.fetch("SELECT count(*)::int AS n FROM kg_edges")
    if not n[0]["n"]:
        pytest.skip("kg_edges is empty (run db/job.sh graph)")


async def test_graph_section_for_a_real_flag(svc):
    db = svc.repo.db
    await _graph_or_skip(db)
    rows = await db.fetch("SELECT flag_id FROM flags WHERE action_id IS NOT NULL ORDER BY score DESC, flag_id LIMIT 3")
    if not rows:
        pytest.skip("flags table is empty")
    for r in rows:
        p = await svc.get_flag_context(r["flag_id"])
        g = p.get("graph")
        assert g, p.get("gaps")
        keys = list(p)
        assert keys.index("facts") < keys.index("graph") and keys[-1] == "question"
        assert est_tokens(g) <= svc.s.graph_token_budget and est_tokens(p) <= svc.s.packet_token_budget
        ids = [it["id"] for it in g]
        assert set(ids) <= set(p["citation_ids"])
        # every graph citation resolves to a real node or document (checkable)
        found = await db.fetch("SELECT node_id AS id FROM kg_nodes WHERE node_id = ANY(%s) "
                               "UNION SELECT doc_id FROM documents WHERE doc_id = ANY(%s)", (ids, ids))
        assert set(ids) <= {x["id"] for x in found}
        assert all(re.search(r" —[a-z_]+→ ", it["fact"]) for it in g)
        print("flag", r["flag_id"], "graph ~%d tokens, packet ~%d:" % (est_tokens(g), est_tokens(p)))
        for it in g:
            print("   ", it["id"], "|", it["fact"])


async def test_graph_tools_on_real_data(svc):
    db = svc.repo.db
    await _graph_or_skip(db)
    loc = (await db.fetch("SELECT l.location_id, l.location_name, l.environment FROM locations l "
                          "JOIN actions a USING (location_id) WHERE a.status = 'FAILED' "
                          "GROUP BY 1, 2, 3 ORDER BY count(*) DESC, 1 LIMIT 1"))[0]
    out = await svc.graph_neighborhood("location:%s" % loc["location_id"], hops=1, k=30)
    facts = [f["fact"] for f in out["facts"]]
    # the location's real environment, as a readable triple
    assert "%s (%s) —has_environment→ %s" % (loc["location_name"], loc["location_id"], loc["environment"]) in facts
    # statistics match SQL over the core tables: 'FT —common_at→ Name (WPxx) (n=X of Y, ...)'
    stats = [f for f in facts if "—common_at→" in f]
    assert stats, facts
    for f in stats:
        ft, n, of = re.match(r"^(\w+) —common_at→ .* \(n=(\d+) of (\d+),", f).groups()
        real = (await db.fetch(
            "SELECT count(*) FILTER (WHERE status = 'FAILED' AND failure_type = %s)::int AS n, count(*)::int AS of "
            "FROM actions WHERE location_id = %s", (ft, loc["location_id"])))[0]
        assert (int(n), int(of)) == (real["n"], real["of"]), f
    # name and id resolution: text first
    by_name = await svc.graph_neighborhood(loc["location_name"], k=5)
    assert by_name["resolved_by"] == "text" and by_name["entity"]["id"] == "location:%s" % loc["location_id"]
    by_id = await svc.graph_neighborhood(loc["location_id"], k=5)
    assert by_id["entity"]["id"] == "location:%s" % loc["location_id"]
    # search: entry nodes by text + vector, then facts
    sg = await svc.search_graph("robot loses localization in a noisy area", k=5)
    assert sg["entry_nodes"] and sg["facts"], sg
    print("search_graph entries:", [(e["id"], e.get("sim"), e["match"]) for e in sg["entry_nodes"]])
    for f in sg["facts"][:8]:
        print("   ", f["id"], "|", f["fact"])
