"""Shared fixtures. Run from amd/system1/:  python -m pytest service/tests -q
Set SYSTEM1_SKIP_MODEL=1 to skip the tests that load real Laya (CPU, ~1 GB RAM, ~10-20 s)."""
import os
import sys
from pathlib import Path

import pytest

SYSTEM1 = Path(__file__).resolve().parents[2]          # amd/system1
sys.path.insert(0, str(SYSTEM1))
os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")

from triage.events import mission_events               # noqa: E402
from triage.kit import load_kit                         # noqa: E402
from triage.questions import QUESTIONS                  # noqa: E402

HOLDOUT_MISSION = "M006"


def events_for(kit, mission_id):
    m = kit.missions[mission_id]
    return mission_events(m, kit.actions_of(mission_id), kit.locations, kit.assets, kit.readings,
                          kit.anomalies, source="kit")


@pytest.fixture(scope="session")
def kit():
    return load_kit()


@pytest.fixture(scope="session")
def m006_events(kit):
    return events_for(kit, HOLDOUT_MISSION)


@pytest.fixture(scope="session")
def sample_items(m006_events):
    """One pre_action, one action (with an anomaly if the mission has one) and the mission event."""
    pre = next(e for e in m006_events if e["kind"] == "pre_action")
    acts = [e for e in m006_events if e["kind"] == "action"]
    act = next((e for e in acts if e["anomaly"]), acts[0])
    mis = next(e for e in m006_events if e["kind"] == "mission")
    return [{"id": e["event_id"], "kind": e["kind"], "event": e} for e in (pre, act, mis)]


class FakeEngine:
    """Engine stand-in: uniform probabilities, records what it was asked."""
    checkpoint = "fake/laya"
    device = "cpu"
    fine_tuned = False

    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def model_info(self):
        return {"checkpoint": self.checkpoint, "fine_tuned": False,
                "temperatures": {"temperature": [1.0, 1.0, 1.0], "temperature_by_options": {}}, "device": "cpu"}

    def predict(self, jobs):
        if self.fail:
            raise RuntimeError("boom")
        self.calls.append(jobs)
        out = []
        for _kind, _event, qids in jobs:
            ans = {}
            for q in qids:
                opts = list(QUESTIONS[q]["criteria"])
                ans[q] = {"answer": opts[0], "probs": {o: 1 / len(opts) for o in opts}, "confidence": 1 / len(opts)}
            out.append(ans)
        return out, {"items": len(jobs), "decisions": sum(len(j[2]) for j in jobs), "forward_ms": 0.0, "skipped": {}}
