"""AMD serving smoke test (Phase 1.1, SRV-00): can one Qwen3.5 candidate on the gfx1151 box answer one
JSON-schema-constrained request? Stdlib only, so it runs on the box before any venv exists. Start llama-server
first (README "Serving smoke test"), then run from amd/system2:

    python scripts/smoke_serve.py --backend rocm
    python scripts/smoke_serve.py --url http://127.0.0.1:8080 --fixture navigation --backend vulkan
    python scripts/smoke_serve.py --runs 3 --max-tokens 350

Sends one fixture packet to llama-server's OpenAI-compatible /v1/chat/completions with a per-packet JSON schema
(cited ids and recommended_action are enums built from the packet, the R3 field order), thinking off. Checks the
reply parses, matches the schema, cites only packet ids and picks an allowed action. Reports latency, tokens/s and
the backend label. Writes results/smoke/<utc>.json. Exit 0 = valid on every run, 1 = invalid output, 2 = no server.

This tests feasibility only: the prompt is a placeholder and the fixture is the Phase 1 packet, not the MCP packet
(Phase 2 switches both).
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("event", "facts", "asset", "waypoint", "incidents")
CONFIDENCE = ("low", "medium", "high")
SYSTEM = ("You explain one escalated SPOT robot inspection flag to a plant operator. Use only the packet. "
          "Every claim cites the ids of the rows it comes from. Copy numbers exactly; do no arithmetic. "
          "Pick recommended_action from allowed_actions. If the packet cannot support an answer, set "
          "insufficient_context to true.")


def load_packet(name: str) -> dict:
    with open(ROOT / "fixtures" / ("%s.json" % name), encoding="utf-8") as f:
        return json.load(f)["response"]["packet"]


def row_ids(packet: dict) -> List[str]:
    return [r["id"] for s in SECTIONS for r in (packet.get(s) or [])]


def schema_for(packet: dict) -> dict:
    """R3 order: evidence -> answer -> question -> recommended_action -> confidence -> insufficient_context."""
    ids = row_ids(packet)
    ev = {"type": "object", "additionalProperties": False, "required": ["claim", "ids"],
          "properties": {"claim": {"type": "string"},
                         "ids": {"type": "array", "minItems": 1, "items": {"type": "string", "enum": ids}}}}
    props = {"evidence": {"type": "array", "maxItems": 5, "items": ev},
             "answer": {"type": "string"}, "question": {"type": "string"},
             "recommended_action": {"type": "string", "enum": list(packet["allowed_actions"])},
             "confidence": {"type": "string", "enum": list(CONFIDENCE)},
             "insufficient_context": {"type": "boolean"}}
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


def check(out: dict, packet: dict) -> List[str]:
    """Problems with a parsed reply; empty list = valid."""
    errs, ids, keys = [], set(row_ids(packet)), list(schema_for(packet)["properties"])
    if list(out) != keys:
        errs.append("keys %r, want %r" % (list(out), keys))
    for e in out.get("evidence") or []:
        bad = [i for i in e.get("ids") or [] if i not in ids]
        if bad:
            errs.append("cites unknown ids %r" % bad)
    if out.get("recommended_action") not in packet["allowed_actions"]:
        errs.append("action %r not allowed" % out.get("recommended_action"))
    if out.get("confidence") not in CONFIDENCE:
        errs.append("confidence %r" % out.get("confidence"))
    return errs


def _post(url: str, body: dict, timeout: float) -> Tuple[dict, float]:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data, time.perf_counter() - t0


def run_once(base: str, packet: dict, max_tokens: int, timeout: float) -> Dict:
    body = {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": json.dumps(packet, ensure_ascii=False)}],
            "temperature": 0, "max_tokens": max_tokens,
            "response_format": {"type": "json_schema", "json_schema": {"name": "explanation",
                                                                       "schema": schema_for(packet)}},
            "chat_template_kwargs": {"enable_thinking": False}}
    data, dt = _post(base.rstrip("/") + "/v1/chat/completions", body, timeout)
    text = data["choices"][0]["message"].get("content") or ""
    tm, usage = data.get("timings") or {}, data.get("usage") or {}
    rec = {"latency_s": round(dt, 2), "model": data.get("model"),
           "prompt_tokens": usage.get("prompt_tokens") or tm.get("prompt_n"),
           "output_tokens": usage.get("completion_tokens") or tm.get("predicted_n"),
           "gen_tok_s": tm.get("predicted_per_second"), "prompt_tok_s": tm.get("prompt_per_second")}
    try:
        out = json.loads(text)
        rec["errors"] = check(out, packet) if isinstance(out, dict) else ["reply is not a JSON object"]
        rec["output"] = out
    except ValueError as exc:
        rec["errors"], rec["raw"] = ["not JSON: %s" % exc], text[:2000]
    return rec


def _f(v) -> str:
    return "-" if v is None else ("%.1f" % v if isinstance(v, float) else str(v))


def main() -> int:
    ap = argparse.ArgumentParser(description="One schema-constrained request against a running llama-server.")
    ap.add_argument("--url", default="http://127.0.0.1:8080", help="llama-server base URL")
    ap.add_argument("--fixture", default="equipment", help="fixture name under fixtures/ (its packet is sent)")
    ap.add_argument("--backend", default="unknown", help="label recorded with the result: rocm | vulkan | cpu")
    ap.add_argument("--runs", type=int, default=1, help="repeat the request (first run includes warm-up)")
    ap.add_argument("--max-tokens", type=int, default=350)
    ap.add_argument("--timeout", type=float, default=300.0, help="seconds per request")
    ap.add_argument("--out-dir", default=str(ROOT / "results" / "smoke"))
    args = ap.parse_args()

    packet = load_packet(args.fixture)
    runs = []
    for i in range(args.runs):
        try:
            rec = run_once(args.url, packet, args.max_tokens, args.timeout)
        except (urllib.error.URLError, OSError) as exc:
            print("no llama-server at %s: %s" % (args.url, exc), file=sys.stderr)
            return 2
        runs.append(rec)
        print("run %d | %s | %ss | %s prompt tok, %s out tok | gen %s tok/s | prompt %s tok/s | %s"
              % (i + 1, rec["model"], _f(rec["latency_s"]), _f(rec["prompt_tokens"]), _f(rec["output_tokens"]),
                 _f(rec["gen_tok_s"]), _f(rec["prompt_tok_s"]), "VALID" if not rec["errors"] else
                 "INVALID: " + "; ".join(rec["errors"])), flush=True)
    ok = all(not r["errors"] for r in runs)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / ("%s.json" % stamp)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"url": args.url, "backend": args.backend, "fixture": args.fixture, "valid": ok,
                   "runs": runs}, f, indent=2)
    print("backend %s | %d/%d valid | wrote %s" % (args.backend, sum(not r["errors"] for r in runs), len(runs),
                                                     path))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
