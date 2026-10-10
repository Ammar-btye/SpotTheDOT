#!/usr/bin/env bash
# The LoRA sweep from research/tech-lora-gap-2026-10-10.md, one run after another on one GPU.
#
#   nohup bash scripts/sweep_lora.sh > checkpoints/sweep.log 2>&1 &
#   RUNS="A C" bash scripts/sweep_lora.sh          # only some runs
#   EPOCHS=6 bash scripts/sweep_lora.sh            # shorter
#
# Every run uses the same data, oversampling, epochs and 600-row benchmark sample (the one run2 and
# run3_lora used, so their epoch tables compare). Checkpoints are selected on the calibration missions
# (calib-ce), so the benchmark stays an unselected test. Each run is ~12 x 14 min with --bench-limit 600.
# Compare: python scripts/compare_runs.py checkpoints/run4_*
set -u
cd "$(dirname "$0")/.."
EPOCHS=${EPOCHS:-12}
RUNS=${RUNS:-"A B C D E"}
COMMON="--epochs $EPOCHS --patience 4 --min-lr-ratio 0 --oversample will_fail=2,anomaly_expected=2
        --bench-limit 600 --select-metric calib-ce"
LORA="--lora --head-lr 3e-4 --weight-decay 0"

run() {   # run <name> <flags...>
  local name=$1; shift
  if [ -f "checkpoints/$name/final/model.safetensors" ]; then echo "skip $name (done)"; return; fi
  echo "=== $name: $* ($(date))"
  python scripts/finetune.py --out "checkpoints/$name" $COMMON "$@" > "checkpoints/$name.log" 2>&1 \
    || echo "!!! $name failed, see checkpoints/$name.log"
  grep -A20 "^| Epoch" "checkpoints/$name/training_report.md" 2>/dev/null
}

mkdir -p checkpoints
for r in $RUNS; do
  case $r in
    A) run run4_A_lora      $LORA --lora-lr 2e-4 ;;                                  # the fixed setup
    B) run run4_B_lora_lr4  $LORA --lora-lr 4e-4 ;;                                  # LR is the most sensitive knob
    C) run run4_C_full      --encoder-lr 2e-5 --llrd 0.95 ;;                          # fair full-FT baseline, same data/epochs
    D) run run4_D_lora_r64  $LORA --lora-lr 2e-4 --lora-r 64 --lora-alpha 128 ;;     # more capacity, same scale
    E) run run4_E_loraplus  $LORA --lora-lr 1e-4 --loraplus-ratio 16 ;;               # LoRA+ (lower base LR)
    F) run run4_F_pissa     $LORA --lora-lr 5e-5 --lora-init pissa_niter_16 ;;       # PiSSA init
    S1) run run4_A_seed1    $LORA --lora-lr 2e-4 --seed 1 ;;                          # seeds for the final call
    S2) run run4_A_seed2    $LORA --lora-lr 2e-4 --seed 2 ;;
    *) echo "unknown run $r" ;;
  esac
done
python scripts/compare_runs.py checkpoints/run2 checkpoints/run3_lora checkpoints/run4_* --metric real
