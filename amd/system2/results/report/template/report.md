# System 2 evaluation report

Held-out dataset content 588700df763b, 38 of 38 flags, runners template. Label `unlabelled`, 2026-10-10T15:30:18.856729Z to 2026-10-10T15:30:18.964402Z. Report system2-report-2026-10-10.1.

**Headline-eligible (held-out fold 2, full set).**

## Reproduce

```
python scripts/report.py --runner template --quiet
python scripts/report.py --rebuild /home/aatif101/wsl_projects/SpotTheDOT/amd/system2/results/report/template
```

`--rebuild` recomputes every number below from cases.jsonl and the checked-in held-out dataset, and exits 4 on any difference.

## Headline: held-out fold-2 missions

38 flags in 8 missions (M006, M009, M012, M013, M017, M018, M020, M023). Controlled packets from System 1 fold-2 held-out kit missions: dynamic evidence comes only from the flag's own mission at or before as_of, with no labels, targets or prior generated answers, and few-shots come from the training pool only. Headline numbers only for the full set; grounding is still mechanical consistency, not entailment. Grounding = mechanical consistency with cited packet content (not entailment, not correctness).

Each cell: value [95% CI] (k/n flags, missions). CI = mission-level bootstrap: whole missions resampled with replacement, 2.5/97.5 percentiles, linear interpolation, 1000 resamples, seed 20261010.

### Served output (what the operator sees, after retry/fallback)

| metric | template |
|---|---|
| public response valid | 100.0% [100.0%, 100.0%] (38/38 flags, 8 missions) |
| schema valid | 100.0% [100.0%, 100.0%] (38/38 flags, 8 missions) |
| citation IDs valid | 100.0% [100.0%, 100.0%] (38/38 flags, 8 missions) |
| numbers consistent with cited rows | 100.0% [100.0%, 100.0%] (38/38 flags, 8 missions) |
| names consistent with cited rows | 100.0% [100.0%, 100.0%] (38/38 flags, 8 missions) |
| all four mechanical checks (grounding pass) | 100.0% [100.0%, 100.0%] (38/38 flags, 8 missions) |
| agreement with validator suggested_action | 100.0% [100.0%, 100.0%] (38/38 flags, 8 missions) |

### Model's own output

No model runner in this run.

### By category

| category | template |
|---|---|
| data_quality | 4 flags, 3 missions |
| equipment | 12 flags, 7 missions |
| mission | 6 flags, 6 missions |
| navigation | 2 flags, 2 missions |
| robot_health | 14 flags, 6 missions |

## Speed

Not measured: no model runner in this run.

## Development set (training missions; not headline)

6 flags. Approved development kit packets from training missions only (synthetic kit data, few-shots drawn from the same pool with the current case excluded). Not held-out and not independent real-world observations; never a headline number.

| metric | template |
|---|---|
| public response valid | 6/6 (100.0%) |
| final schema_valid | 5/5 (100.0%) |
| final citation_valid | 5/5 (100.0%) |
| final numeric_consistent | 5/5 (100.0%) |
| final name_consistent | 5/5 (100.0%) |
| agreement with validator suggested_action | 6/6 (100.0%) |
| model output served (llm + retry) | n/a (0) |
| fell back to the checked template | n/a (0) |

## Limitations and deferred items

- **EVAL-02** claim support judged by a different model: not built. Only the mechanical part is reported: schema, citation-ID, numeric and name consistency with the cited packet content.
- **EVAL-03** LLM-vs-template judge rubric: not built. No judge model scores usefulness or clarity; model and template are compared on mechanical checks only.
- **EVAL-04** action quality against human labels: not built. Only agreement with the validator's suggested_action is reported. That is agreement, not accuracy.
- **EVAL-07** judge-vs-human agreement: not built. Neither a judge nor human labels exist, so their agreement cannot be measured.
- **grounding** entailment / correctness of claims: not built. Grounding means mechanical consistency with cited packet content (not entailment, not correctness).
- **comparison** evidence that the model beats the template: not built. The template passes the mechanical checks by construction (it copies cited rows), so mechanical parity is expected and is not evidence that the model is better.
- **sample size** tight intervals: not built. n is small (38 flags in 8 held-out missions), so the mission-level CIs are wide.
- **data** independent real-world observations: not built. "Real" means sponsor kit missions as opposed to simulator output; the kit itself carries synthetic=True metadata. No synthetic or unrestricted-retrieval results are included.

## Method

- Held-out packets: System 1 fold-2 kit missions; dynamic evidence only from the flag's own mission at or before as_of; no labels, targets or prior answers; few-shots from the training pool only.
- Both runners see the identical normalized packet per flag (packet hashes checked) and finish in the same checker. A fallback is the checked template and never counts as model success.
- Rates: k/n over the stated denominator; failed, timed-out and fallback flags stay in it. Rows for packets marked insufficient are excluded from the final-check denominators.
- CI: mission-level bootstrap: whole missions resampled with replacement, 2.5/97.5 percentiles, linear interpolation; 1000 resamples; seed 20261010; fewer than 2 missions gives no CI.
- Identity hash c363cdfa7bfa; code revision baa4d63fec65.
