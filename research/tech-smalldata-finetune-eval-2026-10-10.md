# Small-data fine-tune and honest benchmark for Laya triage (2026-10-10)

## 1. Scope

Fine-tuning Laya (ModernBERT-large, 421M) to triage SPOT events, and benchmarking it credibly. Real kit: 27 missions (18 V1 / 9 V2), 270 actions, 40 anomalies (4 CRITICAL); labels come from our deterministic policy. Unit = **event** (action + reading + anomaly); group = **mission**. "(unverified)" = no source; "our calc" = our arithmetic.

## 2. Findings

**Laya specifics (read from the repo on 2026-10-10)**
- Laya ships over-confident (temperature refit: ECE 0.466 → 0.081). Zero-shot it scores 0.362, *below* the 0.461 majority baseline; fine-tuned, 0.766. https://huggingface.co/convaiinnovations/laya
- It trains with its own RLCD loop (`laya.train.finetune`), not HF `Trainer`. Defaults: `encoder_lr=2.5e-5`, `head_lr=1e-4`, `weight_decay=0.01`, batch 64, 4 epochs; `freeze_encoder` is all-or-nothing. https://github.com/NandhaKishorM/laya/blob/main/laya/train.py
- On "a few hundred or a thousand labelled rows" predictions can silently **collapse to the class prior**; v0.4.1 prints the update count (1,100 items → 72 updates). Same file; https://github.com/NandhaKishorM/laya#fine-tuning
- **Leakage trap:** `split_calibration` holds out a *random item-level* 10% for temperatures, and the `eval_data` overlap check only catches token-identical inputs, so rendering variants of one event leak. `train_model(..., on_epoch_end=cb)` is the per-epoch hook. https://github.com/NandhaKishorM/laya/blob/main/laya/train.py

**Splitting**
- `StratifiedGroupKFold` keeps each group in exactly one test fold and stratifies only "as much as possible". With few, large groups it degrades toward `GroupKFold`. https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html
- Split correlated samples by group to measure generalization to new groups. https://scikit-learn.org/stable/modules/cross_validation.html
- Train/test (near-)duplicates are a leading leakage type. https://arxiv.org/abs/2207.07048
- Small test sets give CV error bars of about ±10% at n≈100. https://arxiv.org/abs/1706.07581
- Selecting a model or epoch on the reported data biases it upward; keep an untouched test set. https://jmlr.org/papers/v11/cawley10a.html

**Synthetic data**
- TSTR (train synthetic, test real) vs TRTR measures synthetic-data usefulness. https://arxiv.org/abs/1706.02633
- Domain randomization (vary nuisance factors widely) aids sim-to-real transfer. https://arxiv.org/abs/1703.06907
- LLM-generated training data helps less as the task gets more subjective, and data diversity matters. https://arxiv.org/abs/2310.07849
- Classifier two-sample test: if real vs synthetic is separable, the generator has exploitable artifacts. https://arxiv.org/abs/1610.06545
- Models latch onto shortcuts, and partial-input baselines expose them. https://arxiv.org/abs/2004.07780, https://arxiv.org/abs/1803.02324

**Testing beyond policy agreement**
- CheckList provides invariance (INV), directional (DIR) and minimum-functionality tests. https://arxiv.org/abs/2005.04118
- Contrast sets: minimal label-flipping edits, scored per pair. https://arxiv.org/abs/2004.02709
- Counterfactually-augmented data reduces reliance on spurious features. https://arxiv.org/abs/1909.12434
- ISA-18.2 priority = consequence severity × time to respond, backing our policy. https://www.processonline.com.au/content/software-it/article/improving-alarm-management-with-isa-18-2-part-1-37009763

**Metrics and statistics**
- On imbalanced data, the PR curve is more informative than ROC. https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432
- Temperature scaling is a single-parameter fit on a held-out validation set. https://arxiv.org/abs/1706.04599
- Binned ECE is biased and binning-sensitive; use adaptive bins and also report Brier. https://arxiv.org/abs/1904.01685, https://arxiv.org/abs/1909.10155
- Reliability diagrams and calibration curves are available in scikit-learn. https://scikit-learn.org/stable/modules/calibration.html
- Use paired significance tests or a paired bootstrap when comparing systems. https://aclanthology.org/P18-1128/
- Small NLP test sets are badly underpowered. https://arxiv.org/abs/2010.06595
- Wilson-type intervals beat Wald intervals at small n. https://projecteuclid.org/journals/statistical-science/volume-16/issue-2/Interval-Estimation-for-a-Binomial-Proportion/10.1214/ss/1009213286.full
- `scipy.stats.bootstrap` supports BCa and paired resampling. https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html

**Small-data fine-tuning**
- Small-data BERT instability comes from too few iterations; fix with a small LR, bias-corrected Adam, warmup and *more* updates. https://arxiv.org/abs/2006.04884
- With few samples, more training iterations and re-initializing the top layers help. https://arxiv.org/abs/2006.05987
- The random seed alone swings results substantially, so run several seeds. https://arxiv.org/abs/2002.06305
- Freezing the lower layers keeps most of the quality. https://arxiv.org/abs/1911.03090
- ModernBERT architecture. https://arxiv.org/abs/2412.13663
- `EarlyStoppingCallback` needs `load_best_model_at_end` and `metric_for_best_model`; it stops only on save steps. https://huggingface.co/docs/transformers/main_classes/callback
- Model cards are a reporting template. https://arxiv.org/abs/1810.03993

## 3. Recommended split, metrics and training recipe

### 3a. Split: mission-grouped, three roles, rotated
1. Give every item `mission_id`, `event_uid` and `root_event_uid`. The root is the real or simulated event a variant came from. **All renderings, perturbations and paraphrases of a root share its mission's split.**
2. **Real data: 3 folds of 9 missions** (6 V1 + 3 V2 each) via `StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=…)`. Stratify on `config × (mission has a HIGH or CRITICAL anomaly)`. Check by hand that the 4 CRITICAL anomalies and M017 are spread across folds. Each run uses fold A to **train** (and to fit the simulator), fold B for **val/calibration** (per-epoch evaluation, early stopping, temperature) and fold C for **test** (locked). Rotate A→B→C three times so every real mission is tested exactly once, then pool the out-of-fold test predictions (about 270 events, about 40 anomalies). If time allows only one run, report it and say so.
3. **Synthetic data: split by synthetic mission**, about 80/10/10 (for example 400/50/50 missions). Keep the synthetic test set as its own column.
4. **Fit the simulator's statistics on the train-fold missions only.** If you can't, disclose that aggregate rates saw the test missions. That is weaker leakage than event-level overlap, but it is leakage (https://arxiv.org/abs/2207.07048).
5. **Hold out one rendering.** Train on JSON plus log line, and test on operator note (plus a missing-field and noise set). This tests format generalization rather than template memorization.
6. **Keep REAL-TEST and SYN-TEST separate.** REAL-TEST is the headline.
7. **Do not use Laya's built-in random `calib_frac` split.** Pass only train items and set `calib_frac=0` (the code allows a value in [0,1)). Then fit one temperature per question type yourself by minimizing NLL on fold B. Whether `calib_frac=0` skips calibration cleanly is unverified.

### 3b. Benchmark sets (all built from REAL-TEST roots)
- **Canonical:** JSON rendering scored against the policy labels.
- **Robustness:** log line, operator note, keys dropped at 10–30%, typos and unit or format noise, shuffled key order. The CheckList INV test passes when the prediction does not change.
- **Contrast pairs:** minimal edits that cross a policy boundary. Examples: battery 26% → 24%, asset criticality LOW → HIGH, reading GOOD → QUESTIONABLE, MEDIUM → HIGH severity. Report **pair accuracy** (both members right). Add **DIR/monotonicity** checks: P(escalate) must not drop when severity rises.
- **Masked independent labels:** remove a field and predict it from the rest. Examples: hide `severity` and predict it from the reading and context; hide `status` and predict FAILED. The kit's `operator_review_required` is exactly `severity ∈ {HIGH, CRITICAL}`, and QUESTIONABLE readings coincide exactly with FAILED actions (our analysis, `spot-data-insights-2026-10-09.md`). Leaving these fields in the input makes any "independent label" agreement trivial.
- **Shortcut probes:** (a) a partial-input baseline, such as logistic regression on `config_version` + `waypoint` alone, or bag-of-words; (b) a C2ST real-vs-synthetic classifier. If its AUC is ≥0.8, warn that generator artifacts exist (the threshold is our heuristic, unverified).
- **TSTR gap:** for each real fold, compare (i) synthetic only, (ii) real train fold only, (iii) both. Plot real-test Brier against the number of synthetic missions (0, 50, 100, 200, 400). If SYN-TEST improves while REAL-TEST stalls or gets worse, the model is learning the generator.

### 3c. Metrics (on REAL-TEST, each with a 95% CI)
**Top 3 (preregister them; don't switch after looking):**
1. **Escalation recall at a fixed precision** (and PR-AUC). Positive = the policy says escalate. Missed escalations are the costly error.
2. **Macro-F1** across priority classes. Pool CRITICAL with HIGH (as "≥HIGH"), because 4 CRITICAL anomalies can't support a separate estimate.
3. **Brier score** per question (a proper scoring rule), with **ECE** after temperature scaling (10 equal-mass bins, or 5 when n<150) and a reliability diagram.

**Secondary:** per-question accuracy; RPS for `score` questions; robustness drop; contrast-pair accuracy; and a cost-weighted score:
  - cost matrix: missed ≥HIGH escalation = 10, missed MEDIUM = 3, false escalation = 1 (our proposal; state it explicitly)
  - reported as expected cost per 100 events
  - plotted against the escalation threshold

**CIs:**
- Use a **mission-level cluster bootstrap** with 10,000 resamples and BCa or percentile intervals, because events within a mission are correlated.
- Compare systems with a **paired** bootstrap of the difference (same resamples for baseline and fine-tuned).
- Put Wilson intervals on recall when the count of positives is small.
- With only 9 missions in one fold, cluster-bootstrap CIs are themselves unreliable (unverified; this is a known few-clusters problem). Pooling all 3 rotations (27 missions) is much better.

**Sample size (our calc, Wald approximation):**

| Test size | Accuracy ≈ 0.85 | Recall ≈ 0.90 |
|---|---|---|
| 90 events (1 fold) | ±0.074 | ±0.13 (~20 positives) |
| 270 events (pooled) | ±0.043 | ±0.076 (~60 positives) |

At 270 pooled events, a paired comparison can resolve differences of roughly 8–10 points. Do not claim gains smaller than that. That threshold is a rough heuristic consistent with https://arxiv.org/abs/2010.06595.

### 3d. Training recipe (Laya RLCD loop)
- **Data per run:** about 400 synthetic train missions (about 4,000 events) × 2 training renderings, plus the real fold-A events, with real events **oversampled 3×** (heuristic, unverified). Print the optimizer-update count and aim for ≥300 updates total.
- **Hyperparameters:**
  - effective batch 16 (micro 8 × accum 2), down from the default 64, to get more updates
  - `encoder_lr=1.5e-5`, `head_lr=1e-4`, `weight_decay=0.01`, `grad_clip=1.0`
  - max 8 epochs; keep Laya's `sigma` annealing
- **Ablation first:** run `freeze_encoder=True` (head only) as a cheap baseline. Freezing only the lower layers (for example the bottom 14 of 28) would need custom code.
- **Per-epoch evaluation:** pass `on_epoch_end` to `train_model`. On each call, compute Brier and escalation recall on **REAL-VAL (fold B) and SYN-VAL**, save the checkpoint, and keep the best by REAL-VAL Brier. Stop after 2 epochs with no improvement greater than 0.002. Log both curves; when they diverge, the model is learning the generator.
- **Calibration:** after picking the epoch, fit temperatures on fold B and **then** touch fold C once.
- **Seeds:** 3 seeds; report mean ± sd plus the pooled CI. Check the collapse warning (logit range near 0) on every run.
- **If you use a plain ModernBERT classification head with HF `Trainer` instead:**
  - `eval_strategy="epoch"`, `save_strategy="epoch"`
  - `load_best_model_at_end=True`, `metric_for_best_model="brier"`, `greater_is_better=False`
  - `EarlyStoppingCallback(early_stopping_patience=2, early_stopping_threshold=0.002)`

### 3e. Presenting results to judges
- **One table.**
  - Rows:
    - majority class
    - rule policy (System 1) on canonical JSON (100% vs policy by construction; say so)
    - rule policy on variants (with our parser)
    - Laya zero-shot + temperature
    - Laya fine-tuned on synthetic only
    - Laya fine-tuned on synthetic + real
  - Columns: REAL-TEST canonical, REAL-TEST robustness, contrast-pair accuracy, masked-label macro-F1, SYN-TEST, and expected cost per 100 events.
  - Each cell: value plus [95% CI]. Put n (events and missions) in the header.
- **Plots:**
  - reliability diagram before and after temperature, with bin counts
  - per-epoch REAL-VAL vs SYN-VAL curves
  - TSTR learning curve
- **Short model card:** synthetic kit, policy-derived labels, wide CIs, known leakage (simulator stats; single split if so).
- **Pitch:** *robustness and calibrated routing where rules break*, not "beats the rules on rule labels".

## 4. Open questions
1. What is the triage question schema (which `choice`, `score` and `noul` questions), and what is the escalate base rate? The CI and power numbers above assume about 20–25% positives.
2. Can the simulator be refit per fold in the time we have, or do we accept and disclose aggregate-statistics leakage?
3. Does `calib_frac=0` skip calibration cleanly, or call `train_model` directly?
4. Fine-tune wall time on the AMD box decides 3 rotations × 3 seeds (9 runs) vs 1 × 3.
5. Who writes contrast pairs and regex-checks that LLM paraphrases keep key values? (~1 hour.)
6. Confirm cost-matrix weights with NextEra mentors?
