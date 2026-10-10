"""Fine-tune Laya on the SPOT triage data, running the full benchmark after every epoch.

    python scripts/finetune.py --out checkpoints/run1                 # defaults below
    python scripts/finetune.py --out checkpoints/smoke --epochs 1 --train-limit 200 --bench-limit 120
    python scripts/finetune.py --out checkpoints/run1 --push-to-hub <user>/laya-spot-triage

Built on Laya's own training loop (`laya.train.train_model`, pinned laya==0.4.1), the same code the
official fine-tuning notebook runs, so the result loads with `laya.load(<dir>)`. What this adds:
- after EVERY epoch: refit calibration temperatures on data/calib.jsonl (held-out synthetic missions,
  not a random item split), then run the whole benchmark (data/benchmark.jsonl) and save it to
  <out>/epoch_NN/ (report.md, metrics.json, predictions.jsonl);
- the best epoch (by --select-metric) is saved to <out>/best/, the last one to <out>/final/;
- <out>/training_report.md tracks every metric across epochs (epoch 00 = the untuned model).

Defaults follow research/tech-laya-rocm-finetune-2026-10-10.md: soft-ce loss (Laya #741 found no gain
from the RL term at this scale), option-order shuffling against position bias, eager mode, and at least
~350 optimizer updates. Note: selecting the best epoch on the validation set makes that epoch's score
slightly optimistic; the final-epoch score is reported too.
"""
import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from laya.calibrate import fit_temperature_map                                   # noqa: E402
from laya.common import uses_parallel_layout                                     # noqa: E402
from laya.train import (TrainConfig, calibration_records, items_from_rows,       # noqa: E402
                        load_checkpoint, optimizer_updates, prior_collapse_message, resolve_device,
                        save_checkpoint, train_model, update_budget_message)

from scripts.benchmark import read_jsonl, run_benchmark, stratified_limit        # noqa: E402
from triage.harness import LayaRunner                                            # noqa: E402
from triage.questions import QUESTIONS                                           # noqa: E402

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
    return s


def select(summary: dict, metric: str) -> float:
    if metric == "overall":
        return summary["overall"]["mean_macro_f1"]
    return summary.get(metric, {}).get("mean_macro_f1", float("nan"))


def write_training_report(path: Path, history: list, best_epoch: int, args, budget: str):
    L = ["# Laya fine-tuning report", "", "_%s · base `%s` · %s_" % (time.strftime("%Y-%m-%d %H:%M"), args.base, budget), "",
         "Epoch 00 is the untuned model. Scores are mean macro-F1 over questions (decision accuracy in parentheses).", "",
         "| Epoch | Train loss | Real | Synthetic | Counterfactual | Overall | Escalate recall (real) | Will-fail recall (real) |",
         "|---|---|---|---|---|---|---|---|"]
    for h in history:
        s = h["summary"]

        def cell(seg):
            m = s.get(seg)
            return "%.3f (%.1f%%)" % (m["mean_macro_f1"], 100 * m["decision_accuracy"]) if m else "–"

        def rec(q):
            v = s.get("real", {}).get(q, {}).get("recall")
            return "%.1f%%" % (100 * v) if v is not None and v == v else "–"
        mark = " **best**" if h["epoch"] == best_epoch else ""
        L.append("| %02d%s | %s | %s | %s | %s | %s | %s | %s |" % (
            h["epoch"], mark, "%.4f" % h["loss"] if h["loss"] is not None else "–", cell("real"), cell("synthetic"),
            cell("counterfactual"), cell("overall"), rec("escalate"), rec("will_fail")))
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="convaiinnovations/laya")
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--device", default="auto")
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--micro-batch", type=int, default=8)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--encoder-lr", type=float, default=2e-5)
    ap.add_argument("--head-lr", type=float, default=1e-4)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--loss", default="soft-ce", choices=["soft-ce", "rlcd"])
    ap.add_argument("--label-smoothing", type=float, default=0.05)
    ap.add_argument("--freeze-encoder", action="store_true", help="train the decision head only (fast, weaker)")
    ap.add_argument("--no-amp", action="store_true", help="disable fp16 autocast (use if ROCm gives NaNs)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--train-limit", type=int, default=0, help="use N training rows (smoke test)")
    ap.add_argument("--bench-limit", type=int, default=0, help="stratified N benchmark rows per epoch (faster)")
    ap.add_argument("--calib-limit", type=int, default=0, help="use N calibration rows (smoke test)")
    ap.add_argument("--batch-size", type=int, default=16, help="benchmark inference batch")
    ap.add_argument("--select-metric", default="overall", choices=["overall", "real", "synthetic", "counterfactual"])
    ap.add_argument("--push-to-hub", default=None, help="HF repo id to upload the best checkpoint to")
    args = ap.parse_args()

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
    model.to(dev)
    max_len, head_max_len = cfg.get("max_len", 512), cfg.get("head_max_len", 192)
    parallel = uses_parallel_layout(cfg)
    config = TrainConfig(epochs=args.epochs, micro_batch=args.micro_batch, grad_accum=args.grad_accum,
                         encoder_lr=args.encoder_lr, head_lr=args.head_lr, weight_decay=args.weight_decay,
                         loss=args.loss, label_smoothing=args.label_smoothing, shuffle_options=("choice",),
                         freeze_encoder=args.freeze_encoder, seed=args.seed,
                         amp=False if args.no_amp else None, log_every=50)
    config.validate()

    train_items, skipped = items_from_rows(tok, train_rows, max_len, head_max_len, args.label_smoothing)
    calib_items, cskipped = items_from_rows(tok, calib_rows, max_len, head_max_len, 0.0)
    budget = update_budget_message(len(train_items), config)
    print("device %s | train items %d (skipped %s) | calib items %d (skipped %s) | benchmark rows %d"
          % (dev, len(train_items), skipped, len(calib_items), cskipped, len(bench_rows)), flush=True)
    print(budget, flush=True)
    updates = optimizer_updates(len(train_items), config.micro_batch, config.grad_accum, config.epochs)
    if updates < MIN_UPDATES and not args.train_limit:
        print("WARNING: only %d optimizer updates; small runs can collapse to the class prior (laya #963). "
              "Raise --epochs or lower --grad-accum." % updates, flush=True)

    runner = LayaRunner(model, tok, cfg, dev, name=args.base)
    history, best = [], {"score": float("-inf"), "epoch": None}
    run_meta = {"args": vars(args), "train_config": asdict(config), "budget": budget, "device": str(dev)}
    (out / "run_config.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    def save(path: Path, temps):
        out_cfg = dict(cfg, max_len=max_len, head_max_len=head_max_len, fine_tuned=True,
                       temperature=temps["temperature"])
        out_cfg.pop("temperature_by_options", None)
        if temps.get("temperature_by_options"):
            out_cfg["temperature_by_options"] = temps["temperature_by_options"]
        out_cfg["training"] = dict(out_cfg.get("training") or {}, spot_triage=run_meta)
        save_checkpoint(model, tok, out_cfg, str(path))
        qs = {}
        for r in train_rows:
            qs.update(r["questions"])
        (path / "questions.json").write_text(json.dumps({q: QUESTIONS[q] for q in qs}, indent=2), encoding="utf-8")

    def evaluate(epoch: int, loss):
        t0 = time.time()
        temps = {"temperature": cfg.get("temperature"), "temperature_by_options": cfg.get("temperature_by_options")}
        if epoch > 0:   # refit temperatures for the current weights on the held-out calibration missions
            records = calibration_records(model, tok, calib_items, dev, max_len, head_max_len, parallel=parallel)
            msg = prior_collapse_message(records)
            if msg:
                print("WARNING (epoch %d): %s" % (epoch, msg), flush=True)
            fitted = fit_temperature_map(records)
            temps = {"temperature": fitted["temperature"], "temperature_by_options": fitted["temperature_by_options"]}
            runner.set_temperatures(temps["temperature"], temps["temperature_by_options"])
        rep = run_benchmark(runner, bench_rows, train_rows, out / ("epoch_%02d" % epoch), "%s @ epoch %d" % (args.base, epoch),
                            batch_size=args.batch_size, with_classic=(epoch == 0), quiet=True)
        if config.freeze_encoder:
            model.encoder.eval()   # train_model keeps a frozen encoder in eval mode; runner.logits restored .train()
        s = summarize(rep)
        history.append({"epoch": epoch, "loss": loss, "summary": s, "temperatures": temps,
                        "eval_seconds": round(time.time() - t0, 1)})
        score = select(s, args.select_metric)
        line = "epoch %02d | loss %s | real %.3f | synthetic %.3f | counterfactual %.3f | overall %.3f | eval %.0fs" % (
            epoch, "%.4f" % loss if loss is not None else "  –   ",
            s.get("real", {}).get("mean_macro_f1", float("nan")), s.get("synthetic", {}).get("mean_macro_f1", float("nan")),
            s.get("counterfactual", {}).get("mean_macro_f1", float("nan")), s["overall"]["mean_macro_f1"], time.time() - t0)
        if epoch > 0 and score > best["score"]:
            best.update(score=score, epoch=epoch)
            save(out / "best", temps)
            line += "  <- best, saved"
        print(line, flush=True)
        (out / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
        write_training_report(out / "training_report.md", history, best["epoch"], args, budget)
        return temps

    print("benchmarking the untuned model (epoch 00)...", flush=True)
    evaluate(0, None)
    last = {}

    def on_epoch_end(epoch_idx: int, mean_loss: float):
        last["temps"] = evaluate(epoch_idx + 1, mean_loss)

    t0 = time.time()
    train_model(model, tok, train_items, config, dev, max_len, head_max_len, on_epoch_end=on_epoch_end, parallel=parallel)
    save(out / "final", last["temps"])
    print("training done in %.1f min; best epoch %s (%s = %.3f)" % ((time.time() - t0) / 60, best["epoch"],
                                                                    args.select_metric, best["score"]), flush=True)
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
