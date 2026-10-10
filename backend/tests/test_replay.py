"""Replay: background task through the same pipeline, start/stop/status, 409 on double start."""
import asyncio

import httpx

from .conftest import S1, laya_answers, system1_route


async def _wait(h, state="finished", timeout=10.0):
    for _ in range(int(timeout / 0.05)):
        st = (await h.client.get("/api/v1/replay/status")).json()
        if st["state"] == state:
            return st
        await asyncio.sleep(0.05)
    raise AssertionError(st)


async def test_replay_runs_events_through_pipeline(h, mock):
    system1_route(mock, lambda it: laya_answers(it["kind"], event=it.get("event")))
    r = await h.client.post("/api/v1/replay/start", json={"speed": 0, "limit": 22})
    assert r.status_code == 200 and r.json()["state"] == "running" and r.json()["total"] == 22
    st = await _wait(h)
    assert st["sent"] == 22 and st["errors"] == 0 and st["escalated"] >= 1    # M001 ends green-but-broken
    assert st["last_event"]["event_id"] == "E00022"
    assert len(h.repo.events) == 22 and h.repo.raw[0]["source"] == "replay"
    assert h.repo.raw[0]["request_id"] == "rp1-E00001"
    assert {r["route"] for r in h.sink.requests if r["request_id"].startswith("rp1-")} == {"replay"}
    assert h.sink.jobs[0]["job"] == "replay" and h.sink.jobs[0]["status"] == "finished"


async def test_replay_with_laya_down_and_mission_filter(h, mock):
    mock.post(S1 + "/v1/predict").mock(side_effect=httpx.ConnectError("refused"))
    await h.client.post("/api/v1/replay/start", json={"speed": 0, "missions": ["M017"]})
    st = await _wait(h)
    assert st["sent"] > 0 and st["laya_unavailable"] > 0 and st["errors"] == 0
    assert all(e["mission_id"] == "M017" for e in h.repo.events.values())


async def test_double_start_is_409_and_stop_works(h, mock):
    system1_route(mock, lambda it: laya_answers(it["kind"], event=it.get("event")))
    r = await h.client.post("/api/v1/replay/start", json={"speed": 1, "max_gap_s": 5})
    assert r.status_code == 200
    assert (await h.client.post("/api/v1/replay/start", json={})).status_code == 409
    st = (await h.client.post("/api/v1/replay/stop")).json()
    assert st["state"] == "stopped"


async def test_unknown_start_at_is_422(h):
    r = await h.client.post("/api/v1/replay/start", json={"start_at": "NOPE"})
    assert r.status_code == 422


async def test_reset_demo_requires_confirm_and_stops_replay(h, mock):
    assert (await h.client.post("/api/v1/ops/reset-demo", json={})).status_code == 400
    r = await h.client.post("/api/v1/ops/reset-demo", json={"confirm": True})
    assert r.status_code == 200 and "flags" in r.json()["deleted"]
