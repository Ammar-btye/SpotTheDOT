# System 1 "Triage": fine-tuning Laya on SPOT data

[Laya](https://huggingface.co/convaiinnovations/laya) (421M, ModernBERT-large, Apache-2.0) is a non-autoregressive
"System 1" decision model: it reads a **state** plus **typed questions** and returns calibrated probabilities in one
forward pass, so it never generates text and can't hallucinate. Base Laya is near chance zero-shot; its value comes
from fine-tuning. This folder builds the data, benchmarks base Laya, and fine-tunes it on the AMD box with the
benchmark running after every epoch.

## What Laya answers (`triage/questions.py`)
| Track | Event | Questions | Ground truth |
|---|---|---|---|
| **A: Predict** | before an action runs | `will_fail`, `failure_mode`, `anomaly_expected` | **the kit's real outcomes** |
| **B: Triage** | after an action | `escalate`, `priority`, `category`, `reading_trust` | operator-triage policy (`triage/policy.py`) |
| **B: Triage** | after a mission | `escalate`, `priority`, `mission_misleading` | operator-triage policy |

Track A is the honest headline: a job rules *can't* do (forecasting failures from waypoint, environment, battery,
config and mission history), scored against real outcomes and compared with logistic regression and gradient boosting.
Track B labels come from a documented policy (alarm rationalization: consequence × urgency, grounded in
`research/spot-data-insights-2026-10-09.md`). The same policy is the deterministic validator, so Track B measures
how faithfully Laya applies it to text in three renderings and to counterfactual one-field edits.

## Data (`scripts/build_data.py` → `data/`)
- **Splits are by mission.** The 27 kit missions are dealt into 3 folds of 9 (6 V1 + 3 V2), stratified by serious
  anomalies. The holdout fold (default fold 2: M006 M009 M012 M013 M017 M018 M019 M020 M023) is never trained on.
- **Synthetic missions** come from a simulator fitted *only* on the 18 training missions (`triage/simulate.py`):
  ST* train, SC* calibration (temperature fitting), SH* benchmark. Synthetic failure and anomaly rates match the real
  ones (19.9% vs 18.1%, 15.6% vs 14.8%). Edge cases (drift, sensor glitches, low battery) are injected for coverage.
- **Three renderings** of every state: JSON, log line, operator prose (`triage/render.py`). All fit Laya's
  320-token state budget (max 251).
- **The benchmark** (`data/benchmark.jsonl`, 1,557 rows) has three segments, reported separately: `real` (holdout
  missions × 3 renderings, the headline), `synthetic` (SH*), `counterfactual` (one-field edits that flip the triage
  label). Benchmark states that duplicate a training state are dropped.

| file | rows | used for |
|---|---|---|
| `train.jsonl` | 4,254 | fine-tuning (real train missions × 3 renderings + 120 synthetic missions + 600 counterfactual pairs) |
| `calib.jsonl` | 630 | refitting temperatures after each epoch (30 synthetic missions) |
| `benchmark.jsonl` | 1,557 | validation: run before training and after every epoch |

**Training counterfactuals** (`--train-counterfactuals 600`): one-field edits of *training* events (battery,
criticality, severity, reading quality) that flip priority or escalation, each paired with its original so the
trainer batches the two together. Without them the model never saw that a single field flips the label, and
the counterfactual segment lagged (0.60 for LoRA). They use their own RNG, so `calib.jsonl` and
`benchmark.jsonl` are byte-identical with or without them.

Rotate the holdout for cross-validation with `--holdout-fold 0|1|2`.

## Run locally (Mac / CPU)
```bash
cd amd/system1
python3 -m venv .venv && . .venv/bin/activate
pip install torch && pip install -r requirements.txt
python scripts/build_data.py                                   # ~10 s
python scripts/benchmark.py --out results/baseline_laya         # untuned Laya + classic baselines
```

## Run on the AMD Radeon box (gfx1151, ROCm)
```bash
git clone https://github.com/JylerTackson/SpotTheDOT.git && cd SpotTheDOT/amd/system1
python3 -m venv .venv && . .venv/bin/activate
# 1) AMD's gfx1151 PyTorch wheels FIRST (research/tech-amd-rocm-hf-serving-2026-10-09.md)
pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ \
  "torch[device-gfx1151]==2.12.0+rocm7.14.1"
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"   # must show +rocm, True
# 2) the rest. Do NOT install laya[fast] (CUDA-only TileLang path)
pip install -r requirements.txt
python -c "import torch; print(torch.__version__)"   # re-check: still +rocm?

export TORCH_COMPILE_DISABLE=1          # eager mode (the scripts also set this)
python -c "import torch; print(torch.__version__)"   # peft must not have replaced the +rocm torch
mkdir -p checkpoints
# 3) smoke test first (~minutes): 1 epoch on a slice
python scripts/finetune.py --out checkpoints/smoke --epochs 1 --train-limit 300 --bench-limit 150 --calib-limit 100
# 4) the LoRA sweep (research/tech-lora-gap-2026-10-10.md): LoRA at two LRs, a matching full fine-tune,
#    rank 64 and LoRA+, one after another; ~12 epochs x 14 min each. No time budget: LoRA needs the epochs.
nohup bash scripts/sweep_lora.sh > checkpoints/sweep.log 2>&1 &
#    (just the main LoRA run instead: RUNS="A" nohup bash scripts/sweep_lora.sh > checkpoints/sweep.log 2>&1 &)
```
Runs share one GPU, so the script runs them one after the other (never start two at once). If ROCm training produces NaN losses, add `--no-amp`. If the GPU resets mid-run, set `TORCH_BLAS_PREFER_HIPBLASLT=0`
(slower). Watch the GPU with `amd-smi monitor --watch 1`. Upload the best model when you're happy:
`python scripts/finetune.py ... --push-to-hub <user>/laya-spot-triage` (needs `hf auth login`).

## Demo UI (`demo/`)
A minimal FastAPI backend and a one-page frontend that stream SPOT events through Laya and mark each answer
✓/✗ against its expected label.
```bash
pip install -r demo/requirements.txt
python demo/server.py --model checkpoints/run1/best     # or LAYA_MODEL=...; default is untuned base Laya
open http://127.0.0.1:8000
```
1. **Mock feed:** simulated missions from `demo/mock_feed.py` (also runnable alone; prints events as NDJSON).
2. **Challenge-kit CSVs:** upload any of the kit CSVs (the rest come from `data/kit/`) and pick held-out missions,
   all missions or one. Only held-out missions are an honest test.

## Outputs
- `results/baseline_laya/`: untuned Laya on the benchmark (`report.md` is the readable summary).
- `checkpoints/<run>/epoch_NN/`: the full benchmark after each epoch (`epoch_00` = before training).
- `checkpoints/<run>/training_report.md`: every metric across epochs.
- `checkpoints/<run>/best/` and `final/`: load with `laya.load(path)` plus the questions in `questions.json`.

## Training strategies (`triage/trainer.py`, flags on `scripts/finetune.py`)
Training uses Laya's own batches and losses (`laya==0.4.1`) inside our loop, so checkpoints still load with
`laya.load`. Every flag is listed by `python scripts/finetune.py --help`.

| Strategy | Flag (default) | Why |
|---|---|---|
| LR warmup, then cosine decay to a floor | `--warmup-ratio 0.06 --schedule cosine --min-lr-ratio 0.05` | no full-LR shock to the encoder at step 1; smooth landing instead of overshooting |
| Layer-wise LR decay | `--llrd 0.95` | top encoder layer at `--encoder-lr`, each lower layer ×0.95: adapt the task layers, protect pretrained features |
| No weight decay on norms/biases | always on | standard for transformer fine-tuning |
| **LoRA (Hugging Face PEFT)** | `--lora --lora-r 16 --lora-alpha 32 --lora-dropout 0` | adapters on Wqkv, attn.Wo, Wi and mlp.Wo; the head trains fully; merged at save time and also saved as `lora_adapter/` for the Hub |
| LoRA LR, flat across layers | `--lora-lr 2e-4` | LoRA's best LR is ~10× the full fine-tune's in every layer; `--llrd` no longer applies to adapters (0.95²⁷ had left the bottom ones at 1/4 LR) |
| Trainable LayerNorms under LoRA | on (`--no-lora-norms` to freeze) | 58K params incl. `final_norm`, which feeds the head; a full fine-tune trains them. They train at `--encoder-lr` with llrd and land in the merged checkpoint (not in `lora_adapter/`) |
| LoRA+ / PiSSA | `--loraplus-ratio 16`, `--lora-init pissa_niter_16` | optional sweep points: B trains faster than A; SVD init (use `--lora-lr ~5e-5`; no `lora_adapter/` is written since it applies to a residual base) |
| Decision thresholds | on (`--no-thresholds` to disable) | per yes/no question, the threshold on P(yes) that maximises macro-F1 on the calibration missions; saved as `decision_thresholds` and applied by `LayaRunner` (demo, service). Temperatures never change the argmax, so this is what moves rare-positive recall. Reports show "Real (argmax)" too |
| Calibration cross-entropy | always logged; `--select-metric calib-ce` | unsmoothed, so it compares across runs. **Train loss doesn't**: label smoothing 0.05 floors it at ~0.16, and oversampling, dropout and epoch count move it without changing quality |
| Class rebalancing | `--oversample will_fail=2,anomaly_expected=2` | rare "yes" answers (~20%) were collapsing to "no" (will-fail recall 0% in early runs) |
| Early stopping | `--patience 2` | stop after N evals without improvement on `--select-metric` |
| Time budget | `--max-minutes 45` | measures its own speed, fits the epoch count, LR horizon and warmup to the budget, re-plans after every epoch |
| Continue from a checkpoint | `--base checkpoints/run2/best` | resume from a previous best at a lower LR |
| fp32 | `--no-amp` | for NaN losses or GEMM errors (now covers the benchmark too) |

Not used: **QLoRA**. It exists to fit multi-billion-parameter models in small memory. Laya is 421M and
full-fine-tunes comfortably, so 4-bit quantization would only cost accuracy and add bitsandbytes ROCm risk.

Temperatures are refit after every epoch on the held-out calibration missions (now through the fp16 harness,
~3× faster than `laya.train.calibration_records`). The best epoch is selected on the validation set, so its
score is slightly optimistic; `final/` and `compare_runs.py`'s "last" column are reported too.

Compare runs: `python scripts/compare_runs.py checkpoints/run2 checkpoints/run3_lora checkpoints/run4_*`.
For a final LoRA-vs-full verdict: 3 seeds per arm (`RUNS="S1 S2"`), the full benchmark
(`python scripts/benchmark.py --model checkpoints/<run>/best --out results/<run>`), and call it a tie unless the
gap is above ~8 points on real (9 held-out missions are noisy).

## Honest limits
- 27 real missions. Real-segment CIs (mission-level bootstrap) are wide; read them.
- Track B labels are our policy, not NextEra's. Treat a high Track B score as "applies the policy reliably from text",
  not "discovered the truth". The deterministic validator remains the safety floor.
- The data is synthetic and fictional (NextEra's kit).
