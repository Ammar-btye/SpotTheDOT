"""Mock SPOT data: simulated missions, turned into the same events the kit produces.

    python demo/mock_feed.py --missions 2 --seed 7          # print the events as NDJSON
    python demo/mock_feed.py --missions 1 | head -3

The simulator (triage/simulate.py) is fitted on the training missions only, so mock missions never
copy a held-out kit mission. Every event carries its expected labels: the simulated outcome for
Track A and the triage policy for Track B, exactly as in the benchmark.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from triage.events import mission_events      # noqa: E402
from triage.kit import Kit, load_kit           # noqa: E402
from triage.policy import label                # noqa: E402
from triage.simulate import Simulator          # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def holdout_missions() -> list:
    """The held-out kit missions from data/manifest.json (never trained on)."""
    with open(ROOT / "data" / "manifest.json", encoding="utf-8") as f:
        return json.load(f)["holdout_missions"]


def labelled(events: list) -> list:
    """Attach labels. pre_action events take theirs from the matching real outcome event."""
    outcome = {e["action_id"]: e for e in events if e["kind"] == "action"}
    for e in events:
        e["labels"] = label(e, outcome.get(e.get("action_id")) if e["kind"] == "pre_action" else None)
    return events


def kit_events(kit: Kit, mission_ids: list) -> list:
    out = []
    for m in mission_ids:
        out.extend(mission_events(kit.missions[m], kit.actions_of(m), kit.locations, kit.assets,
                                  kit.readings, kit.anomalies, "kit"))
    return labelled(out)


def mock_events(n_missions: int, seed: int, kit: Kit = None) -> list:
    kit = kit or load_kit()
    held = set(holdout_missions())
    sim = Simulator(kit, [m for m in kit.missions if m not in held])
    out = []
    for mission, actions, readings, anomalies in sim.missions(n_missions, seed, prefix="MOCK"):
        out.extend(mission_events(mission, actions, kit.locations, kit.assets, readings, anomalies, "mock"))
    return labelled(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--missions", type=int, default=1)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    for e in mock_events(args.missions, args.seed):
        print(json.dumps(e))


if __name__ == "__main__":
    main()
