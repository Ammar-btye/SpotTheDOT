"""End to end against the local Docker pgvector DB (stand-in for Neon), System 1 mocked.

Starts it with db/local_pgvector.sh, applies db/setup.py migrate + seed --force-reseed, ingests replay events through the
real pipeline (real SQL), then checks every table the pipeline writes and the one-request_id trace.
Skipped when db/setup.py or db/local_pgvector.sh is missing, Docker is unavailable, or SKIP_INTEGRATION=1.
Set INTEGRATION_DATABASE_URL to use an already-running database instead of starting the container.
Setup and teardown run `db/setup.py seed --force-reseed` (the destructive path; plain `seed` never
overwrites flags, audit M5), which restores the seeded events/flags this test touched.
"""
import os
import shutil
import subprocess
import sys
import uuid

import pytest

from app.deps import build_services
from app.main import create_app

from .conftest import ADMIN, REPO_ROOT, laya_answers, make_settings, replay_event, system1_route

pytestmark = pytest.mark.integration
DB_DIR = REPO_ROOT / "db"
LOCAL_URL = "postgresql://postgres:postgres@localhost:5433/spot"


def _skip_reason():
    if os.environ.get("SKIP_INTEGRATION") == "1":
        return "SKIP_INTEGRATION=1"
    if os.environ.get("INTEGRATION_DATABASE_URL"):
        return None
    if not (DB_DIR / "setup.py").exists() or not (DB_DIR / "local_pgvector.sh").exists():
        return "db/setup.py or db/local_pgvector.sh not present yet"
    if not shutil.which("docker") or subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        return "Docker is not available"
    return None


def _setup(url, *cmd):
    env = {**os.environ, "DATABASE_URL": url, "LOGS_DATABASE_URL": url}
    r = subprocess.run([sys.executable, str(DB_DIR / "setup.py"), *cmd], env=env, capture_output=True, text=True,
                       timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.fixture(scope="module")
def db_url():
    reason = _skip_reason()
    if reason:
        pytest.skip(reason)
    url = os.environ.get("INTEGRATION_DATABASE_URL")
    if not url:
        r = subprocess.run(["bash", str(DB_DIR / "local_pgvector.sh")], capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, r.stdout + r.stderr
        url = LOCAL_URL
    _setup(url, "migrate")
    _setup(url, "seed", "--force-reseed")   # a known baseline: the 58 seeded flags (plain `seed` never overwrites)
    yield url
    _setup(url, "seed", "--force-reseed")   # restore the seeded events/flags


@pytest.fixture
async def live(db_url, mock):
    import httpx
    settings = make_settings(database_url=db_url, logs_database_url=db_url, embed_dim=1024)
    svc = build_services(settings)
    await svc.open()
    app = create_app(settings, services=svc)
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://backend", headers=ADMIN)
    system1_route(mock, lambda it: laya_answers(it["kind"], event=it["event"]))
    mock.route(host="embed.test").mock(side_effect=httpx.ConnectError("embed down"))   # -> full-text fallback
    mock.route(host="mcp.test").mock(side_effect=httpx.ConnectError("mcp down"))       # -> SQL packet
    yield svc, client
    await client.aclose()
    await svc.sink.drain()
    await svc.close()


async def test_ingest_end_to_end_writes_every_table(live):
    svc, client = live
    source = "itest-" + uuid.uuid4().hex[:8]
    rid = "r-itest-" + uuid.uuid4().hex[:8]
    events = [replay_event(e) for e in ("E00001", "E00018", "E00019", "E00022")]   # M001: start, A0009, end
    before = (await svc.db.fetchone("SELECT count(*) AS n FROM flags"))["n"]
    r = await client.post("/api/v1/events/batch", json={"events": events, "source": source},
                          headers={"X-Request-ID": rid})
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    assert all(x["persisted"] and not x["warnings"] for x in res), res
    by_id = {x["event_id"]: x for x in res}
    assert by_id["E00001"]["kind"] is None
    assert by_id["E00018"]["kind"] == "pre_action"
    act = by_id["E00019"]
    assert act["kind"] == "action" and act["decision"]["escalated"] and act["flag"]["flag_id"]
    mis = by_id["E00022"]
    assert mis["kind"] == "mission" and mis["decision"]["escalated"]
    await svc.sink.drain()

    db = svc.db
    raw = await db.fetch("SELECT event_id, payload FROM raw.spot_event_log WHERE source = %s ORDER BY log_id",
                         (source,))
    assert [x["event_id"] for x in raw] == ["E00001", "E00018", "E00019", "E00022"]
    assert raw[2]["payload"] == events[2]                                            # verbatim
    ev = await db.fetchone("SELECT payload FROM events WHERE event_id = 'E00019'")
    assert ev["payload"]["triage"]["request_id"] == act["request_id"] == rid + "-002"
    assert ev["payload"]["triage"]["escalated"] is True and "enriched" in ev["payload"]
    preds = await db.fetch("SELECT event_kind, question FROM system1_predictions WHERE action_id = 'A0009' "
                           "AND model = 'laya-test'")
    assert {(p["event_kind"], p["question"]) for p in preds} >= {("action", "escalate"), ("pre_action", "will_fail")}
    flag = await db.fetchone("SELECT * FROM flags WHERE flag_id = %s", (act["flag"]["flag_id"],))
    assert flag["triage_event_id"] == "act-A0009" and flag["escalated"]
    assert flag["priority"] in ("P1", "P2") and flag["category"]                    # real columns, not just reasons
    # idempotent against the 58 seeded flags: the seeded row is updated, never duplicated
    assert act["flag"]["created"] is False and mis["flag"]["created"] is False
    dup = await db.fetchone("SELECT count(*) AS n FROM flags WHERE triage_event_id IN ('act-A0009', 'mis-M001')")
    assert dup["n"] == 2
    assert (await db.fetchone("SELECT count(*) AS n FROM flags"))["n"] == before
    assert [x["rule"] for x in flag["reasons"]][:2] == ["laya_verdict", "rules_verdict"]
    calls = await db.fetch("SELECT system, ok, request_id FROM app.model_calls WHERE request_id LIKE %s",
                           (rid + "%",))
    assert calls == []   # successes are logged by the (here mocked) System 1 service itself (audit M2)
    reqs = await db.fetch("SELECT route, status FROM app.request_log WHERE request_id = %s", (rid,))
    assert reqs == [{"route": "/api/v1/events/batch", "status": 200}]


async def test_reads_against_real_schema(live):
    svc, client = live
    ov = (await client.get("/api/v1/insights/overview")).json()
    cards = {c["key"]: c for c in ov["insights"]}
    assert cards["green_but_broken"]["value"] == 21
    assert cards["battery_cliff"]["value"] == 33.3
    assert cards["v1_vs_v2_matched_battery"]["value"] == 5.3
    fid = (await client.get("/api/v1/flags", params={"limit": 1})).json()["items"][0]["flag_id"]
    ctx = (await client.get("/api/v1/flags/%d/context" % fid)).json()       # MCP not mocked -> SQL fallback
    assert ctx["source"] == "sql_fallback"
    for url in ("/api/v1/missions/M001/timeline", "/api/v1/locations", "/api/v1/assets/HX-204",
                "/api/v1/events?limit=5", "/api/v1/ops/model-calls", "/api/v1/search?q=HX-204"):
        r = await client.get(url)
        assert r.status_code == 200, (url, r.text)


async def test_write_path_works_as_spot_app_role(db_url, mock):
    """The backend's real permissions: run ingest, ack (+ RAG note), explain, replay and ops as a login role in
    `spot_app` (read/write public; INSERT-only raw/app; UPDATE app.job_runs)."""
    import asyncio

    import httpx
    import psycopg
    owner = await psycopg.AsyncConnection.connect(db_url, autocommit=True)
    has = await (await owner.execute("SELECT 1 FROM pg_roles WHERE rolname = 'spot_app'")).fetchone()
    if not has:
        await owner.close()
        pytest.skip("role spot_app not created by db/migrations/007_roles.sql")
    user = "backend_itest_" + uuid.uuid4().hex[:6]
    await owner.execute("CREATE ROLE %s LOGIN PASSWORD 'itest' IN ROLE spot_app" % user)
    url = db_url.replace("postgres:postgres@", "%s:itest@" % user)
    settings = make_settings(database_url=url, logs_database_url=url, embed_dim=1024)
    svc = build_services(settings)
    await svc.open()
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(settings, services=svc)),
                               base_url="http://backend", headers=ADMIN)
    system1_route(mock, lambda it: laya_answers(it["kind"], event=it["event"]))
    mock.post("http://embed.test/v1/embeddings").mock(return_value=httpx.Response(
        200, json={"data": [{"index": 0, "embedding": [0.01] * 1024}], "model": "m"}))
    mock.route(host="mcp.test").mock(side_effect=httpx.ConnectError("mcp down"))
    try:
        res = (await client.post("/api/v1/events", json=replay_event("E00019"),
                                 params={"source": "itest-role-" + user})).json()
        assert res["persisted"] and not res["warnings"], res
        fid = res["flag"]["flag_id"]
        ack = (await client.post("/api/v1/flags/%d/ack" % fid, json={"note": "role test note"})).json()
        assert ack["rag_indexed"] is True, ack
        exp = await client.post("/api/v1/flags/%d/explain" % fid, params={"refresh": "true"})
        assert exp.status_code == 200 and exp.json().get("assessment_id"), exp.text
        r = await client.post("/api/v1/replay/start", json={"speed": 0, "limit": 5})
        assert r.status_code == 200
        for _ in range(100):
            st = (await client.get("/api/v1/replay/status")).json()
            if st["state"] == "finished":
                break
            await asyncio.sleep(0.05)
        assert st["state"] == "finished" and st["errors"] == 0
        for u in ("/api/v1/ops/model-calls", "/api/v1/ops/jobs", "/api/v1/insights/overview"):
            assert (await client.get(u)).status_code == 200, u
        await svc.sink.drain()
        job = await svc.db.fetchone("SELECT status FROM app.job_runs WHERE job = 'replay' ORDER BY run_id DESC LIMIT 1")
        assert job["status"] == "finished"                         # UPDATE on app.job_runs is granted
        await owner.execute("DELETE FROM documents WHERE doc_id = %s", (ack["doc_id"],))
    finally:
        await client.aclose()
        await svc.close()
        await owner.execute("DROP ROLE IF EXISTS %s" % user)
        await owner.close()
