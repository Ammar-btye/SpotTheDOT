"""The service answers exactly what LayaRunner answers on the same benchmark rows (real Laya, CPU).

Events are rebuilt from the kit for holdout mission M006; their JSON rendering must equal the benchmark's
`real:<event_id>:json` state, so the service is scored on the benchmark's own inputs.
Checkpoint: $LAYA_CHECKPOINT (default: base convaiinnovations/laya). Skip with SYSTEM1_SKIP_MODEL=1.
"""
import json
import os

import pytest
from conftest import HOLDOUT_MISSION, SYSTEM1
from fastapi.testclient import TestClient

from service.app import create_app
from service.config import Settings
from triage.render import render_json

pytestmark = pytest.mark.skipif(os.environ.get("SYSTEM1_SKIP_MODEL") == "1", reason="SYSTEM1_SKIP_MODEL=1")

CHECKPOINT = os.environ.get("LAYA_CHECKPOINT", "convaiinnovations/laya")


@pytest.fixture(scope="module")
def engine():
    from service.engine import Engine
    return Engine.load(CHECKPOINT, device="cpu", amp=False)


@pytest.fixture(scope="module")
def bench_rows():
    rows = {}
    with open(SYSTEM1 / "data" / "benchmark.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["id"].startswith("real:") and r["id"].endswith(":json"):
                rows[r["id"].split(":")[1]] = r
    return rows


def test_service_matches_runner(engine, bench_rows, m006_events):
    picked = []
    for kind, n in (("pre_action", 2), ("action", 3), ("mission", 1)):
        evs = [e for e in m006_events if e["kind"] == kind and e["event_id"] in bench_rows][:n]
        assert len(evs) == n, "benchmark has no %s rows for %s" % (kind, HOLDOUT_MISSION)
        picked += evs
    rows = [bench_rows[e["event_id"]] for e in picked]
    for e, r in zip(picked, rows):
        assert render_json(e) == r["state"], e["event_id"]

    direct = engine.runner.predict(rows, batch_size=64, calibrated=True)["predictions"]
    expected = {(p["id"].split(":")[1], p["qid"]): p for p in direct}

    with TestClient(create_app(Settings(), engine=engine)) as c:
        body = c.post("/v1/predict", json={"items": [{"id": e["event_id"], "kind": e["kind"], "event": e}
                                                     for e in picked]}).json()
    assert body["device"] == "cpu" and body["fine_tuned"] == engine.fine_tuned
    n = 0
    for item in body["items"]:
        for qid, a in item["answers"].items():
            p = expected[(item["id"], qid)]
            assert a["answer"] == p["pred"], (item["id"], qid)
            for opt, v in p["probs"].items():
                assert a["probs"][opt] == pytest.approx(v, abs=1e-4)
            n += 1
    assert n == len(direct) == sum(len(r["questions"]) for r in rows)


def test_temperatures_are_applied(engine, bench_rows, m006_events):
    """Calibrated output = softmax(logits / T) with the checkpoint's temperature for that question."""
    ev = next(e for e in m006_events if e["kind"] == "action")
    answers, _ = engine.predict([("action", ev, ["escalate"])])
    raw = engine.runner.predict([bench_rows[ev["event_id"]]], calibrated=False)["predictions"]
    raw = next(p for p in raw if p["qid"] == "escalate")
    import numpy as np
    t = engine.runner._temp(raw["qtype"], raw["k"])
    z = np.array(raw["logits"]) / t
    p = np.exp(z - z.max())
    p /= p.sum()
    assert answers[0]["escalate"]["probs"]["A"] == pytest.approx(float(p[0]), abs=1e-4)
