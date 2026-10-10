"""Replay the kit's replay.ndjson through the ingest pipeline, as a background asyncio task.

Event gaps are the robot's own timestamps divided by `speed` (60 = one minute of mission time per second),
capped at `max_gap_s` so the hours between missions don't stall the demo. speed=0 means "as fast as possible".
Each event gets its own request_id (`rp<run>-<event_id>`) and an app.request_log row, like an HTTP ingest.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .reference import parse_ts

log = logging.getLogger("backend.replay")
# The streamed replay is its own source; `db/setup.py seed` imports the file itself as 'replay.ndjson'.
SOURCE = "replay"


def load_replay(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class ReplayManager:
    def __init__(self, pipeline, sink, replay_path: Path, default_speed: float = 60.0, default_max_gap_s: float = 2.0):
        self.pipeline = pipeline
        self.sink = sink
        self.replay_path = replay_path
        self.default_speed = default_speed
        self.default_max_gap_s = default_max_gap_s
        self.task: Optional[asyncio.Task] = None
        self.run_seq = 0
        self._status: Dict[str, Any] = {"state": "idle"}

    @property
    def running(self) -> bool:
        return self.task is not None and not self.task.done()

    def status(self) -> Dict[str, Any]:
        s = dict(self._status)
        if s.get("state") == "running" and s.get("started_at"):
            s["elapsed_s"] = round(time.time() - s["_t0"], 1)
        s.pop("_t0", None)
        return s

    def select(self, events: List[Dict[str, Any]], missions: Optional[List[str]], start_at: Optional[str],
               limit: Optional[int]) -> List[Dict[str, Any]]:
        if missions:
            want = set(missions)
            events = [e for e in events if e.get("mission_id") in want]
        if start_at:
            idx = next((i for i, e in enumerate(events) if e.get("event_id") == start_at), None)
            if idx is None:
                raise ValueError("start_at event %r not in the replay" % start_at)
            events = events[idx:]
        if limit:
            events = events[:limit]
        return events

    async def start(self, *, speed: Optional[float] = None, max_gap_s: Optional[float] = None,
                    missions: Optional[List[str]] = None, start_at: Optional[str] = None, limit: Optional[int] = None,
                    triage_mode: Optional[str] = None) -> Dict[str, Any]:
        if self.running:
            raise RuntimeError("a replay is already running; stop it first")
        events = self.select(load_replay(self.replay_path), missions, start_at, limit)
        if not events:
            raise ValueError("no replay events match the selection")
        self.run_seq += 1
        speed = self.default_speed if speed is None else speed
        max_gap_s = self.default_max_gap_s if max_gap_s is None else max_gap_s
        mode = triage_mode or self.pipeline.default_mode
        run_id = await self.sink.job_start("replay", {"speed": speed, "max_gap_s": max_gap_s, "missions": missions,
                                                      "start_at": start_at, "limit": limit, "triage_mode": mode,
                                                      "events": len(events)})
        self._status = {"state": "running", "run": self.run_seq, "job_run_id": run_id, "speed": speed,
                        "max_gap_s": max_gap_s, "triage_mode": mode, "total": len(events), "sent": 0,
                        "escalated": 0, "flags_created": 0, "laya_unavailable": 0, "skipped": 0, "errors": 0,
                        "last_event": None, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                        "finished_at": None, "error": None, "_t0": time.time()}
        self.task = asyncio.create_task(self._run(events, speed, max_gap_s, mode, run_id))
        return self.status()

    async def stop(self) -> Dict[str, Any]:
        if self.running:
            self._status["state"] = "stopping"
            self.task.cancel()  # type: ignore[union-attr]
            try:
                await self.task  # type: ignore[misc]
            except asyncio.CancelledError:
                pass
        return self.status()

    async def _run(self, events: List[Dict[str, Any]], speed: float, max_gap_s: float, mode: str,
                   run_id: Optional[int]) -> None:
        st = self._status
        prev_ts = None
        state, error = "finished", None
        try:
            for i, ev in enumerate(events):
                ts = parse_ts(ev.get("timestamp"))
                if i and speed > 0 and ts and prev_ts:
                    gap = max(0.0, (ts - prev_ts).total_seconds()) / speed
                    await asyncio.sleep(min(gap, max_gap_s))
                prev_ts = ts or prev_ts
                rid = "rp%d-%s" % (self.run_seq, ev.get("event_id"))
                t0 = time.perf_counter()
                try:
                    res = await self.pipeline.ingest(ev, source=SOURCE, request_id=rid, mode=mode)
                except Exception as exc:  # noqa: BLE001 - one bad event must not end the replay
                    log.exception("replay event %s failed", ev.get("event_id"))
                    st["errors"] += 1
                    self.sink.request(request_id=rid, route="replay", method="REPLAY", status=500,
                                      latency_ms=int((time.perf_counter() - t0) * 1000), error=str(exc))
                    continue
                self.sink.request(request_id=rid, route="replay", method="REPLAY", status=200,
                                  latency_ms=int((time.perf_counter() - t0) * 1000),
                                  error="; ".join(res.get("warnings") or []) or None)
                st["sent"] += 1
                if res.get("skipped"):
                    st["skipped"] += 1
                if (res.get("decision") or {}).get("escalated"):
                    st["escalated"] += 1
                if (res.get("flag") or {}).get("created"):
                    st["flags_created"] += 1
                if (res.get("system1") or {}).get("status") == "laya_unavailable":
                    st["laya_unavailable"] += 1
                st["last_event"] = {"event_id": ev.get("event_id"), "event_type": ev.get("event_type"),
                                    "mission_id": ev.get("mission_id"), "timestamp": ev.get("timestamp"),
                                    "flag_id": (res.get("flag") or {}).get("flag_id")}
                if st["sent"] % 25 == 0:
                    await self.sink.job_progress(run_id, self._counts())
        except asyncio.CancelledError:
            state = "stopped"
            raise
        except Exception as exc:  # noqa: BLE001
            state, error = "error", str(exc)
            log.exception("replay failed")
        finally:
            st["state"] = state
            st["error"] = error
            st["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            await asyncio.shield(self.sink.job_finish(run_id, state, self._counts(), error))

    def _counts(self) -> Dict[str, Any]:
        return {k: self._status.get(k) for k in ("total", "sent", "escalated", "flags_created", "laya_unavailable",
                                                 "skipped", "errors")}
