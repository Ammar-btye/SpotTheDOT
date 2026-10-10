"""Smoke-test a running System 1 service with real kit events (run on the host, from amd/system1/):

    python -m service.smoke                         # http://localhost:8082, mission M006, 1 of each kind
    python -m service.smoke --url http://system1:8082 --mission M012 --repeat 5
    python -m service.smoke --batch 64              # latency of a full 64-event batch
    python -m service.smoke --print-payload > payload.json

Builds one pre_action, one action (with an anomaly when the mission has one) and the mission event with
triage/kit.py + triage/events.mission_events, POSTs them to /v1/predict and prints the answers and latency.
Standard library only (plus the triage package).
"""
import argparse
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from triage.events import mission_events  # noqa: E402
from triage.kit import load_kit            # noqa: E402


def build_items(mission_id: str, batch: int = 0) -> list:
    kit = load_kit()
    m = kit.missions[mission_id]
    evs = mission_events(m, kit.actions_of(mission_id), kit.locations, kit.assets, kit.readings, kit.anomalies,
                         source="kit")
    if batch:
        evs = (evs * (batch // len(evs) + 1))[:batch]
        return [{"id": "%s#%d" % (e["event_id"], i), "kind": e["kind"], "event": e} for i, e in enumerate(evs)]
    pre = next(e for e in evs if e["kind"] == "pre_action")
    acts = [e for e in evs if e["kind"] == "action"]
    act = next((e for e in acts if e["anomaly"]), acts[0])
    mis = next(e for e in evs if e["kind"] == "mission")
    return [{"id": e["event_id"], "kind": e["kind"], "event": e} for e in (pre, act, mis)]


def call(url: str, path: str, payload=None, timeout: float = 300):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url.rstrip("/") + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8082")
    ap.add_argument("--mission", default="M006")
    ap.add_argument("--batch", type=int, default=0, help="send N events (cycling the mission's events) instead of 3")
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--print-payload", action="store_true")
    args = ap.parse_args()
    payload = {"request_id": "smoke-%d" % int(time.time()), "items": build_items(args.mission, args.batch)}
    if args.print_payload:
        print(json.dumps(payload, indent=2))
        return
    print("health:", call(args.url, "/health"))
    info = call(args.url, "/v1/model")
    print("model:", info["checkpoint"], "fine_tuned=%s" % info["fine_tuned"], "device=%s" % info["device"])
    server_ms, wall_ms, body = [], [], None
    for _ in range(max(1, args.repeat)):
        t0 = time.perf_counter()
        body = call(args.url, "/v1/predict", payload)
        wall_ms.append(1000 * (time.perf_counter() - t0))
        server_ms.append(body["latency_ms"])
    n_dec = sum(len(i["answers"]) for i in body["items"])
    print("%d events, %d decisions/batch | server latency_ms median %d (all %s) | round trip median %.0f ms"
          % (len(body["items"]), n_dec, statistics.median(server_ms), server_ms, statistics.median(wall_ms)))
    if not args.batch:
        print(json.dumps(body, indent=2))


if __name__ == "__main__":
    main()
