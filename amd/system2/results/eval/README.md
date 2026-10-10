# Recorded AMD evaluation runs

## 2026-10-10: Qwen3.5-9B Q4_K_M on gfx1151 (Phase 2 UAT)

**Provenance.** Copied by hand from the AMD box terminal output (Radeon Cloud Jupyter VM `jupyter-amducf07`) and
pasted into the planning session. The raw `cases.jsonl` / `metrics.json` / `report.md` files from this run are
in `~/SpotTheDOT/amd/system2/results/eval/qwen35-9b-{350,512}/` on the box. They were not committed before the
Jupyter server became unreachable (502); commit them from the box when it is back. Until then, this file is
the record.

**Not headline numbers.** The 6 cases are approved development packets from training missions (synthetic kit
data), with few-shots drawn from the same pool. Not held-out and not independent real-world observations.
Grounding means mechanical consistency with the cited packet content, not entailment or correctness.

### Setup

| | |
|---|---|
| Code | `aatif/system2` at `e3a57a9` |
| GPU / backend | Radeon 8060S (gfx1151), llama.cpp ROCm/HIP build in `~/llama.cpp` |
| Model | `~/models/q35/Qwen3.5-9B-Q4_K_M.gguf` |
| Server | `llama-server -ngl all -fa on -lm none -c 16384 -np 1 -rea off --host 127.0.0.1 --port 8080 --metrics` |
| Dataset | `data/dev_packets.json`, content `d7cafc688b6f`, 6 of 6 cases, split train |
| Label | `amd-gfx1151-rocm-qwen35-9b-q4km` |

### Schema-enforcement probe

The probe used a schema with `id` limited to the single value `"F7"` and `note` capped at `maxLength: 20`. The
prompt asked for `F99` and a 200-word note. The server returned `{"id": "F7", "note": "Pumps are mechanical"}`
(exactly 20 characters), so this build enforces single-value enums and `maxLength`.

### Run 1: `--max-tokens 350` (default), 2026-10-10T14:25:06Z to 14:25:37Z

| metric | template | model |
|---|---|---|
| public response valid | 6/6 (100.0%) | 6/6 (100.0%) |
| model accepted (llm+retry) | n/a (0) | 5/5 (100.0%) |
| retry | n/a (0) | 0/5 (0.0%) |
| fallback to template | n/a (0) | 0/5 (0.0%) |
| guarded insufficient: safe manual review | 1/1 (100.0%) | 1/1 (100.0%) |
| first attempt schema_valid | n/a (0) | 5/5 (100.0%) |
| first attempt citation_valid | n/a (0) | 5/5 (100.0%) |
| first attempt numeric_consistent | n/a (0) | 5/5 (100.0%) |
| first attempt name_consistent | n/a (0) | 5/5 (100.0%) |
| final schema_valid | 5/5 (100.0%) | 5/5 (100.0%) |
| final citation_valid | 5/5 (100.0%) | 5/5 (100.0%) |
| final numeric_consistent | 5/5 (100.0%) | 5/5 (100.0%) |
| final name_consistent | 5/5 (100.0%) | 5/5 (100.0%) |
| action agreement with validator | 6/6 (100.0%) | 6/6 (100.0%) |
| action quality (independent refs) | n/a (0) | n/a (0) |
| latency p50 / p95 ms (nearest-rank) | 1 / 2 | 5302 / 7916 |

Per-attempt detail for the model runner (case, path, status, finish_reason, completion tokens, errors):

```
kit-data_quality llm accepted stop 188 []
kit-equipment llm accepted stop 225 []
kit-mission llm accepted stop 167 []
kit-navigation llm accepted stop 230 []
kit-robot_health llm accepted stop 116 []
{'accepted': 5}
```

### Run 2: `--max-tokens 512`, 2026-10-10T14:26:00Z to 14:26:28Z

All rows are identical to Run 1 except latency: model p50 / p95 **5283 / 6580 ms** (template 1 / 2 ms).

### What this shows

- The real llama-server enforces the per-packet schema: 5/5 first attempts were schema-valid with no parse
  errors.
- The 350-token cap is enough on these cases. No reply was truncated; all stopped at 116–230 tokens, compared
  with 439 for the uncapped Phase 1 smoke prompt.
- The 9B model is inside the 15 s budget: p95 6.6–7.9 s.
- On these 6 cases the model does not beat the template on mechanical checks (both 5/5). Showing an advantage
  needs held-out packets and a quality judge or human labels (Phase 4).
- Not measured: peak GPU memory, and throughput in tokens per second (it is in the raw `metrics.json` on the box).

## Model decision (2026-10-10, provisional)

**Qwen3.5-9B Q4_K_M is the serving model for now** (`SYSTEM2_MODEL=qwen3.5-9b-q4km`), based on Run 1 / Run 2
above: 5/5 first-attempt accepted, 0 truncated at 350 tokens, p95 7.9 s (350) / 6.6 s (512), inside the 15 s budget.

Limits: these are 6 training dev cases, not headline numbers; peak GPU memory and tokens/s for this run are not yet
recorded; on mechanical checks the model ties the template (5/5 each).

**MOD-01 pending.** The 27B and 35B-A3B runs on the same harness and packets wait for the AMD box (the Jupyter
server returned 502). When it is back, run `scripts/evaluate.py --runner both` with each model's own `--model`,
`--label` and `--out-dir`, record grounding pass / fallback rate, p95 latency and peak GPU memory (`amd-smi`), and
switch `SYSTEM2_MODEL` only if another model wins within 15 s p95.

**Live /v1/assess check: PENDING (human, AMD box).** Run llama-server plus `scripts/serve.py` in live mode on the
box, curl `/v1/assess` twice (expect `X-System2-Cache: miss` then `hit`), and run `scripts/precompute.py` on a fresh
`SYSTEM2_CACHE_DIR` for live-pipeline p50/p95 (steps in docs/RUNNING.md, "Live mode"). Numbers replace this line.
