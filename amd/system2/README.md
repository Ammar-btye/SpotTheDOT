# System 2 "Analyst": explaining escalated flags

System 1 (Laya + the deterministic validator, `amd/system1`) decides **what** needs attention. System 2 explains **why it
matters and what to do**: it takes one escalated flag plus a short context packet and returns Orbit-style JSON
(question / answer / reasoning / recommended action). It never decides what gets flagged, and every claim must cite a
row in the packet.

Plan and evidence: `research/tech-system2-context-distill-2026-10-10.md` (recommendations R1–R7).
The authoritative HTTP contract is [docs/backend-services-contract.md](../../docs/backend-services-contract.md)
(`2026-10-10.backend.1`). Backend owns retrieval through MCP/SQL fallback and supplies `context`.
The HTTP path does not build its own kit/Neon packet. Phase 1 `analyst/contract.py`, `schema/`, and
`fixtures/*.json` remain legacy offline artifacts, including inputs for the serving feasibility smoke.

## Current backend HTTP transport

`POST /v1/assess` takes strict positive integer `flag_id`, object `flag`, and object `context`, with optional
`request_id`, `event`, and `reasons`. The flat response contains `evidence[{claim,ids}]`, `answer`, `question`,
`recommended_action`, `confidence` (`low | medium | high`), `insufficient_context`, `flag_id`, `model`,
`latency_ms`, `tokens_per_sec`, and `path`. Actions use uppercase MCP vocabulary and packet membership;
`MANUAL_REVIEW` is the documented safe extension. Citations resolve to actual supplied content.
This phase serves `model=stub`; the full prompt/model pipeline remains Phase 2 work.

The published response schema enforces empty evidence, low confidence, `MANUAL_REVIEW`, and
the insufficient path when context is insufficient; complete assessments require evidence and the stub path.
Citation resolution and membership of the recommended action in the supplied packet remain runtime checks,
because the static response schema has no access to that request's content or allowed actions.

Six current fixture pairs are `fixtures/backend/equipment.json`, `fixtures/backend/robot_health.json`,
`fixtures/backend/navigation.json`, `fixtures/backend/data_quality.json`, `fixtures/backend/mission_health.json`,
and `fixtures/backend/insufficient_context.json`. Use their `request` objects for HTTP calls.

Native/compose System 2 port is **8083**; llama-server remains 8080. `SYSTEM2_API_KEY` is the primary secret;
`AMD_API_KEY` is the compatibility alias. See [RUNNING.md](../../RUNNING.md) for current startup and compose.
Authorization via `X-API-Key` precedes body parsing; `/health` is open. Native binds loopback; remote access uses
`ssh -L 8083:127.0.0.1:8083 <user>@<amd-box>`. Compose callers use `http://system2:8083`.

## Historical Phase 1 build order (offline)
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

## Legacy offline contract
All models live in `analyst/contract.py` and reject unknown fields (an extra field gets a 422). Types are strict, so
the server accepts exactly what the exported JSON Schema allows: `"yes"` is not a boolean, `"5"` is not an integer,
and a number is not a timestamp.

Timestamps are **naive** ISO 8601 strings in kit site time, with no offset and no `Z`, e.g. `"2026-09-01T18:27:54"`
(optionally with up to 6 fractional-second digits). This is the only form the kit CSVs use. A timestamp with an offset
or `Z` gets a 422, so send JavaScript dates as local site time, not `toISOString()`. The schema states this as a
`pattern` instead of `format: date-time`, because RFC 3339 date-time requires an offset.

| Model | What it is |
|---|---|
| `Flag` | One escalated System 1 flag: ids, `kind` (action or mission), `category`, `priority`, `escalate`, `reading_trust`, the validator `reasons`, optional `scores`. |
| `ContextPacket` | The cited context System 2 builds for the flag: `event`, `facts`, `asset`, `waypoint`, `incidents` rows, `allowed_actions`, `missing` sections, and the `question`. |
| `Explanation` | The answer: cited `evidence`, `answer`, `question`, `recommended_action`, `confidence`, `insufficient_context`. |
| `Meta` | How the answer was made: `model`, `prompt_ver`, `path`, `latency_ms`, `tokens_per_sec`, `packet_hash`. |
| `AssessRequest` | The request body of `POST /v1/assess`: just `{"flag": {...}}`. System 2 builds the packet itself. |
| `AssessResponse` | The response: `contract_version`, `flag_id`, `explanation`, the `packet` it is grounded in, and `meta`. |

Packet row IDs are a prefix letter plus a number (`E1`, `F3`, `I2`): `E` event, `F` derived facts, `S` asset,
`W` waypoint, `I` similar incidents. Every evidence item cites one or more of these IDs, and the contract rejects a
citation to a row that is not in the packet.

`Explanation` fields always come in this order: `evidence`, `answer`, `question`, `recommended_action`, `confidence`,
`insufficient_context`. The order is part of the contract (the model writes evidence before its answer), so never
reorder fields. `confidence` is `low`, `med` or `high`. `meta.path` is `first_pass`, `retry`, `fallback` or
`insufficient_context`.

`recommended_action` must be one of the packet's `allowed_actions`, which come from this table. Only
`manual_review` is guaranteed: the contract rejects a packet whose `allowed_actions` lacks it. `monitor` is listed
for every category, but a packet may leave it out. `mission_health` flags allow every action. When
`insufficient_context` is true, the action is always `manual_review`, `evidence` is empty and `confidence` is `low`.

| Action | Meaning | Allowed for |
|---|---|---|
| `dispatch_technician` | Send a person to the asset now. | equipment, mission_health |
| `schedule_maintenance` | Book a planned work order; not urgent. | equipment, data_quality, mission_health |
| `reinspect_next_mission` | Add the waypoint to the next SPOT route. | all categories |
| `verify_reading_manually` | Take the reading by hand; the robot's value is not trusted. | data_quality, mission_health |
| `recharge_robot` | Dock and charge SPOT before further work. | robot_health, mission_health |
| `check_robot_comms` | Inspect SPOT's radio/network link. | robot_health, mission_health |
| `clear_route_obstruction` | Remove whatever blocks the path. | navigation, mission_health |
| `relocalize_robot` | Re-run localization / fiducial check. | navigation, mission_health |
| `monitor` | No action now; watch the trend. | all categories |
| `manual_review` | A human must look; System 2 cannot tell. | all categories |

Any change to the wire format bumps `CONTRACT_VERSION` in `analyst/contract.py`, and the JSON Schemas are then
re-exported with `python scripts/export_schema.py`.

## Legacy offline fixtures
Each file in `fixtures/` holds a `request` and the `response` System 2 should give. Every one is built from real kit
data from training missions only, and every number in its explanation appears in its packet.

| File | Kit event | Category | `meta.path` it shows |
|---|---|---|---|
| `fixtures/equipment.json` | `act-A0009` (mission M001): failed visual inspection of Heat Exchanger 08 | equipment | `first_pass` |
| `fixtures/robot_health.json` | `act-A0010` (M001): inspection run at 15% battery | robot_health | `retry` |
| `fixtures/navigation.json` | `act-A0037` (M004): localization issue at WP06 | navigation | `first_pass` |
| `fixtures/data_quality.json` | `act-A0030` (M003): sensor timeout, questionable reading | data_quality | `fallback` (templated explanation) |
| `fixtures/mission_health.json` | `mis-M001`: mission reported COMPLETED with 2 of 10 actions failed | mission_health | `first_pass` |
| `fixtures/insufficient_context.json` | `act-A9999`: an action the data source cannot resolve | data_quality | `insufficient_context` |

The stub answers each request with the matching fixture's response, stamped with the caller's flag and
`meta.model = "stub"` (so stub output can never pass for model output). It keeps the fixture's `meta.path`, so web can
render every UI state. A request whose `flag_id` matches a fixture gets that fixture; otherwise it gets its category's
fixture.

## Historical Phase 1 stub commands (superseded)
The commands below document the original offline fixture stub on 8000. For current HTTP startup, use
`SYSTEM2_API_KEY=your-shared-secret uv run --no-project --with-requirements requirements.txt python scripts/serve.py --port 8083`
from `amd/system2`, and send a `fixtures/backend/` request. The flag-only request and nested response below
describe Phase 1 history, not the current service.
Setup on the AMD box, from `amd/system2`:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Start it, from `amd/system2` (one command). The key must be at least 16 printable ASCII characters with no leading or
trailing whitespace (watch for a trailing space or tab in a `.env` line), and it is never logged. The server compares
keys in constant time (`hmac.compare_digest`).

```bash
AMD_API_KEY=your-shared-secret uv run --no-project --with-requirements requirements.txt python scripts/serve.py
```

With the venv instead of uv: `AMD_API_KEY=your-shared-secret .venv/bin/python scripts/serve.py`. Flags: `--port`
(default 8000), `--host` (default `127.0.0.1`), `--fixtures`, `--log-level`. Without a valid key the script exits with
code 2 before binding any port.

Call it:

```bash
python3 -c "import json; print(json.dumps(json.load(open('fixtures/equipment.json'))['request']))" > /tmp/req.json
curl -s -X POST http://127.0.0.1:8000/v1/assess \
  -H "X-API-Key: $AMD_API_KEY" -H "Content-Type: application/json" --data @/tmp/req.json
```

| Endpoint | Auth | Returns |
|---|---|---|
| `GET /health` | open | `{"status": "ok", "mode": "stub", "contract_version": ..., "fixtures": 6}` |
| `POST /v1/assess` | `X-API-Key` header | an `AssessResponse` |

There are no `/docs`, `/redoc` or `/openapi.json` routes: the committed `schema/*.json` files are the published
contract. Every path except `/health` needs the key (a keyless request to any other path gets 401).

Status codes for `POST /v1/assess`:
- **200**: a schema-valid `AssessResponse`.
- **401**: missing or wrong `X-API-Key`. The key is checked in middleware before the body is read, so a request
  without a valid key gets 401 even when its body is not valid JSON.
- **422**: malformed flag (wrong type, unknown field, broken kind/category rule).
- **501**: no fixture covers the flag's category.

The server binds `127.0.0.1` and never a public interface by default (it warns if you pass a non-loopback `--host`).
To reach it from a laptop, open an SSH tunnel to the box: `ssh -L 8000:127.0.0.1:8000 <user>@<amd-box>`, then call
`http://127.0.0.1:8000` locally.

## Tests and schemas
From `amd/system2`:

```bash
uv run --no-project --with-requirements requirements.txt python -m pytest -q
python scripts/export_schema.py            # regenerate schema/*.json after a contract change
python scripts/export_schema.py --check    # exit 1 if a committed schema no longer matches the contract
```

`schema/` holds the legacy offline generated JSON Schemas: `flag.schema.json`, `packet.schema.json`,
`assess_request.schema.json` and `assess_response.schema.json`. Do not edit them by hand.

## Serving smoke test (AMD box)
SRV-00 is already complete. This optional replay is not an execution prerequisite.
See [evidence index](results/smoke/README.md) for the recorded GPU result's provenance and limits.
Proves one model loads on the gfx1151 GPU and answers one JSON-schema-constrained request (Phase 1.1, SRV-00). The
Radeon Cloud Jupyter VMs have no root and no Docker, so llama.cpp is built in the home folder:

```bash
hf download unsloth/Qwen3.5-9B-GGUF Qwen3.5-9B-Q4_K_M.gguf --local-dir ~/models/q35
git clone https://github.com/ggml-org/llama.cpp ~/llama.cpp && cd ~/llama.cpp
HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" \
  cmake -S . -B build -DGGML_HIP=ON -DGPU_TARGETS=gfx1151 -DCMAKE_BUILD_TYPE=Release && cmake --build build -j "$(nproc)"
~/llama.cpp/build/bin/llama-server -m ~/models/q35/Qwen3.5-9B-Q4_K_M.gguf \
  -ngl all -fa on -lm none -c 16384 -rea off --host 127.0.0.1 --port 8080 --metrics
# from amd/system2, in another terminal:
python3 scripts/smoke_serve.py --backend rocm --runs 3 --max-tokens 1024
```

No ROCm on the machine: use the Vulkan prebuilt (`llama-<ver>-bin-ubuntu-vulkan-x64.tar.gz` from the llama.cpp
releases) and `--backend vulkan`. Older builds reject `-ngl all`, `-lm` or `-rea`; use `-ngl 999 --no-mmap`.

**Result (2026-10-10, Qwen3.5-9B Q4_K_M, ROCm build, Radeon 8060S):** 33/33 layers offloaded to `ROCm0`, 3/3 replies
valid under the original checker, 12.4 s per request for 1,450 prompt and 439 output tokens, generation 35.6 tok/s. Latency is generation-bound,
so the output length is the main lever: 439 tokens exceeds the planned ~350 cap (the reply would truncate), so Phase 2
caps the evidence list or raises `max_tokens` to ~512. The reported prompt tok/s reflects a warm prompt cache; rerun
with an unseen `--fixture` for cold prefill speed.
Cold prefill remains unmeasured; Vulkan was not benchmarked. The current checker validates the complete emitted
schema, including evidence shape/types/caps; original validation checked keys/order and citation/action/confidence
membership only. Current regression coverage is not a retrospective validation of absent raw GPU replies.

## Historical offline interface with System 1 (superseded on HTTP)
The `Flag` model in `analyst/contract.py` is now the agreed shape for System 1 to conform to: `escalate`, `priority`,
`category`, `reading_trust`, their probabilities in `scores`, and the validator rules that fired in `reasons`.
Action-level flags use `kind` "action" with one of the four action categories. Mission-level flags use `kind`
"mission" with `category` "mission_health". Until System 1 emits flags, the packet builder fakes them from the kit's
severity and the policy in `amd/system1/triage/policy.py` (with `source` "policy").
