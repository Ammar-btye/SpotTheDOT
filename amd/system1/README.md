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
| `train.jsonl` | 3,654 | fine-tuning (real train missions × 3 renderings + 120 synthetic missions) |
| `calib.jsonl` | 630 | refitting temperatures after each epoch (30 synthetic missions) |
| `benchmark.jsonl` | 1,557 | validation: run before training and after every epoch |

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
# 3) smoke test first (~minutes): 1 epoch on a slice
python scripts/finetune.py --out checkpoints/smoke --epochs 1 --train-limit 300 --bench-limit 150 --calib-limit 100
# 4) the real run: benchmark after every epoch
python scripts/finetune.py --out checkpoints/run1 2>&1 | tee checkpoints/run1.log
```
If ROCm training produces NaN losses, add `--no-amp`. If the GPU resets mid-run, set `TORCH_BLAS_PREFER_HIPBLASLT=0`
(slower). Watch the GPU with `amd-smi monitor --watch 1`. Upload the best model when you're happy:
`python scripts/finetune.py ... --push-to-hub <user>/laya-spot-triage` (needs `hf auth login`).

## Outputs
- `results/baseline_laya/`: untuned Laya on the benchmark (`report.md` is the readable summary).
- `checkpoints/<run>/epoch_NN/`: the full benchmark after each epoch (`epoch_00` = before training).
- `checkpoints/<run>/training_report.md`: every metric across epochs.
- `checkpoints/<run>/best/` and `final/`: load with `laya.load(path)` plus the questions in `questions.json`.

## Defaults and why (`research/tech-laya-rocm-finetune-2026-10-10.md`, `tech-smalldata-finetune-eval-2026-10-10.md`)
- `--loss soft-ce`: Laya's own #741 measured no gain from the RL term at this scale. `--loss rlcd` is available.
- 12,702 training items; 6 epochs × micro-batch 8 × grad-accum 4 = 2,382 optimizer updates. That's well above the ~350 minimum; small runs can
  collapse to the class prior (laya #963), and the script warns if it sees that.
- Option order is shuffled each epoch so the model can't learn a position prior.
- Temperatures are refit after every epoch on held-out calibration missions, not a random item split.
- The best epoch is selected on the validation set, so its score is slightly optimistic. `final/` is reported too.

## Honest limits
- 27 real missions. Real-segment CIs (mission-level bootstrap) are wide; read them.
- Track B labels are our policy, not NextEra's. Treat a high Track B score as "applies the policy reliably from text",
  not "discovered the truth". The deterministic validator remains the safety floor.
- The data is synthetic and fictional (NextEra's kit).
