"""Compare fine-tuning runs side by side (e.g. full fine-tune vs LoRA vs continued training).

    python scripts/compare_runs.py checkpoints/run2 checkpoints/run3_full checkpoints/run3_lora
    python scripts/compare_runs.py checkpoints/*/ --out results/run_comparison.md

Reads each run's history.json + run_config.json and reports the untuned score, the best epoch and the last
epoch (mean macro-F1 over questions per benchmark segment). The best epoch is chosen on the validation set,
so it is slightly optimistic; the last-epoch column is the unselected number.
"""
import argparse
import json
from pathlib import Path


def strategy(cfg: dict) -> str:
    a = cfg.get("args", {})
    if a.get("lora"):
        kind = "LoRA r=%s" % a.get("lora_r")
    elif a.get("freeze_encoder"):
        kind = "head only"
    else:
        kind = "full FT"
    bits = [kind, "enc lr %g" % a.get("encoder_lr", 0)]
    if a.get("llrd") not in (None, 1.0):
        bits.append("llrd %g" % a["llrd"])
    if a.get("oversample"):
        bits.append("oversample")
    if a.get("base", "convaiinnovations/laya") != "convaiinnovations/laya":
        bits.append("from %s" % Path(a["base"]).parent.name or a["base"])
    return ", ".join(bits)


def seg(h: dict, name: str) -> str:
    m = h["summary"].get(name)
    return "%.3f" % m["mean_macro_f1"] if m else "–"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--metric", default="real", choices=["real", "synthetic", "counterfactual", "overall"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    L = ["| Run | Strategy | Epochs | Untuned %s | Best %s (epoch) | Last %s | Best: real / synthetic / counterfactual / overall | Will-fail recall (real, best) |"
         % ((args.metric,) * 3), "|---|---|---|---|---|---|---|---|"]
    for r in args.runs:
        d = Path(r)
        if not (d / "history.json").exists():
            continue
        hist = json.loads((d / "history.json").read_text())
        cfg = json.loads((d / "run_config.json").read_text()) if (d / "run_config.json").exists() else {}
        trained = [h for h in hist if h["epoch"] > 0]
        if not trained:
            continue
        score = lambda h: h["summary"].get(args.metric, {}).get("mean_macro_f1", float("-inf"))
        best, last = max(trained, key=score), trained[-1]
        wf = best["summary"].get("real", {}).get("will_fail", {}).get("recall")
        L.append("| %s | %s | %d | %s | %s (%02d) | %s | %s / %s / %s / %s | %s |" % (
            d.name, strategy(cfg), len(trained), seg(hist[0], args.metric), seg(best, args.metric), best["epoch"],
            seg(last, args.metric), seg(best, "real"), seg(best, "synthetic"), seg(best, "counterfactual"),
            seg(best, "overall"), "%.1f%%" % (100 * wf) if wf is not None and wf == wf else "–"))
    text = "\n".join(L) + "\n"
    print(text)
    if args.out:
        Path(args.out).write_text("# Fine-tuning runs compared\n\n" + text, encoding="utf-8")


if __name__ == "__main__":
    main()
