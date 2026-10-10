# Phase 4 held-out evaluation report

## What this is

One command (`scripts/report.py`) writes `cases.jsonl`, `report.md` and `metrics.json`. The headline section
covers the controlled held-out packets from System 1 fold 2 (`data/heldout_packets.json`: 38 flags in 8 missions;
M019 has no flags). The 6 training-mission dev packets appear in a separate section that is never headline. Every
rate carries a 95% mission-level bootstrap CI (whole missions resampled, 1000 resamples, seed 20261010) and its
k/n flags and mission count.

## Provenance rules

- `template/` is deterministic offline output: no model, GPU or network.
- An `amd-*` directory is valid only when a person ran `report.py` on the gfx1151 box against the local
  llama-server. Nothing in an `amd-*` directory is ever typed or edited by hand.
- Test runs against fake servers are code-path checks, never measurements.

## Reproduce offline

From the repo root:

```bash
uv run --no-project --with-requirements amd/system2/requirements.txt python amd/system2/scripts/report.py --rebuild amd/system2/results/report/<run> --out-dir /tmp/rebuild
```

The rebuild recomputes every number from `cases.jsonl` and the checked-in datasets. It prints
`rebuild: identical`, or exits 4 if anything differs.

## Run on the AMD box

(a) Update the code:

```bash
cd ~/SpotTheDOT && git fetch origin && git checkout aatif/system2 && git pull --ff-only origin aatif/system2
```

(b) Start llama-server if it isn't already running. Check first with `curl -s 127.0.0.1:8080/health`:

```bash
nohup ~/llama.cpp/build/bin/llama-server -m ~/models/q35/Qwen3.5-9B-Q4_K_M.gguf -ngl all -fa on -lm none -c 16384 -np 1 -rea off --host 127.0.0.1 --port 8080 --metrics > ~/llama-server.log 2>&1 &
until curl -s 127.0.0.1:8080/health | grep -q ok; do sleep 2; done; echo READY
```

(c) Run the report. The 38 + 6 cases on two runners take about 5–10 minutes:

```bash
cd ~/SpotTheDOT/amd/system2 && python3 -m pip install --user -q -r requirements.txt && python3 scripts/report.py --runner both --model-url http://127.0.0.1:8080 --model qwen3.5-9b-q4km --label amd-gfx1151-rocm-qwen35-9b-q4km --out-dir results/report/amd-qwen35-9b-q4km
```

(d) Commit and push from the box:

```bash
cd ~/SpotTheDOT && git add amd/system2/results/report/amd-qwen35-9b-q4km amd/system2/results/eval/qwen35-9b-350 amd/system2/results/eval/qwen35-9b-512 && git commit -m "eval(04): AMD gfx1151 held-out report run (Qwen3.5-9B Q4_K_M)" && git push origin aatif/system2
```

(e) If the box can't push, run `tar czf ~/amd-report.tgz -C ~/SpotTheDOT amd/system2/results/report/amd-qwen35-9b-q4km`.
Download it through the Jupyter file browser, run `tar xzf amd-report.tgz` at the laptop repo root, and commit
there with the same message.

If the Phase 3 bakeoff picks a different model, change the gguf path, `--model`, `--label` and `--out-dir`
together, and keep the `amd-gfx1151` label prefix.

## Recorded runs

| Run | Where | Status |
|---|---|---|
| `template/` | offline, deterministic | Recorded 2026-10-10. 38/38 on all four mechanical checks; rebuild is byte-identical |
| `amd-qwen35-9b-q4km/` | AMD gfx1151, Qwen3.5-9B Q4_K_M | **Pending human run** (the Jupyter server was unreachable) |

## Limitations

See the report's `## Limitations and deferred items` section. These items were not built: the different-model
judge (EVAL-02 claim support, EVAL-03 rubric), action quality against human labels (EVAL-04 beyond validator
agreement), and judge-vs-human agreement (EVAL-07). Because the template passes every mechanical check by
construction, these checks show that the model's output is as grounded as the template. They cannot show that it
is better.
