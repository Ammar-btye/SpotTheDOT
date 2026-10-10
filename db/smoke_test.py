#!/usr/bin/env python3
"""End-to-end check of the RAG layer: embeds queries over HTTP and calls the contract's search functions.

  python db/smoke_test.py                          # the three standard queries
  python db/smoke_test.py "pump bearing too hot"   # your own query (vector + hybrid)
  python db/smoke_test.py --roles                  # also check spot_mcp_reader permissions (needs a superuser URL)
(If the knowledge graph exists it also runs a text, a vector and a 2-hop graph query; contract §7.)

Env: DATABASE_URL, LOGS_DATABASE_URL, EMBED_URL, EMBED_MODEL, EMBED_DIM, EMBED_QUERY_PREFIX.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "amd" / "embed"))
import spotdb  # noqa: E402
from client import EmbedClient, to_pgvector  # noqa: E402

DEFAULT = [
    ("vector", "pressure gauge reading out of range on a heat exchanger"),
    ("vector", "robot lost localization in a noisy turbine hall"),
    ("hybrid", "HX-204"),
]


def show(rows, score_name):
    for r in rows:
        extra = "" if len(r) <= 4 else "  sim=%.3f text_match=%s" % (r[4] or 0, r[5])
        print("   %-24s %s=%.4f%s  %s" % (r[0], score_name, r[2], extra, (r[1] or "")[:90]))


def run(conn, client, mode, query):
    t0 = time.perf_counter()
    vec = to_pgvector(client.embed([query], kind="query")[0])
    t_embed = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    if mode == "vector":
        rows = conn.execute("SELECT doc_id, title, similarity FROM match_documents(%s::vector, match_count => 5)",
                            (vec,)).fetchall()
    else:
        rows = conn.execute("SELECT doc_id, title, score, kind, similarity, text_match "
                            "FROM match_documents_hybrid(%s::vector, %s, match_count => 5)", (vec, query)).fetchall()
    t_sql = (time.perf_counter() - t0) * 1000
    print("\n[%s] %r  (embed %.0f ms, sql %.0f ms)" % (mode, query, t_embed, t_sql))
    show(rows, "sim" if mode == "vector" else "rrf")
    return rows


def graph(conn, client):
    """Graph RAG (contract §7): a name entry point, a vector entry point and a 2-hop neighbourhood."""
    print("\n[graph] kg_nodes %d, kg_edges %d" % (conn.execute("SELECT count(*) FROM kg_nodes").fetchone()[0],
                                                conn.execute("SELECT count(*) FROM kg_edges").fetchone()[0]))
    t0 = time.perf_counter()
    rows = conn.execute("SELECT node_id, score FROM match_kg_nodes_text('HX-204', NULL, 3)").fetchall()
    print("   text 'HX-204' (%.0f ms): %s" % ((time.perf_counter() - t0) * 1000, rows))
    vec = to_pgvector(client.embed(["robot lost localization"], kind="query")[0])
    rows = conn.execute("SELECT node_id, similarity FROM match_kg_nodes(%s::vector, ARRAY['topic','failure_type'], 3)",
                        (vec,)).fetchall()
    print("   vector 'robot lost localization': %s" % [(n, round(s, 3)) for n, s in rows])
    t0 = time.perf_counter()
    rows = conn.execute("SELECT hop, array_to_string(path, ' '), weight FROM graph_neighborhood(ARRAY['location:WP05'], 2, "
                        "NULL, ARRAY['failure_type','topic','manual'], 5)").fetchall()
    print("   neighbourhood of location:WP05 (%.0f ms):" % ((time.perf_counter() - t0) * 1000))
    for hop, path, w in rows:
        print("     hop %d  w=%.3f  %s" % (hop, w, path))


def check_roles(conn):
    """Create a throwaway login in spot_mcp_reader and verify: SELECT public ok, INSERT app ok, writes to public fail."""
    import psycopg
    from urllib.parse import urlparse
    conn.execute("DROP ROLE IF EXISTS smoke_mcp")
    conn.execute("CREATE ROLE smoke_mcp LOGIN PASSWORD 'smoke' IN ROLE spot_mcp_reader")
    u = urlparse(spotdb.database_url())
    url = u._replace(netloc="smoke_mcp:smoke@%s:%s" % (u.hostname, u.port or 5432)).geturl()
    ok = True
    with psycopg.connect(url, autocommit=True) as c:
        def expect(sql, allowed):
            nonlocal ok
            try:
                c.execute(sql)
                res = True
            except psycopg.errors.InsufficientPrivilege:
                res = False
            ok &= res == allowed
            print("   %-6s %-70s %s" % ("ok" if res == allowed else "FAIL", sql[:70], "allowed" if res else "denied"))
        print("\n[roles] spot_mcp_reader")
        expect("SELECT count(*) FROM documents", True)
        expect("SELECT count(*) FROM flags", True)
        expect("SELECT count(*) FROM raw.spot_event_log", True)
        expect("SELECT count(*) FROM raw.get_mission_event_log('M014')", True)
        expect("INSERT INTO app.mcp_tool_calls (tool, args, ok) VALUES ('smoke', '{}', true) RETURNING call_id", True)
        expect("UPDATE flags SET status = status WHERE false", False)
        expect("DELETE FROM documents WHERE false", False)
        expect("SELECT * FROM app.model_calls LIMIT 1", False)   # only call_id is readable (for RETURNING)
        expect("SELECT count(*) FROM raw.kit_rows", False)
        if spotdb.has_table(conn, "public.kg_nodes"):          # Graph RAG (contract §7)
            expect("SELECT count(*) FROM kg_edges", True)
            expect("SELECT count(*) FROM match_kg_nodes_text('HX-204')", True)
            expect("SELECT count(*) FROM graph_neighborhood(ARRAY['location:WP05'], 2)", True)
            expect("DELETE FROM kg_nodes WHERE false", False)
    conn.execute("DELETE FROM app.mcp_tool_calls WHERE tool = 'smoke'")
    conn.execute("DROP ROLE smoke_mcp")
    return ok


def main():
    args = [a for a in sys.argv[1:] if a != "--roles"]
    conn = spotdb.connect(autocommit=True)
    client = EmbedClient()
    queries = [(m, q) for q in args for m in ("vector", "hybrid")] if args else DEFAULT
    for kind, n in conn.execute("SELECT kind, count(*) FROM documents GROUP BY 1 ORDER BY 1"):
        print("documents.%-14s %d" % (kind, n))
    for mode, q in queries:
        run(conn, client, mode, q)
    if spotdb.has_table(conn, "public.kg_nodes"):
        graph(conn, client)
    if "--roles" in sys.argv and not check_roles(conn):
        sys.exit("role check failed")


if __name__ == "__main__":
    main()
