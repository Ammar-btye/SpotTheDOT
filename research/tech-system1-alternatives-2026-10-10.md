# System 1 alternatives to Laya: tabular, time-series, encoder and baseline models

_Researched 2026-10-10 (Sat). Each claim has a URL. Claims marked **unverified** or **estimate** are my judgment, not a published result._

## 1. Scope

- **Task.** System 1 reads one robot event and returns a flag with a calibrated probability. The event fields are status, failure_type, battery, location and environment, asset criticality, the reading and its quality, and the anomaly type and severity. A deterministic validator and the System 2 LLM come after it.
- **Our data.** I computed these from `SPOTDATA/.../02_DATA/` tonight:
  - 270 actions: 221 SUCCESS and **49 FAILED**.
  - 40 anomalies.
  - 220 readings, which form **83 asset × measurement series, median length 3, max 7**.
- **Hardware.** Radeon 8060S, gfx1151 (`research/knighthacks-ix-tracks.md`).
- **Prize.** HF judges on creativity, technical execution and meaningful use of the HF ecosystem (same file).

## 2. Findings

### 2.1 Laya (the planned model)

- **Architecture.** ModernBERT-large, 421M parameters, with three question types: `choice`, `score` (ordinal) and `noul` (yes/no). It returns calibrated probabilities in one forward pass, about 33 ms on a T4. License is Apache-2.0 (https://huggingface.co/convaiinnovations/laya).
- **Limits the card admits** (same URL):
  - Zero-shot accuracy on its typed-decisions benchmark is **0.362, below the 0.461 majority baseline**. The fine-tuned `laya-typed-decisions` checkpoint reaches **0.766**.
  - Ordinal `score` questions are weak (SST-5: 0.372).
  - A `noul` answer "can follow option labels instead of state text".
  - It is over-confident until temperature calibration, which takes ECE from 0.466 to 0.081.
- **Fine-tuning.** A free Kaggle 2×T4 notebook covers the whole loop: build data, RLCD training, temperature calibration, evaluation and export (https://github.com/NandhaKishorM/laya). The "2,000 decisions" figure is the **evaluation** set. The training-set size is **unverified**.
- **Ecosystem.** The model has 5.4k likes, 41.5k downloads and 65+ Spaces (https://huggingface.co/convaiinnovations/laya). It is the current HF "System 1" trend, so it reads well to HF judges.
- **ROCm.** The card never mentions ROCm. The `laya[fast]` TileLang path has been shown only on MI300X (https://rocm.blogs.amd.com/ecosystems-and-partners/rocm-tilelang-kernel/README.html). The plain transformers path should run on AMD's gfx1151 PyTorch wheels (see `tech-amd-rocm-hf-serving`), but this is **unverified**. Flash Attention on gfx1151 is also **unverified**, so use SDPA or eager attention.

### 2.2 Tabular foundation models (in-context learning, no training)

- **TabPFN.**
  - v2 (Nature, Jan 2025) beat tuned baselines on datasets up to 10k samples. In 2.8 s it outperformed an ensemble tuned for 4 hours (https://pubmed.ncbi.nlm.nih.gov/39780007/).
  - Licenses differ by version:
    - **2.5:** gated and non-commercial (https://huggingface.co/Prior-Labs/tabpfn_2_5).
    - **3.5** (Sep 2026, the current default): non-commercial too (https://en.wikipedia.org/wiki/TabPFN, https://www.digitalapplied.com/blog/tabpfn-3-5-tabular-foundation-model-when-to-use).
    - **v2:** "Prior Labs License", which is Apache plus attribution. Load it with `ModelVersion.V2` (https://huggingface.co/Prior-Labs/TabPFN-v2-clf, https://cdn.jsdelivr.net/gh/PriorLabs/TabPFN@main/README.md).
  - Every version needs a `TABPFN_TOKEN` login.
  - AMD install: `pip install torch` from the ROCm index first, then `pip install tabpfn`.
  - CPU limits: about 1k samples for older checkpoints and 5k for v3+ (same README).
- **TabICLv2** (ICML 2026, Inria).
  - Without tuning, it beats RealTabPFN-2.5 on TabArena and TALENT (https://arxiv.org/abs/2602.11139).
  - The weights are on HF under BSD-3 (https://huggingface.co/jingang/TabICL).
  - The model is about 28M parameters. It won 40 of 51 comparisons against tuned GBDTs, with prediction times comparable to CPU implementations (https://hyper.ai/en/stories/f26a4f557e9fdc55b33701ef8afeb4dd). It has the **cleanest license and least friction** of the tabular foundation models.
- **Mitra** (Amazon/AutoGluon).
  - 72M parameters, Apache-2.0, run through `autogluon.tabular[mitra]`, and fine-tunable (https://huggingface.co/autogluon/mitra-classifier).
  - Its paper claims it beats TabPFNv2 and TabICL with "better sample efficiency" (https://arxiv.org/abs/2510.21204).
- **Fit for us.** These models target exactly our size, a few hundred rows with mixed numeric and categorical features. They are the strongest candidate for the numeric question "will this action fail, or is this reading risky?" They don't answer typed questions over text.

### 2.3 Time-series foundation models

- **The models.**
  - Chronos-2: 120M parameters, Apache-2.0, quantile forecasts with covariates (https://huggingface.co/amazon/chronos-2).
  - Chronos-Bolt-small: 48M parameters, Apache-2.0 (https://huggingface.co/amazon/chronos-bolt-small).
  - TimesFM-2.5: 200M parameters, Apache-2.0, quantile head (https://huggingface.co/google/timesfm-2.5-200m-pytorch).
  - Moirai-2.0-R-small: **CC-BY-NC-4.0** (https://huggingface.co/Salesforce/moirai-2.0-R-small).
  - MOMENT: MIT, reconstruction-based anomaly detection with a fixed **512-step** input. Shorter series are zero-padded on the left (https://huggingface.co/AutonLab/MOMENT-1-large, https://arxiv.org/html/2402.03885).
- **Fit: poor.** "30–60 readings per type" are pooled across 20 assets. A real per-asset series is only **3 points long (median), 7 at most**. That's too short for a forecast-residual or reconstruction anomaly score. Within a measurement type, a robust z-score (median and MAD) or an Isolation Forest does the job (https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html). Calling a TSFM "anomaly detection" on 3-point series would be overclaiming. Judges who know time series would notice (**estimate**).
- **Exception.** A stretch demo could run Chronos-2 on synthetic long sensor streams, labeled as simulated.

### 2.4 Small encoders and classifiers

- **ModernBERT-base or -large, plain fine-tune** (Apache-2.0, 150M/396M parameters; https://huggingface.co/answerdotai/ModernBERT-base). Same backbone as Laya, but trained with a normal cross-entropy head. This is **the right ablation**: it shows whether RLCD adds anything beyond the backbone.
- **heman10x/rlcd-modernbert-151m ("OpenJev").**
  - GLiClass on ModernBERT-base, Apache-2.0.
  - Card numbers: ECE 3.35%, Brier 0.0785, p50 latency 35.6 ms, and abstention with 97.5% recall.
  - The card has no fine-tuning guide (https://huggingface.co/heman10x/rlcd-modernbert-151m).
  - It is a smaller sibling of Laya, useful if Laya is too slow on CPU.
- **GLiClass** (https://huggingface.co/knowledgator/gliclass-modern-base-v2.0). A zero-shot classifier whose card has no fine-tuning guide. It would be a zero-shot floor only.
- **SetFit.** Competitive with 8 examples per class (https://huggingface.co/docs/setfit/index). It makes a good baseline for "text classifier on rendered state", but it gives no calibrated typed outputs.
- **Evidence on text-serialized tables.** LLMs reading tables as text are competitive with GBDTs "especially in the very-few-shot setting" (https://arxiv.org/abs/2210.10723). The implication is that with hundreds of rows, a numeric model should match or beat a text model on numeric risk (**estimate** for our data).

### 2.5 Small generative models with constrained decoding

- **LFM2.5-350M-RLCD.**
  - Inference only, with no training, and its "scores ... are not calibrated confidence" (https://huggingface.co/notnotsamuel/LFM2.5-350M-RLCD).
  - The LFM Open License ends commercial rights above **$10M annual revenue**, which matters for any NextEra follow-on (https://www.liquid.ai/lfm-license).
  - Not a fit.
- **anthonym21/qwen3-0.6b-rlcd-decision.**
  - Apache-2.0, accuracy 0.807, ECE 0.021.
  - About 105 ms for eight questions over an 800-token context.
  - Needs the `rlcd` package (https://huggingface.co/anthonym21/qwen3-0.6b-rlcd-decision).
  - A credible alternative decision head, but 750M parameters (https://huggingface.co/Qwen/Qwen3-0.6B) is slower than Laya for no clear gain.

### 2.6 Classic ML (required for credibility)

- **Small-data evidence.** Tree models still beat deep nets on medium tabular data (https://arxiv.org/abs/2207.08815).
- **Logistic regression** is "more likely to return well calibrated predictions by itself". On data under ~1k samples, prefer sigmoid recalibration over isotonic (https://scikit-learn.org/stable/modules/calibration.html). Because Laya's pitch is *calibration*, logistic regression is the fair yardstick for Brier and ECE.

### 2.7 Comparison table

Latency figures come from model cards (different GPUs). Expected-fit cells are **estimates** for 300–2,000 rows.

| Model | License / HF | Expected fit (300–2k rows) | Latency | System 1 story | HF-prize value | ROCm (gfx1151) |
|---|---|---|---|---|---|---|
| **Laya 421M** | Apache-2.0, HF | Good on typed text decisions after fine-tuning; near chance zero-shot | ~33 ms on T4 (card) | Exact fit: typed calibrated decisions | **High** | PyTorch path likely; TileLang **unverified** |
| TabICLv2 | BSD-3, HF | **Likely best** on numeric failure risk | ~CPU speed (hyper.ai) | Good: numeric risk prior | Medium | CPU fine; GPU optional |
| TabPFN v2 / 3.5 | v2 Apache+attribution; 2.5+ non-commercial; token needed | Strong | Seconds on CPU for ≤1k rows | Good | Medium | Documented ROCm install |
| Mitra | Apache-2.0, HF | Strong | **Unverified** | Good | Medium | **Unverified** |
| Chronos-2 / TimesFM / MOMENT | Apache / Apache / MIT | **Poor**: series of 3–7 points | Fast | Weak (overclaim risk) | Medium | PyTorch, **unverified** |
| ModernBERT plain fine-tune | Apache-2.0 | ≈ Laya (ablation) | ~tens of ms | Ablation | Medium | As Laya |
| rlcd-modernbert-151m | Apache-2.0 | **Unverified**; no fine-tuning guide | 35.6 ms p50 | Good, smaller | Medium-high | As Laya |
| Qwen3-0.6B RLCD head | Apache-2.0 | Similar to Laya (**unverified**) | ~105 ms for 8 questions | Good | Medium | **Unverified** |
| LFM2.5-350M-RLCD | LFM ($10M cap) | Not trainable; uncalibrated | 43–393 ms | Poor | Low | **Unverified** |
| LogReg / HistGBM / IsolationForest | BSD (sklearn) | Strong; LogReg well calibrated | Sub-ms (**estimate**) | Rule/stat triage | Low | CPU only, no risk |

## 3. Recommendation

**(a) Is Laya a sound choice?** Yes, for typed decisions, provided it is (1) fine-tuned, (2) temperature-calibrated, and (3) measured against the baselines below. Its typed questions match operator questions: "escalate?" (`noul`), "likely cause?" (`choice`), "recommended action?" (`choice`). Avoid `score` for severity, where the card admits weakness. Laya should not be the only numeric risk scorer. On a few hundred rows of battery, location and environment features, a tabular model or logistic regression will probably match it in accuracy and calibration, cost less and be easier to explain (**estimate**; that's what the benchmark tests).

**Two honesty traps to fix before benchmarking** (from `spot-data-insights`):
- **Deterministic labels.**
  - `operator_review_required` is exactly `severity ∈ {HIGH, CRITICAL}`.
  - QUESTIONABLE quality ⇔ FAILED action.
  - Any model gets ~100% on these, which proves nothing. Predict a target that isn't a function of its inputs. Good choices are action failure from *pre-action* features (battery, waypoint, environment, action type, configuration), or escalation from features that exclude severity.
- **Synthetic augmentation.** Train on synthetic data if you like, but **evaluate only on held-out original missions**, split by `mission_id` with grouped cross-validation. Otherwise the benchmark measures our own generator. With 49 failures the confidence intervals are wide, so report them.

**(b) Baselines** (metrics: AUROC, Brier, ECE, p50 latency):
1. **Logistic regression** on one-hot plus numeric features: the calibration yardstick.
2. **HistGradientBoosting or LightGBM**: the standard small-tabular champion.
3. **TabICLv2** from HF, BSD-3: the tabular foundation model, so judges see an HF-native, non-Laya comparison. Use TabPFN v2 if TabICL install fails, and note its token and attribution requirement.
- **If time allows:** a plain ModernBERT-base fine-tune on the same rendered text. This isolates the effect of RLCD from the backbone, which is the most interesting result for HF judges.
- **For readings:** a per-type robust z-score or Isolation Forest, not a time-series foundation model.

**(c) Hybrid (recommended architecture).**
1. **Numeric layer:** TabICLv2 (or logistic regression) gives `p_fail` for the action, plus a per-type robust z-score for the reading.
2. **Render the state as text** with those numbers included, for example: "battery 22% (below the 25% cliff); WP09 HIGH_NOISE; PRESSURE_PSI 3.1 MAD above type median; p_fail=0.71".
3. **Laya** answers the typed questions over that text and returns calibrated probabilities.
4. **The validator** checks Laya's flags against hard rules. Its verdict decides escalation to System 2.

Benchmark Laya with and without the numeric features in the text. If the features help, the chart shows the hybrid working. Publish the fine-tuned checkpoint, the rendered-state dataset and a demo Space to the Hub. That covers the prize's "meaningful use of the HF ecosystem" criterion.

## 4. Open questions

- **Speed.** How fast is Laya on gfx1151 under PyTorch ROCm, and on CPU? Both are **unverified**; measure p50 on the box.
- **Training data.** How many labeled examples did Laya's typed-decisions fine-tune use? **Unverified.** This decides whether ~300 real rows plus synthetic data are enough.
- **Install.** Does `tabicl` install cleanly next to the ROCm torch wheels without pulling a CUDA build? **Unverified.**
- **Temperature fitting.** Can Laya's temperatures be fit on ~50–100 held-out events without overfitting? Isotonic calibration overfits below ~1k samples (sklearn), and Laya's procedure is **unverified**.
- **Prize criteria.** Does the HF track's judging favor a fine-tuned checkpoint pushed to the Hub? I found no public Knight Hacks IX prize page, so this is **unverified**.
