"""Fine-tune Laya on the SPOT triage data, running the full benchmark after every epoch.

    python scripts/finetune.py --out checkpoints/run1                 # defaults below
    python scripts/finetune.py --out checkpoints/smoke --epochs 1 --train-limit 200 --bench-limit 120
    python scripts/finetune.py --out checkpoints/run1 --push-to-hub <user>/laya-spot-triage

Training runs in triage/trainer.py: Laya's own batches and losses (pinned laya==0.4.1) with warmup,
layer-wise LR decay, optional LoRA (Hugging Face PEFT), class rebalancing, early stopping and a time
budget. Checkpoints load with `laya.load(<dir>)` (LoRA is merged in). What this script adds:
- after EVERY epoch: refit calibration temperatures on data/calib.jsonl (held-out synthetic missions,
  not a random item split), fit per-question decision thresholds for the yes/no questions on the same
  missions, log the calibration cross-entropy (unsmoothed, so comparable across runs, unlike train loss),
  then run the whole benchmark (data/benchmark.jsonl) and save it to <out>/epoch_NN/ (report.md,
  metrics.json, predictions.jsonl);
- the best epoch (by --select-metric) is saved to <out>/best/, the last one to <out>/final/;
- <out>/training_report.md tracks every metric across epochs (epoch 00 = the untuned model).

Defaults follow research/tech-laya-rocm-finetune-2026-10-10.md: soft-ce loss (Laya #741 found no gain
from the RL term at this scale), option-order shuffling against position bias, eager mode, and at least
~350 optimizer updates. Note: selecting the best epoch on the validation set makes that epoch's score
slightly optimistic; the final-epoch score is reported too.
"""
import argparse
import json
import math
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from laya.calibrate import fit_temperature_map                                   # noqa: E402
from laya.common import uses_parallel_layout                                     # noqa: E402
from laya.train import load_checkpoint, prior_collapse_message, resolve_device  # noqa: E402

from scripts.benchmark import read_jsonl, run_benchmark, stratified_limit        # noqa: E402
from triage.metrics import score as question_scores                              # noqa: E402
from triage.harness import LayaRunner, fit_thresholds                            # noqa: E402
from triage.questions import POSITIVE, QUESTIONS                                 # noqa: E402
from triage.trainer import (LoopConfig, apply_lora, items_with_qids,             # noqa: E402
                            oversample_positives, save_laya, train_loop)
import numpy as np                                                               # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MIN_UPDATES = 350


def summarize(rep: dict) -> dict:
    s = {}
    for seg, m in rep["by_segment"].items():
        s[seg] = {"mean_macro_f1": m["_all"]["mean_question_macro_f1"], "decision_accuracy": m["_all"]["decision_accuracy"]}
        for q, v in m.items():
            if q != "_all":
                s[seg][q] = {"macro_f1": v["macro_f1"], "accuracy": v["accuracy"]}
                if "recall" in v:
                    s[seg][q]["recall"] = v["recall"]
    s["overall"] = {"mean_macro_f1": rep["overall"]["_all"]["mean_question_macro_f1"],
                    "decision_accuracy": rep["overall"]["_all"]["decision_accuracy"],
                    "ece": {q: v.get("ece") for q, v in rep["overall"].items() if q != "_all"}}
    if rep.get("argmax"):   # the same answers without decision thresholds (comparable with older runs)
        s["argmax"] = {seg: {"mean_macro_f1": m["_all"]["mean_question_macro_f1"],
                             **{q: {"macro_f1": v["macro_f1"], "recall": v.get("recall")} for q, v in m.items()
                                if q != "_all"}}
                       for seg, m in rep["argmax"]["by_segment"].items()}
        s["decision_thresholds"] = rep["decision_thresholds"]
    return s


def select(summary: dict, metric: str) -> float:
    if metric == "calib-ce":       # lower is better; calibration missions, not the benchmark
        return -summary.get("calib", {}).get("ce", float("inf"))
    if metric == "overall":
        return summary["overall"]["mean_macro_f1"]
    return summary.get(metric, {}).get("mean_macro_f1", float("nan"))


def strategy_line(args) -> str:
    if args.lora:
        lora = "LoRA r=%d alpha=%d dropout %g on %s, lora lr %g" % (
            args.lora_r, args.lora_alpha, args.lora_dropout, args.lora_targets, args.lora_lr)
        if args.loraplus_ratio != 1:
            lora += ", LoRA+ x%g" % args.loraplus_ratio
        if args.lora_init != "default":
            lora += ", init %s" % args.lora_init
        lora += ", norms %s (lr %g, llrd %g)" % ("trained" if not args.no_lora_norms else "frozen",
                                                 args.encoder_lr, args.llrd)
        parts = [lora, "head lr %g" % args.head_lr]
    else:
        parts = ["frozen encoder" if args.freeze_encoder else "full fine-tune",
                 "enc lr %g, head lr %g" % (args.encoder_lr, args.head_lr), "llrd %g" % args.llrd]
    parts += ["warmup %g" % args.warmup_ratio, "%s schedule" % args.schedule, "weight decay %g" % args.weight_decay,
              "loss %s" % args.loss, "label smoothing %g" % args.label_smoothing]
    if args.oversample:
        parts.append("oversample %s" % args.oversample)
    if args.patience:
        parts.append("patience %d" % args.patience)
    if args.max_minutes:
        parts.append("budget %g min" % args.max_minutes)
    if args.no_thresholds:
        parts.append("no decision thresholds")
    parts.append("select %s" % args.select_metric)
    return ", ".join(parts)


def write_training_report(path: Path, history: list, best_epoch: int, args, budget: str):
    L = ["# Laya fine-tuning report", "", "_%s · base `%s` · %s_" % (time.strftime("%Y-%m-%d %H:%M"), args.base, budget), "",
         "**Strategy:** %s" % strategy_line(args), "",
         "Epoch 00 is the untuned model. Scores are mean macro-F1 over questions (decision accuracy in parentheses), "
         "with the decision thresholds fitted on the calibration missions. **Real (argmax)** is the same without them, "
         "comparable with runs that had none. **Calib CE** is unsmoothed cross-entropy on the calibration missions: "
         "compare runs on it and on held-out F1, never on train loss (label smoothing alone floors it at ~0.16).", "",
         "| Epoch | Train loss | Calib CE | Real | Real (argmax) | Synthetic | Counterfactual | Overall | Escalate recall (real) | Will-fail recall (real) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for h in history:
        s = h["summary"]

        def cell(seg):
            m = s.get(seg)
            return "%.3f (%.1f%%)" % (m["mean_macro_f1"], 100 * m["decision_accuracy"]) if m else "–"

        def rec(q):
            v = s.get("real", {}).get(q, {}).get("recall")
            return "%.1f%%" % (100 * v) if v is not None and v == v else "–"
        mark = (" **best**" if h["epoch"] == best_epoch else "") + (" (partial)" if h.get("partial") else "")
        ce = s.get("calib", {}).get("ce")
        am = s.get("argmax", {}).get("real", {}).get("mean_macro_f1")
        L.append("| %02d%s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            h["epoch"], mark, "%.4f" % h["loss"] if h["loss"] is not None else "–",
            "%.4f" % ce if ce is not None else "–", cell("real"), "%.3f" % am if am is not None else "same",
            cell("synthetic"), cell("counterfactual"), cell("overall"), rec("escalate"), rec("will_fail")))
    L += ["", "Per-epoch details: `epoch_NN/report.md`. Best checkpoint: `best/`; last epoch: `final/`."]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def model_card(repo_id: str, base: str, history: list, best_epoch: int) -> str:
    best = next(h for h in history if h["epoch"] == best_epoch)["summary"]
    base_s = history[0]["summary"]
    rows = []
    for seg in ("real", "synthetic", "counterfactual"):
        if seg in best:
            rows.append("| %s | %.3f | %.3f |" % (seg, base_s[seg]["mean_macro_f1"], best[seg]["mean_macro_f1"]))
    return "\n".join([
        "---", "license: apache-2.0", "library_name: laya", "base_model: %s" % base, "pipeline_tag: text-classification",
        "tags: [laya, system-one, rlcd, robotics, boston-dynamics-spot, industrial-inspection, triage]", "---", "",
        "# %s" % repo_id.split("/")[-1], "",
        "Laya fine-tuned as the **System 1 triage model** for Boston Dynamics SPOT inspection data (Knight Hacks IX,",
        "NextEra SPOT challenge). It answers typed questions about each robot event in one forward pass:",
        "will the next action fail, how, will it raise an anomaly (real outcomes), and should a finished action or",
        "mission be escalated, at what priority, for what reason, and can its reading be trusted (operator-triage policy).", "",
        "## Benchmark (mean macro-F1 over questions, held-out missions)", "",
        "| Segment | Base Laya | This model |", "|---|---|---|", *rows, "",
        "Real = held-out kit missions; synthetic = held-out simulated missions; counterfactual = one-field edits.",
        "Data is synthetic and fictional (NextEra challenge kit). Usage: `laya.load(\"%s\")` with the questions in `questions.json`." % repo_id,
    ]) + "\n"


def parse_oversample(spec: str) -> dict:
    """'will_fail=2,anomaly_expected=1.5' -> {'will_fail': 2.0, 'anomaly_expected': 1.5}"""
    out = {}
    for part in filter(None, (p.strip() for p in (spec or "").split(","))):
        q, f = part.split("=")
        if q not in POSITIVE:
            raise SystemExit("--oversample: %r is not a yes/no question (%s)" % (q, ", ".join(POSITIVE)))
        out[q] = float(f)
    return out


def main():
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--base", default="convaiinnovations/laya",
                    help="HF id or a local checkpoint dir (e.g. checkpoints/run2/best to continue training)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--device", default="auto")
    g = ap.add_argument_group("schedule")
    g.add_argument("--epochs", type=int, default=6)
    g.add_argument("--micro-batch", type=int, default=8)
    g.add_argument("--grad-accum", type=int, default=4)
    g.add_argument("--encoder-lr", type=float, default=2e-5,
                   help="peak LR of the TOP encoder layer (full fine-tune); with --lora, the LR of the LayerNorms")
    g.add_argument("--head-lr", type=float, default=1e-4)
    g.add_argument("--warmup-ratio", type=float, default=0.06, help="fraction of updates spent warming up")
    g.add_argument("--schedule", default="cosine", choices=["cosine", "linear", "constant"])
    g.add_argument("--min-lr-ratio", type=float, default=0.05, help="LR floor as a fraction of peak")
    g.add_argument("--llrd", type=float, default=0.95, help="layer-wise LR decay (1.0 = off)")
    g.add_argument("--weight-decay", type=float, default=0.01)
    g.add_argument("--max-minutes", type=float, default=0, help="wall-clock budget for the whole run (0 = none)")
    g.add_argument("--patience", type=int, default=0, help="stop after N evals without improvement (0 = off)")
    g = ap.add_argument_group("objective / data")
    g.add_argument("--loss", default="soft-ce", choices=["soft-ce", "rlcd"])
    g.add_argument("--label-smoothing", type=float, default=0.05)
    g.add_argument("--oversample", default="", help="repeat positives of yes/no questions, e.g. will_fail=2,anomaly_expected=2")
    g = ap.add_argument_group("parameter-efficient / regularisation")
    g.add_argument("--lora", action="store_true", help="LoRA adapters on the encoder (Hugging Face PEFT); head trains fully")
    g.add_argument("--lora-r", type=int, default=16)
    g.add_argument("--lora-alpha", type=int, default=32)
    g.add_argument("--lora-dropout", type=float, default=0.0, help="0 matches ModernBERT's own (zero) dropout")
    g.add_argument("--lora-targets", default="Wqkv,Wo,Wi", help="Wo matches both attn.Wo and mlp.Wo")
    g.add_argument("--lora-lr", type=float, default=2e-4,
                   help="adapter LR, flat across layers (~10x the full fine-tune LR; --llrd does not apply)")
    g.add_argument("--loraplus-ratio", type=float, default=1.0, help="LoRA+: lora_B LR = lora lr x ratio (try 8-16)")
    g.add_argument("--lora-init", default="default",
                   help="default (B=0) or a PEFT init: pissa_niter_16, olora, ... (pissa: lower --lora-lr to ~5e-5)")
    g.add_argument("--no-lora-norms", action="store_true", help="keep the encoder LayerNorms frozen under LoRA")
    g.add_argument("--freeze-encoder", action="store_true", help="train the decision head only (fast, weaker)")
    g.add_argument("--grad-checkpointing", action="store_true", help="less memory, ~30%% slower")
    g = ap.add_argument_group("runtime")
    g.add_argument("--no-amp", action="store_true", help="fp32 in training AND benchmarking (NaNs or GEMM errors)")
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("--train-limit", type=int, default=0, help="use N training rows (smoke test)")
    g.add_argument("--bench-limit", type=int, default=0, help="stratified N benchmark rows per epoch (faster)")
    g.add_argument("--calib-limit", type=int, default=0, help="use N calibration rows (smoke test)")
    g.add_argument("--batch-size", type=int, default=16, help="benchmark inference batch")
    g.add_argument("--select-metric", default="overall",
                   choices=["overall", "real", "synthetic", "counterfactual", "calib-ce"],
                   help="calib-ce selects on the calibration missions, so the benchmark stays an unselected test")
    g.add_argument("--no-thresholds", action="store_true",
                   help="don't fit per-question decision thresholds on the calibration missions (plain argmax)")
    g.add_argument("--push-to-hub", default=None, help="HF repo id to upload the best checkpoint to")
    args = ap.parse_args()
    if args.lora and args.freeze_encoder:
        raise SystemExit("--lora and --freeze-encoder are mutually exclusive")
    t_start = time.time()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data = Path(args.data_dir)
    train_rows, calib_rows = read_jsonl(data / "train.jsonl"), read_jsonl(data / "calib.jsonl")
    bench_rows = read_jsonl(data / "benchmark.jsonl")
    if args.train_limit:
        train_rows = stratified_limit(train_rows, args.train_limit, seed=args.seed)
    if args.bench_limit:
        bench_rows = stratified_limit(bench_rows, args.bench_limit)
    if args.calib_limit:
        calib_rows = stratified_limit(calib_rows, args.calib_limit, seed=args.seed)

    dev = resolve_device(args.device)
    model, tok, cfg = load_checkpoint(args.base)
    if args.lora:
        apply_lora(model, args.lora_r, args.lora_alpha, args.lora_dropout, args.lora_targets.split(","),
                   init=args.lora_init, train_norms=not args.no_lora_norms)
    model.to(dev)
    runner = LayaRunner(model, tok, cfg, dev, name=args.base, amp=False if args.no_amp else None)
    max_len, head_max_len = cfg.get("max_len", 512), cfg.get("head_max_len", 192)
    parallel = uses_parallel_layout(cfg)
    loop_cfg = LoopConfig(epochs=args.epochs, micro_batch=args.micro_batch, grad_accum=args.grad_accum,
                          encoder_lr=args.encoder_lr, head_lr=args.head_lr, lora_lr=args.lora_lr,
                          loraplus_ratio=args.loraplus_ratio, warmup_ratio=args.warmup_ratio,
                          schedule=args.schedule, min_lr_ratio=args.min_lr_ratio, llrd=args.llrd,
                          weight_decay=args.weight_decay, loss=args.loss, freeze_encoder=args.freeze_encoder,
                          amp=not args.no_amp, grad_checkpointing=args.grad_checkpointing, seed=args.seed)
    loop_cfg.validate()

    train_items, skipped = items_with_qids(tok, train_rows, max_len, head_max_len, args.label_smoothing)
    added = {}
    if args.oversample:
        train_items, added = oversample_positives(train_items, parse_oversample(args.oversample), POSITIVE, args.seed)
    calib_items, calib_metas, cskipped = runner.build_items(calib_rows)
    updates = math.ceil(math.ceil(len(train_items) / args.micro_batch) / args.grad_accum) * args.epochs
    budget = "%d train items%s, effective batch %d, %d optimizer updates over %d epoch(s)" % (
        len(train_items), (" (+%s oversampled)" % added) if added else "", args.micro_batch * args.grad_accum,
        updates, args.epochs)
    print("device %s | train items %d (skipped %s) | calib items %d (skipped %s) | benchmark rows %d"
          % (dev, len(train_items), skipped, len(calib_items), cskipped, len(bench_rows)), flush=True)
    print("strategy: %s" % strategy_line(args), flush=True)
    print(budget, flush=True)
    if updates < MIN_UPDATES and not args.train_limit:
        print("WARNING: only %d optimizer updates; small runs can collapse to the class prior (laya #963). "
              "Raise --epochs or lower --grad-accum." % updates, flush=True)

    history, best = [], {"score": float("-inf"), "epoch": None, "stale": 0}
    run_meta = {"args": vars(args), "loop_config": asdict(loop_cfg), "budget": budget, "device": str(dev)}
    (out / "run_config.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    def save(path: Path, temps):
        out_cfg = dict(cfg, max_len=max_len, head_max_len=head_max_len, fine_tuned=True,
                       temperature=temps["temperature"])
        out_cfg.pop("temperature_by_options", None)
        if temps.get("temperature_by_options"):
            out_cfg["temperature_by_options"] = temps["temperature_by_options"]
        out_cfg.pop("decision_thresholds", None)
        if temps.get("decision_thresholds"):
            out_cfg["decision_thresholds"] = temps["decision_thresholds"]
        out_cfg["training"] = dict(out_cfg.get("training") or {}, spot_triage=run_meta)
        save_laya(model, tok, out_cfg, str(path))
        qs = {}
        for r in train_rows:
            qs.update(r["questions"])
        (path / "questions.json").write_text(json.dumps({q: QUESTIONS[q] for q in qs}, indent=2), encoding="utf-8")

    def evaluate(epoch: int, loss, partial: bool = False):
        t0 = time.time()
        temps = {"temperature": cfg.get("temperature"), "temperature_by_options": cfg.get("temperature_by_options"),
                 "decision_thresholds": cfg.get("decision_thresholds")}
        # same (qtype, logits, target, k) records as laya's calibration_records, but through the benchmark
        # harness: fp16 + the benchmark batch size, ~3x faster on GPU and identical to how inference runs
        lgs = runner.logits(calib_items, args.batch_size)
        if epoch > 0:   # refit temperatures and thresholds for the current weights on the calibration missions
            records = [(it["qtype"], lg, it["target"], it["k"]) for it, lg in zip(calib_items, lgs)]
            msg = prior_collapse_message(records)
            if msg:
                print("WARNING (epoch %d): %s" % (epoch, msg), flush=True)
            fitted = fit_temperature_map(records)
            temps = {"temperature": fitted["temperature"], "temperature_by_options": fitted["temperature_by_options"]}
            runner.set_temperatures(temps["temperature"], temps["temperature_by_options"])
            thr = {} if args.no_thresholds else fit_thresholds(runner.decide(calib_items, calib_metas, lgs, thresholds=False))
            runner.set_thresholds(thr)
            temps["decision_thresholds"] = thr
        cpreds = runner.decide(calib_items, calib_metas, lgs)
        calib = {"ce": float(np.mean([-np.log(max(p["probs"][p["gold"]], 1e-12)) for p in cpreds])),
                 "mean_macro_f1": question_scores(cpreds)["_all"]["mean_question_macro_f1"]}
        rep = run_benchmark(runner, bench_rows, train_rows, out / ("epoch_%02d" % epoch), "%s @ epoch %d" % (args.base, epoch),
                            batch_size=args.batch_size, with_classic=(epoch == 0), quiet=True)
        s = summarize(rep)
        s["calib"] = calib
        history.append({"epoch": epoch, "loss": loss, "partial": partial, "summary": s, "temperatures": temps,
                        "eval_seconds": round(time.time() - t0, 1), "elapsed_min": round((time.time() - t_start) / 60, 1)})
        score = select(s, args.select_metric)
        line = "epoch %02d | loss %s | calib ce %.4f | real %.3f | synthetic %.3f | counterfactual %.3f | overall %.3f | eval %.0fs | %.1f min" % (
            epoch, "%.4f" % loss if loss is not None else "  –   ", calib["ce"],
            s.get("real", {}).get("mean_macro_f1", float("nan")), s.get("synthetic", {}).get("mean_macro_f1", float("nan")),
            s.get("counterfactual", {}).get("mean_macro_f1", float("nan")), s["overall"]["mean_macro_f1"],
            time.time() - t0, (time.time() - t_start) / 60)
        improved = epoch > 0 and score > best["score"]
        if improved:
            best.update(score=score, epoch=epoch, stale=0)
            save(out / "best", temps)
            line += "  <- best, saved"
        elif epoch > 0:
            best["stale"] += 1
        print(line, flush=True)
        if temps.get("decision_thresholds"):
            print("         decision thresholds %s | real without them %.3f" % (
                temps["decision_thresholds"], s.get("argmax", {}).get("real", {}).get("mean_macro_f1", float("nan"))),
                flush=True)
        (out / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
        write_training_report(out / "training_report.md", history, best["epoch"], args, budget)
        return temps

    print("benchmarking the untuned model (epoch 00)...", flush=True)
    evaluate(0, None)
    last = {}

    def on_epoch_end(epoch_idx: int, mean_loss: float, partial: bool):
        last["temps"] = evaluate(epoch_idx + 1, mean_loss, partial)
        if args.patience and best["stale"] >= args.patience:
            print("early stop: no %s improvement for %d eval(s)" % (args.select_metric, best["stale"]), flush=True)
            return False
        return True

    deadline, eval_s = None, 0.0
    if args.max_minutes:
        eval_s = history[0]["eval_seconds"] * 1.1 + 15        # epoch 00 already scores the calibration items
        deadline = t_start + args.max_minutes * 60 - 45          # leave time to save final/
    t0 = time.time()
    train_loop(model, tok, train_items, loop_cfg, dev, max_len, head_max_len, parallel,
               on_epoch_end=on_epoch_end, deadline=deadline, eval_seconds=eval_s)
    save(out / "final", last.get("temps") or {"temperature": cfg.get("temperature")})
    print("training done in %.1f min (run total %.1f min); best epoch %s (%s = %.3f)" % (
        (time.time() - t0) / 60, (time.time() - t_start) / 60, best["epoch"], args.select_metric, best["score"]), flush=True)
    print((out / "training_report.md").read_text(encoding="utf-8"))

    if args.push_to_hub and best["epoch"] is not None:
        from huggingface_hub import HfApi
        (out / "best" / "README.md").write_text(model_card(args.push_to_hub, args.base, history, best["epoch"]), encoding="utf-8")
        for name in ("training_report.md",):
            (out / "best" / name).write_text((out / name).read_text(encoding="utf-8"), encoding="utf-8")
        api = HfApi()
        api.create_repo(args.push_to_hub, exist_ok=True)
        api.upload_folder(folder_path=str(out / "best"), repo_id=args.push_to_hub)
        print("pushed best checkpoint to https://huggingface.co/%s" % args.push_to_hub, flush=True)


if __name__ == "__main__":
    main()
