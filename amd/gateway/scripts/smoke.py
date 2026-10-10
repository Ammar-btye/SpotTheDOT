"""Smoke-test a running gateway: one call per alias, json_schema on system2, auth, latency overhead.

    python scripts/smoke.py                                   # GATEWAY_URL (default http://127.0.0.1:4000)
    python scripts/smoke.py --only system2,system1            # skip aliases whose upstream isn't up
    python scripts/smoke.py --image path/to/gauge.png         # also send a real image to system2-vision
    python scripts/smoke.py --stubs                           # start offline stubs + a gateway first (no models)

Needs LITELLM_MASTER_KEY. Prints one PASS/FAIL line per check and exits 1 on any failure. The system1 check sends
a hand-built mission event (valid against amd/system1 schemas); --stubs uses tests/stubs.py for every upstream.
"""
import argparse
import base64
import json
import os
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
GATEWAY = HERE.parent
ALIASES = ("system2", "system2-vision", "system1", "embed")
SCHEMA = {"type": "json_schema", "json_schema": {"name": "smoke", "schema": {
    "type": "object", "properties": {"status": {"type": "string", "enum": ["ok"]}},
    "required": ["status"], "additionalProperties": False}}}
MISSION = {"mission_id": "SMOKE-1", "configuration_version": "v1", "timestamp": "2026-10-10T00:00:00Z",
           "reported_status": "COMPLETED", "duration_min": 30, "start_battery_pct": 100, "end_battery_pct": 62,
           "actions_total": 10, "actions_failed": 0, "failure_types": [],
           "anomalies_by_severity": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}, "worst_anomaly": None}
PNG_1PX = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
failures = []


def check(name, ok, detail=""):
    print("%s  %-34s %s" % ("PASS" if ok else "FAIL", name, detail))
    if not ok:
        failures.append(name)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_stubs_and_gateway(key):
    sys.path.insert(0, str(GATEWAY / "tests"))
    from stubs import ServerThread
    ports = {n: free_port() for n in ("text", "vision", "laya", "embed", "gateway")}
    for role, name in (("llama", "text"), ("llama", "vision"), ("laya", "laya"), ("embed", "embed")):
        ServerThread(role, ports[name], name).start()
    env = dict(os.environ, LITELLM_MASTER_KEY=key, GATEWAY_HOST="127.0.0.1", GATEWAY_PORT=str(ports["gateway"]),
               LLAMA_URL="http://127.0.0.1:%d" % ports["text"], VISION_LLAMA_URL="http://127.0.0.1:%d" % ports["vision"],
               SYSTEM1_URL="http://127.0.0.1:%d" % ports["laya"], EMBED_URL="http://127.0.0.1:%d" % ports["embed"])
    env.pop("DATABASE_URL", None)
    proc = subprocess.Popen([sys.executable, str(GATEWAY / "serve.py")], env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    url = "http://127.0.0.1:%d" % ports["gateway"]
    for _ in range(240):
        try:
            if httpx.get(url + "/health/liveliness", timeout=1).status_code == 200:
                return url, proc, "http://127.0.0.1:%d" % ports["text"]
        except httpx.HTTPError:
            time.sleep(0.5)
    proc.kill()
    sys.exit("gateway did not start")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("GATEWAY_URL", "http://127.0.0.1:4000"))
    ap.add_argument("--only", default=",".join(ALIASES))
    ap.add_argument("--image", help="PNG/JPEG to send to system2-vision (default: a 1x1 PNG)")
    ap.add_argument("--stubs", action="store_true", help="start offline stubs and a local gateway first")
    ap.add_argument("--repeat", type=int, default=10, help="system2 calls for the latency line")
    args = ap.parse_args()
    key = os.environ.get("LITELLM_MASTER_KEY") or ("sk-smoke-stub-key-000001" if args.stubs else "")
    if not key:
        sys.exit("set LITELLM_MASTER_KEY")
    proc, direct = None, None
    if args.stubs:
        args.url, proc, direct = start_stubs_and_gateway(key)
    only = [a.strip() for a in args.only.split(",") if a.strip()]
    auth = {"Authorization": "Bearer " + key}
    http = httpx.Client(timeout=60)
    try:
        check("liveliness (no auth)", http.get(args.url + "/health/liveliness").status_code == 200)
        r = http.post(args.url + "/v1/chat/completions", json={"model": "system2", "messages": []})
        check("no key -> 401", r.status_code == 401, str(r.status_code))
        ids = sorted(m["id"] for m in http.get(args.url + "/v1/models", headers=auth).json().get("data", []))
        check("/v1/models lists the aliases", ids == sorted(ALIASES), ",".join(ids))

        def chat(model, messages, **extra):
            t0 = time.perf_counter()
            resp = http.post(args.url + "/v1/chat/completions", headers=auth,
                             json=dict({"model": model, "messages": messages}, **extra))
            return resp, (time.perf_counter() - t0) * 1000

        if "system2" in only:
            r, ms = chat("system2", [{"role": "user", "content": 'Reply with {"status":"ok"}.'}],
                         temperature=0, max_tokens=32, response_format=SCHEMA,
                         chat_template_kwargs={"enable_thinking": False})
            ok = r.status_code == 200
            content = r.json()["choices"][0]["message"]["content"] if ok else r.text[:200]
            try:
                parsed = json.loads(content) if ok else None
            except ValueError:
                parsed = None
            check("system2 json_schema", ok and isinstance(parsed, dict) and (args.stubs or "status" in parsed),
                  "%d ms %s timings=%s" % (ms, content[:60], "timings" in r.json() if ok else "-"))
            lat = [chat("system2", [{"role": "user", "content": "ok"}], max_tokens=1)[1] for _ in range(args.repeat)]
            line = "median %.0f ms over %d" % (statistics.median(lat), len(lat))
            if direct:
                d = []
                for _ in range(args.repeat):
                    t0 = time.perf_counter()
                    http.post(direct + "/v1/chat/completions", json={"messages": [], "max_tokens": 1})
                    d.append((time.perf_counter() - t0) * 1000)
                line += "; direct to stub %.0f ms -> gateway overhead ~%.0f ms" % (
                    statistics.median(d), statistics.median(lat) - statistics.median(d))
            check("system2 latency", True, line)
        if "system2-vision" in only:
            img = base64.b64encode(Path(args.image).read_bytes()).decode() if args.image else PNG_1PX
            mime = "image/jpeg" if args.image and args.image.lower().endswith((".jpg", ".jpeg")) else "image/png"
            content = [{"type": "image_url", "image_url": {"url": "data:%s;base64,%s" % (mime, img)}},
                       {"type": "text", "text": "Describe this image in five words."}]
            r, ms = chat("system2-vision", [{"role": "user", "content": content}], max_tokens=48,
                         chat_template_kwargs={"enable_thinking": False})
            check("system2-vision image", r.status_code == 200,
                  "%d ms %s" % (ms, (r.json()["choices"][0]["message"]["content"] if r.status_code == 200
                                     else r.text)[:80]))
        if "system1" in only:
            r, ms = chat("system1", [{"role": "user", "content": json.dumps({"kind": "mission", "event": MISSION})}])
            ok = r.status_code == 200
            data = json.loads(r.json()["choices"][0]["message"]["content"]) if ok else {}
            check("system1 /v1/predict", ok and bool(data.get("items")),
                  "%d ms model=%s %s" % (ms, data.get("model"), "" if ok else r.text[:120]))
            r, _ = chat("system1", [{"role": "user", "content": "not json"}])
            check("system1 bad input -> 400", r.status_code == 400, str(r.status_code))
        if "embed" in only:
            t0 = time.perf_counter()
            r = http.post(args.url + "/v1/embeddings", headers=auth, json={"model": "embed", "input": ["pump hot"]})
            ok = r.status_code == 200
            check("embed", ok, "%d ms dim=%s" % ((time.perf_counter() - t0) * 1000,
                                                len(r.json()["data"][0]["embedding"]) if ok else r.text[:120]))
    finally:
        if proc:
            proc.terminate()
            proc.wait(10)
    print("\n%d failure(s)" % len(failures) if failures else "\nall checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
