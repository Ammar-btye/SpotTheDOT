# Why LoRA trailed the full fine-tune on Laya, and how to close the gap (2026-10-10)

## 1. Scope
The question: why did the LoRA run (r=16, α=32 on Wqkv/Wo/Wi; adapter LR 2e-4 with LLRD 0.95; head LR 1e-4; 3 epochs cut by a 45-minute budget) score below the full fine-tune, and how do we keep LoRA (portable PEFT workflow) while closing the gap?

Five parallel research passes, plus code reading of `amd/system1/triage/trainer.py`, `scripts/finetune.py`, `scripts/build_data.py` and the laya 0.4.1 source:
1. Why LoRA learns less, and the hyperparameters that close the gap
2. LoRA variants and initializations in Hugging Face PEFT (0.21.2 installed)
3. The optimization recipe for LoRA plus a freshly trained head
4. Laya- and ModernBERT-specific handicaps
5. Loss as a yardstick, class imbalance, and evaluation

Skipped: newer PEFT methods (GraLoRA, KaSA, MiCA, HiRA, GLoRA), for which there is no NLU evidence; QLoRA, which isn't needed at 421M.

No ModernBERT-specific LoRA-vs-full-FT study exists. Most evidence is from RoBERTa/DeBERTa GLUE and decoder-LLM SFT.

## 2. Findings: what's handicapping our LoRA run

| # | Cause | Evidence | Fix (✅ = existing flag) |
|---|---|---|---|
| 1 | **Undertrained.** The budget cut the run to 3 epochs, and real F1 was still rising (0.629 → 0.689 → 0.733). LoRA needs more epochs than full FT. The LoRA paper trained RoBERTa GLUE for 10–30 epochs; Mosbach et al. recommend about 20 on small data. | [Hu et al. Table 9](https://ar5iv.labs.arxiv.org/html/2106.09685), [Mosbach 2021](https://arxiv.org/abs/2006.04884) | ✅ `--epochs 12 --max-minutes 0` |
| 2 | **LLRD starves the lower adapters.** 0.95²⁷ ≈ 0.25×, so the bottom adapters ran at about 5e-5. LoRA's best LR is about 10× full FT's (≈2e-4 here), uniform across layers. B starts at zero, so a low LR barely moves those layers. No source combines LLRD with LoRA. | [Thinking Machines, "LoRA Without Regret"](https://thinkingmachines.ai/blog/lora/), [Biderman 2024](https://arxiv.org/abs/2405.09673) | ✅ `--llrd 1.0` |
| 3 | **Head LR (1e-4) is below the adapter LR (2e-4).** The head is a 26.5M-param fresh network: 2 transformer layers plus a scorer. Published recipes give the head an LR ≥ the adapters'. | [Hu et al.](https://ar5iv.labs.arxiv.org/html/2106.09685), [arXiv 2602.06204](https://arxiv.org/pdf/2602.06204) | ✅ `--head-lr 3e-4` |
| 4 | **The LR is the most sensitive LoRA knob.** A tuned LR closes most of the gaps between variants. | [Biderman](https://arxiv.org/abs/2405.09673), [arXiv 2602.04998](https://arxiv.org/pdf/2602.04998) | ✅ sweep `--encoder-lr` 2e-4 / 4e-4 |
| 5 | **LoRA dropout 0.05, while ModernBERT's own dropouts are all 0.** This adds noise that full FT doesn't have. | [Laya encoder config](https://huggingface.co/convaiinnovations/laya/raw/main/encoder/config.json) | ✅ `--lora-dropout 0` |
| 6 | **All LayerNorms are frozen under LoRA** (58K params, including `final_norm`, which feeds the head). Full FT trains them. | code: `apply_lora` only wraps the targets | code: unfreeze `*norm.weight` after `get_peft_model`; the export already handles them |
| 7 | **Warmup was 12%, not 6%.** Warmup is computed from the 6-epoch horizon before `_fit_budget` shrinks it. | code: `trainer.py` `warmup = …plan["horizon"]` | code: recompute warmup after the budget fit (moot with `--max-minutes 0`) |
| 8 | **Rank 16 is probably not the bottleneck.** About 26k label bits vs about 7.2M adapter params. Rank 64 reduces "intruder dimensions" and may help generalization a little. | [Shuttleworth 2024](https://arxiv.org/html/2410.21228) | ✅ `--lora-r 64 --lora-alpha 128` (sweep point) |

Already correct:
- The targets hit all four linears (`Wqkv`, `attn.Wo`, `Wi`, `mlp.Wo`): 7.2M adapters plus 26.5M head = 33.7M trainable.
- Gradients flow (no `no_grad` in `_forward`).
- Laya adds no special tokens, so the frozen embeddings cost little.

## 3. Loss is the wrong yardstick
- **There's a floor.** Label smoothing 0.05 makes the minimum soft-CE the target entropy: K=2 0.117, K=3 0.169, K=4 0.201, about **0.16 averaged over the question mix**. Oversampling, LoRA dropout, epoch count and budget-resized schedules all move train loss without changing quality. Full FT's 13× more trainable capacity memorizes more, which lowers train loss.
- **Per-step "loss" is one micro-batch of 8**, so swings from 0.22 to 1.4 are expected.
- **Rule:** compare runs on held-out real macro-F1 with mission-bootstrap CIs. Break ties on unsmoothed calib CE. Never compare train loss across runs.
- **Will-fail recall is noise at `--bench-limit 600`.** The real segment has only 17 positives, so 35% → 29% is one item (Wilson CI ~13–53%).

## 4. LoRA variants (PEFT `LoraConfig`)
Well-tuned plain LoRA roughly matches full FT on GLUE-style classification, and variants add 0–1.5 points with contradictory rankings across papers. Try in order:
1. **Plain LoRA, fixed setup** (§2).
2. **LoRA+** (B-matrix LR × 8–16; +1–2% on RoBERTa per [Hayou 2024](https://arxiv.org/html/2402.12354); Thinking Machines say it ≈ a re-tuned LR). Implement inside `param_groups`; PEFT's `create_loraplus_optimizer` would override our head LR.
3. **PiSSA** (`init_lora_weights="pissa_niter_16"`, lower LR 5e-5 to 1e-4). +1.2 on DeBERTa GLUE in [its paper](https://arxiv.org/html/2404.02948), no gain in [EVA's re-run](https://arxiv.org/html/2410.07170). The SVD runs on CPU before `.to(dev)`, so ROCm is not involved.
4. **LoRA-GA** (`LoraGAConfig` + `preprocess_loraga`, PEFT ≥ 0.19) has the strongest reported gain ([2407.05000](https://arxiv.org/html/2407.05000), T5 GLUE 87.77 vs FT 87.91 vs LoRA 82.08) but the most integration work.
- Skip **DoRA** (loses to LoRA on DeBERTa NLU) and **rsLoRA** (helps only at r ≥ 128).
- Don't use `modules_to_save`: it breaks `export_state_dict` key mapping. Every variant above still merges into a plain Laya checkpoint. PiSSA/LoRA-GA adapters apply to a residual base, so the merged checkpoint is the source of truth.

## 5. Imbalance, counterfactuals, stabilizers
- **Post-hoc per-question threshold (logit offset) fit on `calib.jsonl`** (64 will_fail and 52 anomaly positives). No retraining needed. The decision is a plain argmax, and temperature scaling doesn't change it, so current calibration does nothing for recall. Logit adjustment ≈ or > reweighting ([Menon 2021](https://arxiv.org/abs/2007.07314)). Calib is synthetic, so confirm on real. Keep ×2 oversampling; skip focal loss at 15–20% positives.
- **Counterfactuals are built only from held-out events** (`scripts/build_data.py:178`), so training has no one-field contrast pairs. That explains the weakest segment (0.60). Generate them from training events too, and batch each pair together ([Kaushik 2019](https://arxiv.org/abs/1909.12434), [Teney 2020](https://arxiv.org/abs/2004.09034)).
- **LP-FT** (head-only first, then adapters) rescues collapsed LoRA runs but is neutral on non-collapsed ones ([Tomihari & Sato 2024](https://arxiv.org/html/2405.16747)). Our run didn't collapse. It's cheap via `--freeze-encoder`, then `--base`.
- **Stabilizers:** SWA never helped on RoBERTa/GLUE; R-Drop needs dropout (we have none); there's no EMA evidence for classification. **Ensembling 3 seeds' logits** is the reliable one.
- **Seed variance is large on small data** ([Dodge 2020](https://arxiv.org/abs/2002.06305)). Our own note says paired differences under about 8–10 points on ~270 real events are unresolvable.

## 6. Proposed runs (sequential on one GPU, no `--max-minutes`)
Run A uses existing flags only:
```
--lora --lora-r 16 --lora-alpha 32 --lora-dropout 0 --encoder-lr 2e-4 --llrd 1.0 --head-lr 3e-4
--weight-decay 0 --epochs 12 --min-lr-ratio 0 --patience 4 --oversample will_fail=2,anomaly_expected=2
```
Ranked sweep:
1. **A**
2. **B:** A with `--encoder-lr 4e-4`
3. **C:** long full FT, as the fair baseline (`--encoder-lr 2e-5 --epochs 12`, same everything else)
4. **D:** A with `--lora-r 64 --lora-alpha 128`
5. **E:** best of A/B/D plus trainable norms and LoRA+ (needs code)
6. **F:** best config × seeds 1, 2, then ensemble

Fair-comparison protocol:
- Same data, oversampling, smoothing and update count.
- Full benchmark (no `--bench-limit`) for the final call.
- 3 seeds per arm.
- Select checkpoints on calib, not real.
- Call it a tie unless the paired difference is > ~8 points with a CI excluding 0.

## 7. Head-to-head (same 600-row benchmark, since epoch 00 is identical; both 3 epochs)
| Run | Best epoch | Real | Synthetic | Counterfactual | Will-fail recall |
|---|---|---|---|---|---|
| run2 full FT | 2 | **0.805** | 0.739 | **0.846** | 41.2% |
| run3_lora | 3 (still rising) | 0.733 | 0.731 | 0.602 | 29.4% |

- **The gap is concentrated in counterfactual (−24 points).** Synthetic is a tie (−1), and real is −7, inside the ~8–10 point noise band.
- Full FT peaked at epoch 2; LoRA was still climbing. That's consistent with LoRA learning slower (§2 #1–2).
- Hypothesis (untested): one-field sensitivity needs the lower layers, which LLRD starved under LoRA.
- run2's exact flags are not in its report (it predates the Strategy line). Check `run2.log` / `run2/run_config.json`.

## 8. Open questions
- run2's settings: oversampling, LLRD, LR, budget.
- Untested: the LLRD + LoRA interaction; trainable norms for NLU; the 10× LR rule on encoder classifiers (it's from LLM SFT).
- Whether calib-fit thresholds transfer from synthetic to the 9 real missions.
