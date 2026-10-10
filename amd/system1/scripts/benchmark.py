"""Run the SPOT triage benchmark (validation set) on a Laya checkpoint.

    python scripts/benchmark.py --model convaiinnovations/laya --out results/baseline_laya
    python scripts/benchmark.py --model checkpoints/run1/best --out results/run1_best
    python scripts/benchmark.py --limit 60 --out results/smoke     # quick check

Writes metrics.json, predictions.jsonl and report.md to --out. Also scores the majority-class and
classic baselines (logistic regression, gradient boosting) on Track A for comparison.
"""
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")   # eager mode on ROCm/MPS (tech-laya-rocm-finetune)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from triage import baselines                                   # noqa: E402
from triage.harness import LayaRunner, parity_check            # noqa: E402
from triage.metrics import full_report, majority_from_rows     # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
QUESTION_ORDER = ["will_fail", "failure_mode", "anomaly_expected", "escalate", "priority", "category",
                  "reading_trust", "mission_misleading"]


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def stratified_limit(rows, n, seed=0):
    """A small sample that keeps every segment and track represented."""
    rng = random.Random(seed)
    groups = {}
    for r in rows:
        groups.setdefault((r["meta"]["segment"], r["meta"]["track"]), []).append(r)
    per = max(1, n // len(groups))
    out = []
    for g in groups.values():
        out.extend(rng.sample(g, min(per, len(g))))
    return out


def _f(v, pct=False):
    if v is None or v != v:
        return "–"
    return ("%.1f%%" % (100 * v)) if pct else ("%.3f" % v)


def _ci(ci):
    return "" if not ci else " [%.2f–%.2f]" % tuple(ci)


def write_report(path: Path, name: str, rep: dict, classic: dict, speed: dict, meta: dict):
    L = ["# Benchmark: %s" % name, "",
         "_%s · %d decisions over %d rows · %.1f rows/s on %s_" % (
             time.strftime("%Y-%m-%d %H:%M"), rep["overall"]["_all"]["n"], meta["rows"], speed["rows_per_sec"],
             meta["device"]), "",
         "Segments: **real** = held-out kit missions (headline), **synthetic** = held-out simulated missions, "
         "**counterfactual** = one-field edits that flip the triage label (Track B robustness).", "",
         "## Per question (macro-F1, accuracy in parentheses)", "",
         "| Question | Track | Real | Synthetic | Counterfactual | Majority (real) | Real 95% CI |",
         "|---|---|---|---|---|---|---|"]
    seg = rep["by_segment"]
    for q in QUESTION_ORDER:
        if q not in rep["overall"]:
            continue
        track = "A predict" if q in baselines.TRACK_A else "B triage"
        cells = []
        for s in ("real", "synthetic", "counterfactual"):
            m = seg.get(s, {}).get(q)
            cells.append("%s (%s)" % (_f(m["macro_f1"]), _f(m["accuracy"], True)) if m else "–")
        mr = seg.get("real", {}).get(q, {})
        maj = "%s (%s)" % (_f(mr.get("majority_macro_f1")), _f(mr.get("majority_accuracy"), True)) if mr else "–"
        ci = _ci(rep.get("ci_real", {}).get(q, {}).get("macro_f1"))
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (q, track, *cells, maj, ci))
    L += ["", "## Positive-class recall / precision (real segment)", "",
          "| Question | Recall | Precision | Recall 95% CI |", "|---|---|---|---|"]
    for q in QUESTION_ORDER:
        m = seg.get("real", {}).get(q)
        if m and "recall" in m:
            L.append("| %s | %s | %s | %s |" % (q, _f(m["recall"], True), _f(m["precision"], True),
                                                 _ci(rep.get("ci_real", {}).get(q, {}).get("recall"))))
    L += ["", "## Calibration (all segments)", "", "| Question | ECE | Brier | Mean confidence |", "|---|---|---|---|"]
    for q in QUESTION_ORDER:
        m = rep["overall"].get(q)
        if m and "ece" in m:
            L.append("| %s | %s | %s | %s |" % (q, _f(m["ece"]), _f(m["brier"]), _f(m["mean_confidence"])))
    L += ["", "## Robustness by rendering (mean macro-F1 over questions)", "", "| Rendering | Mean macro-F1 | Decision accuracy |",
          "|---|---|---|"]
    for r, m in rep["by_rendering"].items():
        L.append("| %s | %s | %s |" % (r, _f(m["_all"]["mean_question_macro_f1"]), _f(m["_all"]["decision_accuracy"], True)))
    if classic:
        L += ["", "## Track A vs classic baselines (real segment, macro-F1 / accuracy)", "",
              "| Question | Laya (this model) | Logistic regression | Gradient boosting | Majority |", "|---|---|---|---|---|"]
        for q in baselines.TRACK_A:
            row = [q]
            m = seg.get("real", {}).get(q)
            row.append("%s / %s" % (_f(m["macro_f1"]), _f(m["accuracy"], True)) if m else "–")
            for name in ("logreg", "hgb"):
                c = classic[name]["by_segment"].get("real", {}).get(q)
                row.append("%s / %s" % (_f(c["macro_f1"]), _f(c["accuracy"], True)) if c else "–")
            row.append("%s / %s" % (_f(m.get("majority_macro_f1")), _f(m.get("majority_accuracy"), True)) if m else "–")
            L.append("| " + " | ".join(row) + " |")
    if meta.get("parity"):
        p = meta["parity"]
        L += ["", "Harness parity with `laya.load(...).predict`: %.1f%% agreement on %d decisions." % (
            100 * p["agreement"], p["decisions"])]
    if meta.get("skipped"):
        L += ["", "Skipped items: %s" % meta["skipped"]]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def run_benchmark(runner: LayaRunner, bench_rows, train_rows, out_dir: Path, name: str, batch_size=16,
                  with_classic=True, with_ci=True, parity_rows=0, model_path=None, quiet=False):
    """Score `runner` on `bench_rows`; write results to `out_dir`. Returns the report dict."""
    out_dir.mkdir(parents=True, exist_ok=True)
    res = runner.predict(bench_rows, batch_size=batch_size)
    majority = majority_from_rows(train_rows)
    rep = full_report(res["predictions"], majority, with_ci=with_ci)
    classic = {}
    if with_classic:
        for cname, preds in baselines.run(train_rows, bench_rows).items():
            classic[cname] = full_report(preds, majority, with_ci=False)
    meta = {"model": name, "rows": len(bench_rows), "items": res["items"], "device": str(runner.device),
            "skipped": res["skipped"]}
    if parity_rows and model_path:
        sample = random.Random(0).sample(bench_rows, min(parity_rows, len(bench_rows)))
        meta["parity"] = parity_check(model_path, sample, res["predictions"])
    speed = {"seconds": res["seconds"], "rows_per_sec": res["rows_per_sec"], "items_per_sec": res["items_per_sec"]}
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "speed": speed, "laya": rep, "classic": classic}, f, indent=2)
    with open(out_dir / "predictions.jsonl", "w", encoding="utf-8") as f:
        for p in res["predictions"]:
            f.write(json.dumps(p) + "\n")
    write_report(out_dir / "report.md", name, rep, classic, speed, meta)
    if not quiet:
        print((out_dir / "report.md").read_text(encoding="utf-8"))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="convaiinnovations/laya", help="Hub ID or local checkpoint dir")
    ap.add_argument("--data", default=str(ROOT / "data" / "benchmark.jsonl"))
    ap.add_argument("--train", default=str(ROOT / "data" / "train.jsonl"), help="for majority/classic baselines")
    ap.add_argument("--out", default=str(ROOT / "results" / "baseline_laya"))
    ap.add_argument("--device", default="auto")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0, help="stratified sample of N rows (smoke test)")
    ap.add_argument("--parity", type=int, default=25, help="rows to cross-check against laya.load().predict")
    ap.add_argument("--no-classic", action="store_true")
    ap.add_argument("--uncalibrated", action="store_true", help="ignore the checkpoint's temperatures")
    args = ap.parse_args()

    bench, train = read_jsonl(args.data), read_jsonl(args.train)
    if args.limit:
        bench = stratified_limit(bench, args.limit)
    runner = LayaRunner.load(args.model, args.device)
    if args.uncalibrated:
        runner.set_temperatures(None, None)
    print("model %s on %s | %d benchmark rows" % (args.model, runner.device, len(bench)), flush=True)
    run_benchmark(runner, bench, train, Path(args.out), args.model, args.batch_size,
                  with_classic=not args.no_classic, parity_rows=args.parity, model_path=args.model)


if __name__ == "__main__":
    main()
