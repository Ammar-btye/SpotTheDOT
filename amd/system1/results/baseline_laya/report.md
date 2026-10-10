# Benchmark: convaiinnovations/laya

_2026-10-10 01:32 · 5491 decisions over 1557 rows · 2.4 rows/s on mps_

Segments: **real** = held-out kit missions (headline), **synthetic** = held-out simulated missions, **counterfactual** = one-field edits that flip the triage label (Track B robustness).

## Per question (macro-F1, accuracy in parentheses)

| Question | Track | Real | Synthetic | Counterfactual | Majority (real) | Real 95% CI |
|---|---|---|---|---|---|---|
| will_fail | A predict | 0.545 (67.4%) | 0.539 (65.0%) | – | 0.455 (83.3%) |  [0.47–0.61] |
| failure_mode | A predict | 0.277 (80.7%) | 0.242 (77.2%) | – | 0.227 (83.3%) |  [0.22–0.41] |
| anomaly_expected | A predict | 0.461 (73.3%) | 0.476 (71.5%) | – | 0.461 (85.6%) |  [0.42–0.50] |
| escalate | B triage | 0.450 (48.1%) | 0.529 (53.0%) | 0.486 (50.0%) | 0.459 (84.8%) |  [0.38–0.50] |
| priority | B triage | 0.159 (17.8%) | 0.187 (25.5%) | 0.251 (32.0%) | 0.191 (61.6%) |  [0.10–0.21] |
| category | B triage | 0.403 (68.9%) | 0.365 (58.5%) | 0.243 (20.0%) | 0.157 (64.4%) |  [0.29–0.46] |
| reading_trust | B triage | 0.509 (56.7%) | 0.510 (57.5%) | 0.453 (50.0%) | 0.253 (61.1%) |  [0.45–0.55] |
| mission_misleading | B triage | 0.625 (63.0%) | 0.447 (47.5%) | – | 0.357 (55.6%) |  [0.49–0.66] |

## Positive-class recall / precision (real segment)

| Question | Recall | Precision | Recall 95% CI |
|---|---|---|---|
| will_fail | 42.2% | 23.5% |  [0.29–0.56] |
| anomaly_expected | 7.7% | 7.7% |  [0.02–0.20] |
| escalate | 80.0% | 19.9% |  [0.67–0.90] |
| mission_misleading | 66.7% | 66.7% |  [0.67–0.67] |

## Calibration (all segments)

| Question | ECE | Brier | Mean confidence |
|---|---|---|---|
| will_fail | 0.104 | 0.476 | 0.634 |
| failure_mode | 0.164 | 0.387 | 0.624 |
| anomaly_expected | 0.127 | 0.422 | 0.677 |
| escalate | 0.130 | 0.524 | 0.638 |
| priority | 0.133 | 0.762 | 0.373 |
| category | 0.069 | 0.665 | 0.491 |
| reading_trust | 0.055 | 0.534 | 0.503 |
| mission_misleading | 0.259 | 0.664 | 0.702 |

## Robustness by rendering (mean macro-F1 over questions)

| Rendering | Mean macro-F1 | Decision accuracy |
|---|---|---|
| json | 0.359 | 52.1% |
| log | 0.390 | 53.7% |
| prose | 0.445 | 61.2% |

## Track A vs classic baselines (real segment, macro-F1 / accuracy)

| Question | Laya (this model) | Logistic regression | Gradient boosting | Majority |
|---|---|---|---|---|
| will_fail | 0.545 / 67.4% | 0.618 / 85.6% | 0.606 / 84.4% | 0.455 / 83.3% |
| failure_mode | 0.277 / 80.7% | 0.301 / 84.4% | 0.275 / 77.8% | 0.227 / 83.3% |
| anomaly_expected | 0.461 / 73.3% | 0.458 / 84.4% | 0.527 / 85.6% | 0.461 / 85.6% |

Harness parity with `laya.load(...).predict`: 100.0% agreement on 85 decisions.
