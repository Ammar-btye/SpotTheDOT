#!/usr/bin/env python3
"""End-to-end proof across the compose stack (backend -> system1 -> db, mcp -> embed -> db).

    backend/.venv/bin/python scripts/e2e.py                       # both TRIAGE_MODEs, local compose stack
    E2E_MODES=parallel backend/.venv/bin/python scripts/e2e.py
    BACKEND_URL=... E2E_DATABASE_URL=... backend/.venv/bin/python scripts/e2e.py   # another stack / Neon

For each mode it POSTs five kit replay events with a known X-Request-ID and a run+mode-unique `source` (raw is
idempotent on (source, sha256), so a reused source would log no new raw row): an HX-204 action the rules escalate
(A0029), a routine action (A0002), a rules-P1 action base Laya calls routine (A0060), a rules-P3 action base Laya
escalates (A0001), and a mission completion (M001). Then it asserts:
  A1  raw.spot_event_log, events, system1_predictions, flags, app.model_calls and app.request_log all have
      rows for that one request_id (system1_predictions and flags have no request_id column; they are reached
      through events.payload.triage {request_id, triage_event_id, flag_id} and the prediction's created_at)
  A2  GET /flags/{id}/context is the MCP packet (source=mcp, citation_ids, and an app.mcp_tool_calls row
      written by the mcp container under the context call's request_id)
  A3  /flags/{id}/explain is the template fallback (System 2 not deployed)
  A4  /search?q=HX-204 returns hits
  A0  (audit H3) POST /events and /ops/reset-demo without X-Admin-Token get 401; CORS rejects a foreign origin
  A3  (audit M10) also: the template is stored as state TEMPLATE, and amd/embed/ingest.py builds no explanation
      doc from a template
Admin calls send X-Admin-Token from ADMIN_TOKEN (env, else the repo's .env).
and prints per-hop latencies. Needs httpx + psycopg (both in backend/.venv). Exit code 1 if any assertion fails.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
import uuid
from pathlib import Path

import httpx
import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "amd" / "system1" / "data" / "kit" / "replay.ndjson"
BACKEND = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
DB_URL = os.environ.get("E2E_DATABASE_URL") or "postgresql://postgres:%s@localhost:%s/spot" % (
    os.environ.get("POSTGRES_PASSWORD", "postgres"), os.environ.get("DB_PORT", "5433"))
MODES = [m for m in os.environ.get("E2E_MODES", "serial,parallel").split(",") if m]


def _dotenv(name):
    """A value from the repo's .env (compose syntax: KEY=value, optional trailing `  # comment`)."""
    try:
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].split(" #")[0].strip().strip("'\"") or None
    except OSError:
        pass
    return None


ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN") or _dotenv("ADMIN_TOKEN")
ADMIN = {"X-Admin-Token": ADMIN_TOKEN or ""}
TIMEOUT = float(os.environ.get("E2E_TIMEOUT_S", "180"))
RESULTS = []          # (mode, check, ok, detail)


def pick_events():
    """Result events of A0029 (HX-204, rules P2), A0002 (rules P4), A0060 (rules P1; base Laya: log),
    A0001 (rules P3; base Laya: escalate), and M001's completion (rules P2)."""
    actions = ("A0029", "A0002", "A0060", "A0001")
    want = {("action", a) for a in actions} | {("mission", "M001")}
    out = {}
    for line in REPLAY.read_text().splitlines():
        ev = json.loads(line)
        d, t = ev.get("details") or {}, ev["event_type"]
        if t in ("ACTION_COMPLETED", "ACTION_FAILED") and ("action", d.get("action_id")) in want:
            out[("action", d["action_id"])] = ev
        elif t == "MISSION_COMPLETED" and ("mission", ev["mission_id"]) in want:
            out[("mission", ev["mission_id"])] = ev
    return [out[("action", a)] for a in actions] + [out[("mission", "M001")]]


def check(mode, name, ok, detail=""):
    RESULTS.append((mode, name, bool(ok), detail))
    print("  [%s] %-44s %s" % ("PASS" if ok else "FAIL", name, detail))
    return ok


def poll(fn, timeout=10.0):
    """Logging is fire-and-forget: give the async log writes a moment."""
    end = time.monotonic() + timeout
    while True:
        v = fn()
        if v or time.monotonic() > end:
            return v
        time.sleep(0.3)


def q(conn, sql, *args):
    return conn.execute(sql, args).fetchall()


def wait_ready(http):
    end = time.monotonic() + 600
    while time.monotonic() < end:
        try:
            h = http.get(BACKEND + "/health", params={"deep": "true"}, timeout=30).json()
            need = ("database", "logs_database", "system1", "embed", "mcp")
            if all((h.get(k) or {}).get("status") == "up" for k in need):
                return h
            print("waiting for:", {k: (h.get(k) or {}).get("status") for k in need})
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(3)
    raise SystemExit("backend not ready at %s" % BACKEND)


def run_mode(http, conn, mode, run):
    print("\n== TRIAGE_MODE=%s (run %s)" % (mode, run))
    out = {"mode": mode, "events": []}
    events = pick_events()
    for i, ev in enumerate(events):
        rid = "e2e-%s-%s-%d" % (run, mode[0], i)
        t_start = conn.execute("SELECT now() AS t").fetchone()["t"]
        t0 = time.perf_counter()
        r = http.post(BACKEND + "/api/v1/events", json=ev, params={"source": "e2e-%s-%s" % (run, mode), "triage_mode": mode},
                      headers={"X-Request-ID": rid, **ADMIN}, timeout=TIMEOUT)
        wall = int((time.perf_counter() - t0) * 1000)
        r.raise_for_status()
        res = r.json()
        kind, tid = res.get("kind"), res.get("triage_event_id")
        dec = res.get("decision") or {}
        s1 = res.get("system1") or {}
        print(" %s %s (%s) -> kind=%s laya=%s escalated=%s priority=%s agreement=%s flag=%s  [%d ms]" % (
            rid, ev["event_id"], ev["event_type"], kind, s1.get("status"), dec.get("escalated"), dec.get("priority"),
            dec.get("agreement"), (res.get("flag") or {}).get("flag_id"), wall))
        if res.get("warnings"):
            print("    warnings:", res["warnings"])

        # A1: one request_id across the six tables
        raw = poll(lambda: q(conn, "SELECT log_id, source FROM raw.spot_event_log WHERE request_id = %s", rid))
        check(mode, "A1 raw.spot_event_log has request_id", raw, "log_id=%s" % (raw[0]["log_id"] if raw else None))
        evs = q(conn, "SELECT event_id, payload->'triage' AS triage FROM events "
                      "WHERE payload->'triage'->>'request_id' = %s", rid)
        check(mode, "A1 events.payload.triage.request_id", evs, evs[0]["event_id"] if evs else "")
        triage = evs[0]["triage"] if evs else {}
        aid = res.get("action_id")
        mid = ev["mission_id"] if kind == "mission" else None
        key_col, key = ("mission_id", mid) if kind == "mission" else ("action_id", aid)
        preds = q(conn, "SELECT question, answer, confidence, model FROM system1_predictions WHERE event_kind = %%s "
                        "AND %s = %%s AND created_at >= %%s ORDER BY question" % key_col, kind, key, t_start)
        check(mode, "A1 system1_predictions (this request)", preds,
              ", ".join("%s=%s" % (p["question"], p["answer"]) for p in preds))
        fid = (triage or {}).get("flag_id")
        flags = q(conn, "SELECT flag_id, escalated, priority, severity, reasons FROM flags WHERE flag_id = %s",
                  fid) if fid else []
        rv = next((x for x in (flags[0]["reasons"] if flags else []) if x.get("rule") == "rules_verdict"), {})
        if dec.get("escalated"):        # escalated -> a flags row this request wrote (its reasons carry the mode)
            ok = bool(flags) and flags[0]["escalated"] and rv.get("triage_mode") == mode
        else:                           # routine -> no flag, or the seeded flag un-escalated by this request
            ok = not flags or (not flags[0]["escalated"] and rv.get("triage_mode") == mode)
        check(mode, "A1 flags row (escalated) / none (routine)", ok,
              "flag_id=%s escalated=%s %s" % (fid, flags[0]["escalated"] if flags else None, rv.get("detail", ""))
              if fid else "no flag: routine, never seeded")
        mc = poll(lambda: q(conn, "SELECT system, latency_ms, metadata->>'caller' AS caller, device, ok "
                                  "FROM app.model_calls WHERE request_id = %s ORDER BY call_id", rid))
        check(mode, "A1 app.model_calls has request_id", mc,
              "; ".join("%s/%s %sms ok=%s" % (m["system"], m["caller"] or "system1-server", m["latency_ms"], m["ok"])
                        for m in mc))
        rl = poll(lambda: q(conn, "SELECT route, status, latency_ms FROM app.request_log WHERE request_id = %s", rid))
        check(mode, "A1 app.request_log has request_id", rl,
              "%s %s %sms" % (rl[0]["route"], rl[0]["status"], rl[0]["latency_ms"]) if rl else "")
        out["events"].append({"request_id": rid, "event": ev["event_id"], "kind": kind, "triage_event_id": tid,
                              "wall_ms": wall, "pipeline_ms": res.get("latency_ms"),
                              "system1_server_ms": s1.get("latency_ms"), "laya": s1.get("status"),
                              "laya_escalate": (res.get("laya") or {}).get("escalate"),
                              "laya_p": (res.get("laya") or {}).get("p_escalate"),
                              "rules": (res.get("rules") or {}).get("priority"), "decision": dec, "flag_id": fid,
                              "model_calls": [dict(m) for m in mc]})

    # A2: MCP context for the HX-204 flag (seeded, so it exists in both modes)
    fid = out["events"][0]["flag_id"] or conn.execute(
        "SELECT flag_id FROM flags WHERE triage_event_id = 'act-A0029'").fetchone()["flag_id"]
    crid = "e2e-%s-%s-ctx" % (run, mode[0])
    t0 = time.perf_counter()
    r = http.get(BACKEND + "/api/v1/flags/%d/context" % fid, headers={"X-Request-ID": crid}, timeout=TIMEOUT)
    ctx_ms = int((time.perf_counter() - t0) * 1000)
    pk = r.json() if r.status_code == 200 else {}
    cites = pk.get("citation_ids") or []
    check(mode, "A2 context source=mcp", pk.get("source") == "mcp", "flag %s, %d ms" % (fid, ctx_ms))
    check(mode, "A2 context has citation_ids", cites, "%d ids, e.g. %s" % (len(cites), cites[:6]))
    tools = poll(lambda: q(conn, "SELECT tool, latency_ms, result_count, top_similarity, ok FROM app.mcp_tool_calls "
                                 "WHERE request_id = %s", crid))
    check(mode, "A2 app.mcp_tool_calls row from mcp", tools,
          "; ".join("%s %sms n=%s top_sim=%s" % (t["tool"], t["latency_ms"], t["result_count"],
                                                  None if t["top_similarity"] is None else round(t["top_similarity"], 3))
                    for t in tools))
    emb = q(conn, "SELECT count(*) AS n, sum(latency_ms) AS ms FROM app.model_calls WHERE request_id = %s "
                  "AND system = 'embed'", crid)[0]
    out["context"] = {"request_id": crid, "flag_id": fid, "ms": ctx_ms, "mcp_tool_ms": tools[0]["latency_ms"]
                      if tools else None, "embed_calls": emb["n"], "embed_ms": emb["ms"], "citations": len(cites)}

    # A3: explain -> template (System 2 not deployed)
    t0 = time.perf_counter()
    r = http.post(BACKEND + "/api/v1/flags/%d/explain" % fid, params={"refresh": "true"},
                  headers={"X-Request-ID": "e2e-%s-%s-exp" % (run, mode[0])}, timeout=TIMEOUT)
    exp_ms = int((time.perf_counter() - t0) * 1000)
    ex = r.json() if r.status_code == 200 else {}
    check(mode, "A3 explain source=template", ex.get("source") == "template",
          "%d ms, reason=%s, context=%s" % (exp_ms, ex.get("fallback_reason"), ex.get("context_source")))
    st = conn.execute("SELECT state, model FROM assessments WHERE flag_id = %s", (fid,)).fetchone() or {}
    check(mode, "A3 template stored as state TEMPLATE (M10)", st.get("state") == "TEMPLATE" and
          st.get("model") == "template", "state=%s model=%s" % (st.get("state"), st.get("model")))
    sys.path.insert(0, str(ROOT / "amd" / "embed"))
    import ingest as embed_ingest      # noqa: E402  (needs only httpx + psycopg)
    with psycopg.connect(DB_URL, autocommit=True) as plain:     # ingest reads tuples, not dict rows
        docs = embed_ingest.build_explanations(plain)
        n_tpl = plain.execute("SELECT count(*) FROM assessments WHERE model = 'template'").fetchone()[0]
    bad = [d["doc_id"] for d in docs if (d["metadata"] or {}).get("model") in ("template", None)]
    check(mode, "A3 ingest builds no template explanation doc", not bad,
          "%d template assessments in DB, %d explanation docs built, %d from templates" % (n_tpl, len(docs), len(bad)))
    out["explain"] = {"ms": exp_ms, "source": ex.get("source"), "context_source": ex.get("context_source")}

    # A4: search
    t0 = time.perf_counter()
    r = http.get(BACKEND + "/api/v1/search", params={"q": "HX-204"},
                 headers={"X-Request-ID": "e2e-%s-%s-search" % (run, mode[0])}, timeout=TIMEOUT)
    s_ms = int((time.perf_counter() - t0) * 1000)
    sr = r.json() if r.status_code == 200 else {}
    hits = sr.get("hits") or []
    check(mode, "A4 search HX-204 has hits", hits, "%d hits, mode=%s, %d ms, top=%s" % (
        len(hits), sr.get("mode"), s_ms, hits[0]["doc_id"] if hits else None))
    out["search"] = {"ms": s_ms, "mode": sr.get("mode"), "hits": len(hits),
                     "fallback_reason": sr.get("fallback_reason")}
    return out


def check_auth(http, ev):
    """A0 (audit H3): admin endpoints refuse a missing or wrong token; CORS only allows CORS_ORIGINS."""
    print("\n== A0 admin auth + CORS")
    r = http.post(BACKEND + "/api/v1/events", json=ev, params={"source": "e2e-noauth"}, timeout=30)
    check("auth", "A0 POST /events without token -> 401", r.status_code == 401, "%s %s" % (r.status_code, r.text[:80]))
    r = http.post(BACKEND + "/api/v1/ops/reset-demo", json={"confirm": True}, headers={"X-Admin-Token": "wrong"},
                  timeout=30)
    check("auth", "A0 reset-demo with a wrong token -> 401", r.status_code == 401, "%s" % r.status_code)
    r = http.get(BACKEND + "/api/v1/replay/status", headers=ADMIN, timeout=30)
    check("auth", "A0 replay/status with ADMIN_TOKEN -> 200", r.status_code == 200,
          "%s%s" % (r.status_code, "" if ADMIN_TOKEN else " (ADMIN_TOKEN not set in env or .env)"))
    r = http.options(BACKEND + "/api/v1/ops/reset-demo", headers={
        "Origin": "http://evil.example", "Access-Control-Request-Method": "POST"}, timeout=30)
    check("auth", "A0 CORS rejects a foreign origin", r.headers.get("access-control-allow-origin") is None,
          "%s allow-origin=%s" % (r.status_code, r.headers.get("access-control-allow-origin")))


def main() -> int:
    run = dt.datetime.now().strftime("%H%M%S") + uuid.uuid4().hex[:4]
    with httpx.Client() as http, psycopg.connect(DB_URL, autocommit=True, row_factory=dict_row) as conn:
        h = wait_ready(http)
        print("backend health:", {k: (h.get(k) or {}).get("status") for k in
                                  ("database", "logs_database", "system1", "embed", "mcp", "system2")})
        check_auth(http, pick_events()[0])
        summary = [run_mode(http, conn, m, run) for m in MODES]
    out_path = Path(os.environ.get("E2E_OUT", "/tmp/spot-e2e-%s.json" % run))
    out_path.write_text(json.dumps({"run": run, "results": RESULTS, "summary": summary}, indent=1, default=str))
    failed = [r for r in RESULTS if not r[2]]
    print("\n%d checks, %d failed. Details: %s" % (len(RESULTS), len(failed), out_path))
    if len(summary) == 2:
        print("\nserial vs parallel:")
        for a, b in zip(summary[0]["events"], summary[1]["events"]):
            print("  %-10s laya_escalate=%s p=%s rules=%s | serial: escalated=%s %s (%s) | parallel: escalated=%s %s (%s)"
                  % (a["event"], a["laya_escalate"], a["laya_p"], a["rules"], a["decision"].get("escalated"),
                     a["decision"].get("priority"), a["decision"].get("agreement"), b["decision"].get("escalated"),
                     b["decision"].get("priority"), b["decision"].get("agreement")))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
