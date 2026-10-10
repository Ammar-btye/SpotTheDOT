# Completed SRV-00 evidence index

AMD GPU feasibility is complete, recorded 2026-10-10. No new GPU run was performed for this audit.

| Recorded observation | Value |
|---|---|
| GPU | Radeon 8060S, gfx1151 |
| Model | Qwen3.5-9B Q4_K_M |
| Backend | llama.cpp ROCm/HIP |
| Offload | 33/33 layers on ROCm0 |
| Valid replies | 3/3 under the original checker |
| Prompt tokens | 1450 |
| Output tokens | 439 |
| Request time | 12.4 seconds |
| Generation throughput | 35.6 tokens/s |

## Provenance and limits

GPU figures come from the recorded README observation in commit `e4a8386c42efa69afa67296951c56b6e7ef4335f`
(2026-10-10), also preserved in `.planning/STATE.md`'s SRV-00 decision and `.planning/REQUIREMENTS.md`.
The original smoke client is commit `6b18d04dd7ace4d4d83bdbb15a6fb28c6386cf6a`.
No original GPU JSON/logs were found in repository results, `/tmp`, or known local agent session artifacts.
These are recorded observations, not reconstructed raw measurements.

Two existing scratchpad artifacts are explicitly `backend=test`, `model=fake`, hence client regression evidence,
not GPU measurements:

- [Valid fake-server JSON](/tmp/claude-1000/-home-aatif101-wsl-projects-SpotTheDOT/bb2b7c88-ba0b-45c2-a4e8-ab8baef5bd4b/scratchpad/smoke/20261010T103110Z.json)
- [Unknown-citation fake-server JSON](/tmp/claude-1000/-home-aatif101-wsl-projects-SpotTheDOT/bb2b7c88-ba0b-45c2-a4e8-ab8baef5bd4b/scratchpad/smoke/20261010T103111Z.json)

These absolute local links are ephemeral; no files were copied or relabeled as GPU results.
Original validity checked exact keys/order, citation membership, action and confidence enums. It did not fully
verify field types, evidence shape, citation minimums or caps. Current checker and HTTP fake-server regressions
cover those constraints; absent original replies cannot be retrospectively checked.

Prompt throughput reflected warm prompt cache. Cold prefill remains unmeasured. Vulkan was not benchmarked.
439 output tokens exceed the proposed 350-token cap: Phase 2 must shorten evidence or raise max_tokens to
approximately 512 and evaluate latency/truncation. No p95 latency or production pipeline result is claimed.

## Optional replay

With the documented ROCm llama-server running on 8080, from `amd/system2`:

```bash
python3 scripts/smoke_serve.py --backend rocm --runs 3 --max-tokens 1024
```

This uses legacy offline `fixtures/equipment.json` and lowercase actions. The current HTTP contract is
[backend-services-contract.md](../../../../docs/backend-services-contract.md).
New runs write timestamped JSON here; this index never manufactures historical result files.
