# Cascade architecture + alarm management for the SPOT dashboard

_Researched 2026-10-10. The ISA-18.2/IEC 62682 and EEMUA 191 standards are paywalled, so their numbers come from vendor and consultant summaries (cited). Laya figures are the authors' own model-card claims, and we have not reproduced them._

## 1. Scope

Is **Laya (System 1) → deterministic validator → LLM (System 2)** a safe and defensible design for flagging SPOT inspection events, given that a missed critical issue costs more than a nuisance flag? This file covers cascade and deferral research, rule/model ordering, industrial alarm standards, how to evaluate the pipeline, and what to build and show judges.

## 2. Findings

### 2.1 Cascades, deferral, selective prediction
- **Cascades save cost when the cheap model can tell when it's unsure.** FrugalGPT matched GPT-4 at up to 98% lower cost by learning when to escalate ([arXiv 2305.05176](https://arxiv.org/abs/2305.05176)). RouteLLM cut cost by more than 2x with no quality loss on MMLU and MT-Bench ([arXiv 2406.18665](https://arxiv.org/abs/2406.18665)).
- **Confidence-threshold deferral is a strong default, but it breaks under distribution shift, label noise, or a specialist downstream model** ([Jitkrittum et al., arXiv 2307.02764](https://arxiv.org/abs/2307.02764)). Our V1→V2 configuration change is exactly that kind of shift. On data streams, plain confidence deferral was "inadequate" and needed post-hoc recalibration ([arXiv 2402.04513](https://arxiv.org/abs/2402.04513)).
- **Learning-to-defer** trains the classifier and the "rejector" together as a cost-sensitive problem ([Mozannar & Sontag, arXiv 2006.01862](https://arxiv.org/abs/2006.01862)). **Selective classification** lets you pick a target risk and abstain as needed, which gives a risk-coverage curve ([Geifman & El-Yaniv, arXiv 1705.08500](https://arxiv.org/abs/1705.08500)).
- **Thresholds can come with guarantees.** Conformal methods give distribution-free coverage for any pretrained model ([arXiv 2107.07511](https://arxiv.org/abs/2107.07511)). "Trust or Escalate" calibrates a cascade threshold so that P(correct | not escalated) ≥ 1−α with high probability ([arXiv 2407.18370](https://arxiv.org/abs/2407.18370)).
- **Calibration:** modern neural nets are over-confident, and temperature scaling (one parameter) is usually the best fix ([Guo et al., arXiv 1706.04599](https://arxiv.org/abs/1706.04599)). Under cost asymmetry, the Bayes-optimal flag threshold is p* = C_FP / (C_FP + C_FN) ([Elkan 2001](https://mlanthology.org/ijcai/2001/elkan2001ijcai-foundations)). If a miss costs 20× a false flag, p* ≈ 0.05.
- **An LLM's stated confidence is not a probability.** LLMs are highly over-confident when they verbalize confidence ([arXiv 2306.13063](https://arxiv.org/abs/2306.13063)). So System 2 must not set priority.

### 2.2 Laya specifically (model card, [huggingface.co/convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya))
- ModernBERT-large plus a decision head, 421M parameters, Apache-2.0, about 33 ms per question.
- **The card says the act/escalate head "carries no usable signal yet."** Use the answer-option confidence instead (AUROC 0.77 vs 0.30).
- **It ships over-confident.** ECE is 0.466 before domain temperature fitting and 0.081 after. **Zero-shot accuracy on out-of-domain tasks is about 0.36**, versus 0.766 after fine-tuning.
- **Implication:** out of the box, Laya is the least reliable part of the pipeline. Any design that lets a Laya miss go unchecked is unsafe.

### 2.3 Rule/model ordering (neuro-symbolic, guardrails)
- **LLM-Modulo:** the LLM generates and external sound verifiers check the output ([Kambhampati et al., arXiv 2402.01817](https://arxiv.org/abs/2402.01817)). This pattern fits *explanations* (the LLM writes, rules fact-check). It does not fit *detection*, where a verifier only ever sees what the model chose to send it.
- **Shielding:** a synthesized safety "shield" either offers only safe actions up front, or watches the learner's action and **corrects it only when it would violate the spec** ([Alshiekh et al., arXiv 1708.08611](https://arxiv.org/abs/1708.08611)). That is a precedent for a rule layer that overrides the model.
- **Process-safety independence (LOPA):** a protection layer counts only if it is independent of the initiating event and of other layers' failures ([Primatech](https://www.primatech.com/technical/pt-notes/171); [U-Mich SAFeCHE LOPA tutorial](https://safeche.engin.umich.edu/tutorials/lopa-tutorial)). A rule check that only runs on Laya-flagged events depends on Laya, so it is not an independent layer.

### 2.4 Alarm management (ISA-18.2 / IEC 62682, EEMUA 191)
- **What counts as an alarm:** an alarm means "requiring a timely response." If the operator can acknowledge it and do nothing without consequence, it is not an alarm ([Yokogawa/Control Eng.](https://www.yokogawa.com/us/library/resources/media-publications/implementing-alarm-management-per-the-ansi-isa-182-standard-control-engineering/)). ISA-18.2-2016 adds the **alert**, a notification that needs assessment but doesn't meet alarm criteria ([exida](https://www.exida.com/Blog/when-is-an-alarm-not-an-alarm)).
- **Priority distribution:** about **80% low / 15% medium / 5% high** of *annunciated* alarms. The annunciated figure is the target. The configured (rationalized) figure is a planning tool ([exida, Stauffer 2020](https://exida.com/Blog/which-measure-rationalized-or-annunciated-is-more-important); [Siemens via ProcessOnline](https://www.processonline.com.au/articles/65390-Improving-alarm-management-with-ISA-18-2-Part-2)).
- **Alarm-rate targets** ([Siemens via ProcessOnline](https://www.processonline.com.au/articles/65390-Improving-alarm-management-with-ISA-18-2-Part-2)):

  | Measure | Target | Limit |
  |---|---|---|
  | Alarms per operator | ~1 per 10 min (~6/hr) | 2 per 10 min (~12/hr) |
  | Alarm flood | — | >10 alarms in 10 min |
  | Time spent in flood | <1% | — |
  | Chattering alarms | 0 | — |
  | Stale alarms (active >24 h) | <5 per day | — |

  EEMUA 191 has similar targets: <1 alarm per 10 min in steady state and <10 in the first 10 min after an upset ([Emerson "Alarm management by numbers"](https://d1-live.emerson.com/documents/automation/article-alarm-management-by-numbers-deltav-en-38292.pdf); [automation.com](https://www.automation.com/en-us/articles/2014-1/eemua-191-implications-of-revision-3-on-kpis)).
- **Rationalization sets priority from consequence severity × time to respond**, for example under 3 minutes up to over 30 minutes ([Control Global](https://www.controlglobal.com/articles/2016/alarm-management-is-more-than-just-rationalization/)). The cause, consequence, corrective action and time to respond are documented and shown to the operator on demand. Emerson's DeltaV "Alarm Help" does exactly this ([Emerson white paper](https://d1-live.emerson.com/documents/automation/white-paper-alarm-help-deltav-en-57056.pdf)).
- **State model:** Normal → Unacknowledged → Acknowledged → RTN-Unacknowledged. There are three suppression states: **Shelved** (the operator's, time-limited), **Suppressed-by-Design** (logic), and **Out-of-Service** (maintenance) ([ICONICS ISA-18.2 diagram](https://documentation.iconics.com/v10.97.3/Content/Alarming/Alarm%20Server/Alarm%20References/alarm-state-transition-diagram.htm)). Shelved alarms clear from the display and **come back automatically when the shelf expires**.
- **Why this matters (the "speak NextEra's language" angle):** at Texaco Milford Haven (1994), two operators faced **275 alarms in the last 11 minutes**. The UK HSE named too many, poorly prioritized alarms as a contributing factor ([HSE case study](https://www.hse.gov.uk/comah/sragtech/casetexaco94.htm)).

### 2.5 Operator trust
- **Trust should be calibrated:** reliance should match what the automation can actually do, and how the display presents information shapes trust ([Lee & See 2004](https://journals.sagepub.com/doi/10.1518/hfes.46.1.50_30392)).
- **False alarms lower *compliance* (operators respond less), while misses lower *reliance*.** False-alarm-prone automation is often the more damaging of the two (Dixon, Wickens & McCarley 2007, *Human Factors* 49(4) — **URL unverified**; secondary summary in [Frontiers 2019](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.00519/pdf)). This is the "cry-wolf" effect.

### 2.6 A data fact that matters for evaluation
Our dataset's `operator_review_required` is **exactly** `severity ∈ {HIGH, CRITICAL}` (spot-data-insights-2026-10-09.md). The deterministic rules already reproduce that label, so scoring Laya against it shows nothing.

## 3. Recommendations

**R1. Verdict on ordering: don't run it serially; run the two checks in parallel and escalate on either.**
- Both the rules and Laya see **every** event.
- `escalate = rule_hit OR p_laya ≥ τ`.
- **Rules set a priority floor that the model can raise but never lower.** This is the shield pattern, and it keeps the rule layer independent in the LOPA sense.
- Rules may **force-escalate** without Laya: a CRITICAL asset with any anomaly, a mid-mission battery ≤ 25%, a repeat offender (≥ 3 anomalies on the asset).
- Rules may **not silently suppress**. Physically implausible readings, and QUESTIONABLE readings from FAILED actions, are re-routed to a **Data-quality alert** ("re-inspect; don't trust this value") rather than dropped.

**R2. Priority is deterministic; the LLM explains it.**
- Priority comes from a rationalization table: asset criticality (consequence) × anomaly severity, battery and mission state (time to respond).
- Three alarm priorities plus "alert". Tune the table until the *annunciated* distribution over the 27 missions is close to 80/15/5.
- **Every alarm carries a required action.** If there is none, it is an alert or a log entry.
- System 2 (the LLM) writes only the Cause and Recommended-action text, in the DeltaV Alarm Help / Orbit format. Consequence and time to respond come from the table.

**R3. Fact-check the LLM (LLM-Modulo).**
- Every number and asset ID in the explanation must match the Neon rows. If one doesn't, regenerate, or fall back to a templated explanation.
- Never show the LLM's self-reported confidence.

**R4. Thresholds.**
- Fit a Laya temperature on a held-out split using cross-validation, since the data is tiny.
- Set τ by Elkan's formula with a stated cost ratio (C_FN = 20 × C_FP → τ ≈ 0.05). Then check it against the alarm budget: an annunciated rate of ≤ 6/hr per operator, with 12/hr as the hard ceiling.
- Use a three-way band:

  | Laya probability and rule result | Action |
  |---|---|
  | p < τ_low and no rule hit | Logged, not annunciated |
  | τ_low ≤ p < τ_high and no rule hit | **Alert**, plus an LLM explanation on demand |
  | p ≥ τ_high, or a rule hit | Alarm at the table priority, plus a pre-generated LLM explanation |

- Ignore Laya's act/escalate head. Use the option probability.

**R5. Give Laya a job the rules can't do.** Examples:
- Predicting **action failure risk** from free text and context (battery, environment tag, waypoint history).
- Scoring "is this anomaly description consistent with the reading?"

Measure its *marginal* recall over rules-only, not recall against the severity label.

**R6. Alarm UI that follows the standard.**
- ISA-18.2 states: unacknowledged events blink, acknowledged ones are steady, return-to-normal-unacknowledged is shown in grey.
- **Shelve** requires a reason, has a max duration, and auto-returns. Show a shelved-count badge.
- Show these live KPIs next to their targets:

  | KPI | Target |
  |---|---|
  | Alarms per hour | 6 (12 ceiling) |
  | Flood indicator | lights at >10 alarms per 10 min |
  | Priority distribution | close to 80/15/5 |
  | Stale alarms | <5 per day |

- Group repeats per asset (PANEL-212) instead of re-annunciating them. This prevents chattering.

**R7. Evaluation table (build an ablation).** Compare rules-only, Laya-only, LLM-on-everything, serial (as proposed) and parallel (recommended) on these metrics:
- **Escalation recall at a fixed alarm rate** (≤ 6/hr), with **missed HIGH/CRITICAL as a hard gate** that must be 0.
- **Cost-weighted loss:** C_FN·FN + C_FP·FP + c_LLM·LLM-calls.
- **Share of events resolved without the LLM**, and **LLM call reduction** versus LLM-on-everything.
- **Latency per tier**, p50 and p95: about 33 ms for Laya; seconds for the LLM, pre-generated for priority-1 alarms.
- **Calibration:** ECE (few bins) and Brier score, before and after temperature scaling, plus a reliability diagram and a risk-coverage curve.
- **Operator trust:** acceptance rate, override rate with reason, time to acknowledge, explanation fact-check pass rate, and "flags whose evidence the operator opened". Even 3–5 classmates as test operators gives honest numbers.

**R8. What to show judges.**
- One "Why operators can trust it" panel: the safety floor ("AI can raise priority, never lower it"), alarm KPIs against ISA-18.2/EEMUA 191 targets, the Milford Haven line, and the ablation table with 0 missed criticals.
- Say plainly that the data is synthetic and small (40 anomalies), so the guarantees are directional.

## 4. Open questions
- What cost ratio C_FN : C_FP would NextEra endorse? Ask a NextEra mentor; until then, state 20:1 as our assumption.
- Can we fine-tune Laya overnight on ~270 labeled actions? The model card says fine-tuning is supported (0.36 → 0.77 on its benchmark), but our sample is very small. Unverified for our domain.
- What is the operator "position" for alarm-rate KPIs: one operator per site, or per robot? This changes what "6/hr" means.
- Conformal recall guarantees on 40 positives will be very loose. Show them as a method, not a claim.
- Dixon et al. 2007: the primary URL is not verified (PubMed fetch failed).
