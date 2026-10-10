# System 2 "Analyst": explaining escalated flags

System 1 (Laya + the deterministic validator, `amd/system1`) decides **what** needs attention. System 2 explains **why it
matters and what to do**: it takes one escalated flag plus a short context packet and returns Orbit-style JSON
(question / answer / reasoning / recommended action). It never decides what gets flagged, and every claim must cite a
row in the packet.

Plan and evidence: `research/tech-system2-context-distill-2026-10-10.md` (recommendations R1–R7).
API contract with `web/`: `docs/ARCHITECTURE.md` §4 (`POST /v1/assess`).

## Build order
1. **Context packet builder** (R1–R2): `flag → packet` JSON under ~1,500 tokens, key facts first, every row with a short
   ID (`F#` derived facts, `S#` asset, `W#` waypoint, `I#` similar incidents). Reads the kit CSVs
   (`amd/system1/data/kit/`) for now; swaps to Neon views later.
2. **Output schema** (R3): `evidence[{claim, ids}]` → `answer` → `question` → `recommended_action` (enum) →
   `confidence` → `insufficient_context`. Grammar-enforced; the `ids` enum is built per packet.
3. **Prompt**: system prompt + 3 few-shot packet→JSON examples, thinking off, `max_tokens` ~350.
4. **Post-check** (R4): every number and asset/waypoint name in the output must appear in the packet; retry once,
   then fall back to a templated explanation.
5. **Test set + eval** (R6): held-out flags; schema validity, citation validity, number consistency, latency.
6. **Serve** on the AMD box behind `/v1/assess`, and precompute explanations for every flag (R7).

Prompt first. Fine-tuning is a gated stretch goal (R5), only if the pipeline works end to end.

## Interface with System 1 (to agree with Tyler)
The fields System 2 receives from Laya / the validator, e.g. `escalate`, `priority`, `category`, `reading_trust`,
their probabilities, and the validator rules that fired. Until that's fixed, the packet builder fakes them from the
kit's severity and the policy in `amd/system1/triage/policy.py`.
