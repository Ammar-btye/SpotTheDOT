"""Minimal demo backend: feed SPOT events through System 1 (Laya) and stream the answers.

    pip install -r demo/requirements.txt
    python demo/server.py                                  # base Laya (near chance: untuned)
    python demo/server.py --model checkpoints/run1/best    # a fine-tuned checkpoint (or set LAYA_MODEL)
    open http://127.0.0.1:8000

Two feeds, both streamed back as NDJSON (one line per classified event):
- POST /api/mock {"missions": 2, "seed": 7}
      mock missions from the simulator (demo/mock_feed.py).
- POST /api/kit  {"missions": ["M006"] | "holdout" | "all", "files": {"actions.csv": "<csv text>", ...}}
      the challenge-kit CSVs. Uploaded files replace the bundled data/kit/ copies; the rest are bundled.
Each event is rendered as JSON (the app's format), Laya answers the event's questions, and every
answer is compared with its expected label: the real outcome (Track A) or the triage policy (Track B).
"""
import argparse
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import List, Union

os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn                                                   # noqa: E402
from fastapi import Body, FastAPI, HTTPException                 # noqa: E402
from fastapi.responses import FileResponse, StreamingResponse    # noqa: E402

from mock_feed import holdout_missions, kit_events, mock_events  # noqa: E402
from triage.harness import LayaRunner                            # noqa: E402
from triage.kit import KIT_DIR, load_kit                         # noqa: E402
from triage.questions import QUESTION_SETS, TRACK, questions_for  # noqa: E402
from triage.render import render_json, render_log                # noqa: E402

HERE = Path(__file__).resolve().parent
KIT_FILES = ("locations.csv", "assets.csv", "missions.csv", "actions.csv", "readings.csv", "anomalies.csv")
MAX_MOCK_MISSIONS = 20

app = FastAPI(title="SPOT System 1 demo")
RUNNER: LayaRunner = None
LOCK = threading.Lock()      # one model, one request at a time


def classify(events: list, source: str, held: set):
    """Yield one NDJSON line per event: the event, Laya's answers and whether each matches."""
    yield json.dumps({"type": "start", "source": source, "events": len(events),
                      "missions": sorted({e["mission_id"] for e in events})}) + "\n"
    for e in events:
        row = {"id": e["event_id"], "state": render_json(e), "questions": questions_for(e["kind"]),
               "expected": {q: e["labels"][q] for q in QUESTION_SETS[e["kind"]]}, "meta": {}}
        t0 = time.perf_counter()
        with LOCK:
            res = RUNNER.predict([row])
        answers = {p["qid"]: {"pred": p["pred"], "expected": p["gold"], "correct": p["pred"] == p["gold"],
                              "confidence": round(p["confidence"], 3)} for p in res["predictions"]}
        yield json.dumps({"type": "event", "event_id": e["event_id"], "mission_id": e["mission_id"],
                          "kind": e["kind"], "track": TRACK[e["kind"]], "held_out": e["mission_id"] in held,
                          "log": render_log(e), "state": row["state"], "answers": answers,
                          "skipped": res["skipped"], "ms": round(1000 * (time.perf_counter() - t0))}) + "\n"
    yield json.dumps({"type": "done"}) + "\n"


def ndjson(lines) -> StreamingResponse:
    return StreamingResponse(lines, media_type="application/x-ndjson")


@app.get("/")
def index():
    return FileResponse(HERE / "index.html")


@app.get("/api/info")
def info():
    kit = load_kit()
    return {"model": RUNNER.name, "device": str(RUNNER.device), "missions": sorted(kit.missions),
            "holdout": holdout_missions(), "kit_files": list(KIT_FILES)}


@app.post("/api/mock")
def run_mock(missions: int = Body(1, embed=True), seed: int = Body(7, embed=True)):
    if not 1 <= missions <= MAX_MOCK_MISSIONS:
        raise HTTPException(400, "missions must be between 1 and %d" % MAX_MOCK_MISSIONS)
    return ndjson(classify(mock_events(missions, seed), "mock", set()))


@app.post("/api/kit")
def run_kit(missions: Union[str, List[str]] = Body("holdout", embed=True), files: dict = Body({}, embed=True)):
    unknown = set(files) - set(KIT_FILES)
    if unknown:
        raise HTTPException(400, "unexpected file(s) %s; expected some of %s" % (sorted(unknown), list(KIT_FILES)))
    with tempfile.TemporaryDirectory() as tmp:
        for name in KIT_FILES:
            text = files[name] if name in files else (KIT_DIR / name).read_text(encoding="utf-8")
            (Path(tmp) / name).write_text(text, encoding="utf-8")
        try:
            kit = load_kit(Path(tmp))
        except (KeyError, ValueError) as err:
            raise HTTPException(400, "could not read the CSVs (%s: %s)" % (type(err).__name__, err))
    held = set(holdout_missions())
    if missions == "holdout":
        ids = [m for m in sorted(kit.missions) if m in held]
    elif missions == "all":
        ids = sorted(kit.missions)
    else:
        ids = [m for m in missions if m in kit.missions]
    ids = [m for m in ids if kit.actions_of(m)]
    if not ids:
        raise HTTPException(400, "none of the selected missions have actions in these CSVs")
    try:
        events = kit_events(kit, ids)
    except (KeyError, ValueError, TypeError) as err:
        raise HTTPException(400, "the CSVs don't join up (%s: %s)" % (type(err).__name__, err))
    return ndjson(classify(events, "kit", held))


def main():
    global RUNNER
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.environ.get("LAYA_MODEL", "convaiinnovations/laya"),
                    help="Hub ID or local checkpoint dir (e.g. checkpoints/run1/best)")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    print("loading %s ..." % args.model, flush=True)
    RUNNER = LayaRunner.load(args.model, args.device)
    print("model on %s; open http://%s:%d" % (RUNNER.device, args.host, args.port), flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
