"""Build the fine-tuning, calibration and benchmark (validation) datasets.

    python scripts/build_data.py                 # holdout fold 2 (default)
    python scripts/build_data.py --holdout-fold 0  # rotate for cross-validation

Writes data/train.jsonl, data/calib.jsonl, data/benchmark.jsonl and data/manifest.json.

Splits (all by MISSION, so no event or rendering of it can appear on both sides):
- The 27 kit missions are dealt into 3 folds of 9 (6 V1 + 3 V2), stratified by serious anomalies.
  The holdout fold is the REAL benchmark segment; the other 18 missions are real training data.
- The simulator is fitted on the 18 training missions only, then generates disjoint synthetic sets:
  train (ST*), calibration (SC*, for temperature fitting) and holdout (SH*, a benchmark segment).
- Counterfactual edits of holdout events form a third benchmark segment (Track B robustness).
"""
import argparse
import copy
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from triage.events import mission_events                        # noqa: E402
from triage.kit import load_kit                                   # noqa: E402
from triage.policy import POLICY_VERSION, label                   # noqa: E402
from triage.questions import QUESTION_SETS, TRACK, questions_for  # noqa: E402
from triage.render import RENDERINGS, render                      # noqa: E402
from triage.simulate import Simulator                             # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SERIOUS = ("HIGH", "CRITICAL")


def make_folds(kit, seed: int):
    """3 folds of 9 missions: 6 V1 + 3 V2 each, dealt in order of serious-anomaly count."""
    rng = random.Random(seed)
    folds = [[], [], []]
    for cfg in ("V1", "V2"):
        ms = [m for m in kit.missions.values() if m["configuration_version"] == cfg]
        rng.shuffle(ms)
        ms.sort(key=lambda m: -sum(1 for a in kit.actions_of(m["mission_id"])
                                   if kit.anomalies.get(a["action_id"], {}).get("severity") in SERIOUS))
        for i, m in enumerate(ms):
            folds[i % 3].append(m["mission_id"])
    return [sorted(f) for f in folds]


def events_for(missions, kit, source):
    """missions: list of (mission, actions, readings, anomalies)."""
    out = []
    for mission, actions, readings, anomalies in missions:
        out.extend(mission_events(mission, actions, kit.locations, kit.assets, readings, anomalies, source))
    return out


def kit_missions(kit, ids):
    return [(kit.missions[m], kit.actions_of(m), kit.readings, kit.anomalies) for m in ids]


def labelled(events):
    """Attach labels. pre_action events take their label from the matching real outcome event."""
    outcome = {e["action_id"]: e for e in events if e["kind"] == "action"}
    for e in events:
        e["labels"] = label(e, outcome.get(e.get("action_id")) if e["kind"] == "pre_action" else None)
    return events


def features(e):
    """Structured features for the classic (non-Laya) baselines on Track A."""
    if e["kind"] != "pre_action":
        return None
    m = e["mission_so_far"]
    return {"action_type": e["action_type"], "environment": e["location"]["environment"],
            "zone_type": e["location"]["zone_type"], "location_id": e["location"]["location_id"],
            "asset_type": e["asset"]["asset_type"], "criticality": e["asset"]["criticality"],
            "configuration_version": e["configuration_version"], "battery_pct": e["battery_pct"],
            "sequence": e["sequence"], "failures_so_far": m["failures_so_far"],
            "last_failed": int(m["last_status"] == "FAILED")}


def to_rows(events, segment, renderings, rng):
    rows = []
    for e in events:
        for how in renderings(rng):
            rows.append({
                "id": "%s:%s:%s" % (segment, e["event_id"], how),
                "state": render(e, how, rng),
                "questions": questions_for(e["kind"]),
                "expected": {q: e["labels"][q] for q in QUESTION_SETS[e["kind"]]},
                "meta": {"track": TRACK[e["kind"]], "segment": segment, "source": e["source"],
                         "rendering": how, "kind": e["kind"], "mission_id": e["mission_id"],
                         "event_id": e["event_id"], "features": features(e)},
            })
    return rows


ALL = lambda rng: list(RENDERINGS)                      # noqa: E731
ONE = lambda rng: [rng.choice(RENDERINGS)]              # noqa: E731


def counterfactuals(events, rng, n_max):
    """Minimal one-field edits of action events that change the policy's priority or escalation."""
    edits = [
        ("battery_critical", lambda e: e.__setitem__("battery_pct", 14)),
        ("battery_ok", lambda e: e.__setitem__("battery_pct", 72)),
        ("asset_critical", lambda e: e["asset"].__setitem__("criticality", "CRITICAL")),
        ("asset_low", lambda e: e["asset"].__setitem__("criticality", "LOW")),
        ("severity_critical", lambda e: e["anomaly"] and e["anomaly"].__setitem__("severity", "CRITICAL")),
        ("severity_low", lambda e: e["anomaly"] and e["anomaly"].__setitem__("severity", "LOW")),
        ("reading_questionable", lambda e: e["reading"] and e["reading"].__setitem__("quality", "QUESTIONABLE")),
    ]
    out = []
    pool = [e for e in events if e["kind"] == "action"]
    rng.shuffle(pool)
    for e in pool:
        for name, fn in rng.sample(edits, len(edits)):
            c = copy.deepcopy(e)
            fn(c)
            c["labels"] = label(c)
            if (c["labels"]["priority"], c["labels"]["escalate"]) != (e["labels"]["priority"], e["labels"]["escalate"]):
                c["event_id"] = "%s~%s" % (e["event_id"], name)
                c["source"] = e["source"] + "+counterfactual"
                out.append(c)
                break
        if len(out) >= n_max:
            break
    return out


def label_dist(rows):
    d = defaultdict(Counter)
    for r in rows:
        for q, v in r["expected"].items():
            d[q][v] += 1
    return {q: dict(sorted(c.items())) for q, c in sorted(d.items())}


def token_check(rows, max_state_tokens):
    try:
        from transformers import AutoTokenizer
        from laya.common import serialize_state
        from laya.train import resolve_checkpoint_dir
    except ImportError:
        return {"checked": False}
    tok = AutoTokenizer.from_pretrained(str(Path(resolve_checkpoint_dir("convaiinnovations/laya")) / "tokenizer"))
    lens = [len(tok(serialize_state(r["state"]), add_special_tokens=False)["input_ids"]) for r in rows]
    over = sum(1 for n in lens if n > max_state_tokens)
    return {"checked": True, "max": max(lens), "mean": round(sum(lens) / len(lens), 1),
            "over_budget": over, "budget": max_state_tokens}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout-fold", type=int, default=2, choices=[0, 1, 2])
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--synth-train", type=int, default=120, help="synthetic training missions")
    ap.add_argument("--synth-calib", type=int, default=30, help="synthetic calibration missions")
    ap.add_argument("--synth-holdout", type=int, default=40, help="synthetic benchmark missions")
    ap.add_argument("--counterfactuals", type=int, default=150)
    ap.add_argument("--no-token-check", action="store_true")
    args = ap.parse_args()

    kit = load_kit()
    folds = make_folds(kit, args.seed)
    hold_ids = folds[args.holdout_fold]
    train_ids = sorted(m for i, f in enumerate(folds) if i != args.holdout_fold for m in f)

    sim = Simulator(kit, train_ids)
    rng = random.Random(args.seed)
    real_train = labelled(events_for(kit_missions(kit, train_ids), kit, "real"))
    real_hold = labelled(events_for(kit_missions(kit, hold_ids), kit, "real"))
    syn_train = labelled(events_for(sim.missions(args.synth_train, args.seed + 1, "ST"), kit, "synthetic"))
    syn_calib = labelled(events_for(sim.missions(args.synth_calib, args.seed + 2, "SC"), kit, "synthetic"))
    syn_hold = labelled(events_for(sim.missions(args.synth_holdout, args.seed + 3, "SH"), kit, "synthetic"))
    cf = counterfactuals(real_hold + syn_hold, random.Random(args.seed + 4), args.counterfactuals)

    train = to_rows(real_train, "train_real", ALL, rng) + to_rows(syn_train, "train_synthetic", ONE, rng)
    calib = to_rows(syn_calib, "calib_synthetic", ONE, rng)
    bench = (to_rows(real_hold, "real", ALL, rng) + to_rows(syn_hold, "synthetic", ONE, rng)
             + to_rows(cf, "counterfactual", ONE, rng))

    # A benchmark state identical to a training/calibration state would leak; drop it.
    seen = {json.dumps(r["state"], sort_keys=True) for r in train + calib}
    before = len(bench)
    bench = [r for r in bench if json.dumps(r["state"], sort_keys=True) not in seen]
    dropped = before - len(bench)

    DATA.mkdir(exist_ok=True)
    for name, rows in (("train", train), ("calib", calib), ("benchmark", bench)):
        with open(DATA / ("%s.jsonl" % name), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def seg_counts(rows):
        return dict(Counter((r["meta"]["segment"], r["meta"]["track"]) for r in rows).most_common())

    manifest = {
        "policy_version": POLICY_VERSION, "seed": args.seed, "holdout_fold": args.holdout_fold,
        "folds": folds, "holdout_missions": hold_ids, "train_missions": train_ids,
        "synthetic_missions": {"train": args.synth_train, "calib": args.synth_calib, "holdout": args.synth_holdout},
        "rows": {"train": len(train), "calib": len(calib), "benchmark": len(bench)},
        "benchmark_dropped_as_duplicate_of_train": dropped,
        "segments": {k: {"%s/%s" % s: n for s, n in seg_counts(v).items()}
                     for k, v in (("train", train), ("calib", calib), ("benchmark", bench))},
        "label_distribution": {"train": label_dist(train), "benchmark": label_dist(bench),
                               "benchmark_real": label_dist([r for r in bench if r["meta"]["segment"] == "real"])},
        "state_tokens": {} if args.no_token_check else token_check(train + calib + bench, 320),
    }
    with open(DATA / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("folds:", folds)
    print("holdout (real benchmark) missions:", hold_ids)
    print("rows: train %d | calib %d | benchmark %d (dropped %d duplicates)" % (len(train), len(calib), len(bench), dropped))
    print("benchmark segments:", manifest["segments"]["benchmark"])
    print("state tokens:", manifest["state_tokens"])
    for q, d in manifest["label_distribution"]["benchmark_real"].items():
        print("  real-holdout %-18s %s" % (q, d))


if __name__ == "__main__":
    main()
