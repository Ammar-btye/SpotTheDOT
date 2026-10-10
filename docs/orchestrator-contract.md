# Orchestrator contract (LangGraph, port 8085)

Companion to `docs/backend-services-contract.md` (System 1, System 2, backend) and `docs/system2-rag-contract.md`
(MCP). **Change this file first, then code** (`amd/orchestrator/`). Version marker: `2026-10-10.orchestrator.2` (`.2`, audit fixes: demo images never judge the asset, `source:
"system2_template"`, vision row `flags`/`bound`, caller `vision`/`ocr` stripped, `image_kind` enum, image-aware System 2
budget, `/v1/ask` `cited`/`retrieved`).

The orchestrator is one container that runs two LangGraph graphs:
- **assess** (`POST /v1/assess`): the deterministic per-flag pipeline MCP context -> System 1 -> route -> vision ->
  System 2 -> finalize. The model never calls tools on this path (decision "System 2 does not call tools on
  /explain" still holds); System 2 enforces grounding, and the orchestrator passes its answer through unchanged.
- **ask** (`POST /v1/ask`): a new, separate chat path. The System 2 model (gateway alias `system2`) may call the
  read-only MCP tools in a bounded loop (at most 4 calls, 30 s).

It talks to everything over HTTP: the MCP server (`MCP_URL`, streamable HTTP JSON-RPC), the LiteLLM gateway
(`GATEWAY_URL`, OpenAI-compatible, aliases `system1` and `system2`), the vision service (`VISION_URL`,
`docs/vision-contract.md`) and System 2 (`SYSTEM2_URL`, `/v1/assess`). It has no database access.

## Auth
Every route except `GET /health` and `GET /v1/graph` requires `X-API-Key: <ORCHESTRATOR_API_KEY>` (constant-time
compare; 401 `{"detail": "missing or invalid X-API-Key"}`). The key must be at least 16 printable ASCII characters
with no surrounding whitespace; the service refuses to start without one unless `ORCHESTRATOR_ALLOW_NO_AUTH=1`
(tests and local experiments only).

## POST /v1/assess
```json
{"flag_id": 42, "request_id": "r-123", "image_b64": "<base64 or data: URL>", "image_kind": "thermal",
 "action_type": "THERMAL_INSPECTION", "refresh": false, "return_image": false,
 "context": { "...optional prefetched get_flag_context packet..." }}
```
| Field | Meaning |
|---|---|
| `flag_id` | required, integer >= 1 |
| `request_id` | optional; else `X-Request-ID`; else generated `o-<12 hex>`. Forwarded to MCP, gateway, vision, System 2 |
| `image_b64` | optional inspection image (operator-supplied, `pairing: "linked"`). Max `ORCH_MAX_IMAGE_B64` chars; 422 if not base64 |
| `image_kind` | optional vision `kind`, one of `auto`, `thermal`, `gauge`, `spectrogram`, `acoustic_imager`, `orbit_screenshot`, `visual` (`docs/vision-contract.md`; anything else is 422); default `auto` (the vision router uses `action_type`) |
| `action_type` | optional; else the packet's `event.action_type`. Drives the vision router and the demo-image mapping |
| `refresh` | accepted for parity with the backend's `/explain`; the orchestrator has no cache (System 2 and the backend own caching) |
| `return_image` | include `vision.annotated_image_b64` in the response (default false: keeps responses small) |
| `context` | optional MCP packet the caller already has (e.g. the backend's SQL fallback packet); skips `load_context`. Any `vision` / `ocr` keys in it are dropped: only rows the orchestrator got from the vision service are sent to System 2 (and so citable) |

### Graph
```
START -> load_context -> system1 -> route -?-> vision -> system2 -> finalize -> END
                                          |-> system1_only -> END     (no escalation signal)
                                          \-> finalize               (no_context)
```
| Node | Does | Budget (env, default) |
|---|---|---|
| `load_context` | MCP `get_flag_context(flag_id)` (or the request's `context`) | `ORCH_CONTEXT_BUDGET_S` 15 s, and at most 40 % of the deadline |
| `system1` | Laya answers: the packet's `system1` items when present (`source: "packet"`); else gateway alias `system1` with a canonical event rebuilt from the packet (`source: "gateway"`); failure is tolerated (`source: "none"`) | `ORCH_SYSTEM1_BUDGET_S` 6 s |
| `route` | the System 1 -> System 2 routing rule below | - |
| `vision` | only with an image: the request's `image_b64` (`pairing: "linked"`), else with `DEMO_IMAGES=1` the kit sample for the action type (`pairing: "demo"`); calls `POST {VISION_URL}/v1/vision` with `X-API-Key: $VISION_API_KEY` | `ORCH_VISION_BUDGET_S` 12 s, and never more than what is left after keeping `ORCH_SYSTEM2_IMAGE_BUDGET_S` for System 2 (floor 3 s) |
| `system2` | `POST {SYSTEM2_URL}/v1/assess` (backend request shape + `context.vision`, `context.ocr`, `context.system1`, top-level `image_b64`) | `ORCH_SYSTEM2_BUDGET_S` 20 s without an image (System 2's 15 s generation deadline + its checks); `ORCH_SYSTEM2_IMAGE_BUDGET_S` 28 s when an image is sent (System 2's `SYSTEM2_IMAGE_DEADLINE_S` 25 s + checks); capped by what is left |
| `system1_only` | the short System 1 answer (no vision, no System 2) | - |
| `finalize` | System 2's answer, else the deterministic template | - |

Global deadline `ORCH_DEADLINE_S` (default 40 s: below the backend's `REQUEST_DEADLINE_S` of 45 s, whose
orchestrator call is capped at 45 - 3 s reserve = 42 s, so the backend always gets the answer in time to store it;
the full chain is in `docs/RUNNING.md` "Timeouts and keys"). Each node gets
`min(node budget, time left - reserve)` where reserve = `min(3 s, 10 % of the deadline)`; a node with no time left is
`skipped` and the request still finishes with the template. Never a hang, never a 500 for a dependency failure.

Timeout chain for a request **with an image** (operator upload or demo image):
`backend REQUEST_DEADLINE_S 45` -> orchestrator call <= 42 s -> `ORCH_DEADLINE_S 40` (reserve 3 s) -> `vision`
<= min(12 s, time left - 28 s), at least 3 s -> `system2` node <= 28 s -> System 2 `SYSTEM2_IMAGE_DEADLINE_S 25`
(two attempts; the image call keeps 8 s back and, if it times out, the same attempt is re-sent text-only) -> the
gateway's `system2-vision` timeout 30 s is never the binding one. Typical: context ~1 s, vision ~1-3 s, System 2
<= 28 s, total <= ~33 s. Text-only requests keep `system2` 20 s / System 2 15 s. Env vars for compose: see
`amd/AUDIT-FOLLOWUPS.md`.

### Routing rule (System 1 -> System 2)
The flag takes the **full** path (vision + System 2) when ANY of these hold; each one that fired is listed in
`route_reasons`:
1. `laya_escalate`: System 1's latest `escalate` answer is `A` (escalate).
2. `laya_priority`: System 1's `priority` answer is `P1` or `P2`.
3. `flag_escalated` / `flag_priority`: the stored flag is `escalated: true` or its priority is `P1`/`P2`.
4. `validator`: the packet's validator (`event.validator` or `event.mission.validator`) says `escalate: A` or
   priority `P1`/`P2`.
5. `rules_fired`: the flag's `reasons` contain a fired policy rule (any rule other than `laya_verdict`,
   `rules_verdict`, `laya_unavailable`).
6. `operator_image`: the caller supplied `image_b64` (the operator asked for a visual check; demo images do not count).

Stored flags are already escalated at ingest: the backend runs System 1 (Laya) plus the rules when an event arrives
and only escalated events become flags, so for a stored flag `flag_escalated` (or `validator`/`rules_fired`) almost
always fires. The System 1 -> System 2 routing saving therefore happens **at ingest** (routine events never become
flags and never reach System 2); `system1_only` here applies to un-escalated items, e.g. a routine flag created by
hand, a prefetched `context` for an event that was not escalated, or a packet whose flag was de-escalated.

Otherwise **system1_only**: no vision, no System 2 call; the `system1_only` node returns a short System 1 answer
(`source: "system1"`, action limited to `MONITOR` / `NO_ACTION` / `REINSPECT_NEXT_ROUTE`). Without a context packet the route is **no_context** and `finalize` returns the template
with `insufficient_context: true` and `context_source: "none"` (the backend then runs its own path, which has a SQL
fallback).

### Vision rows sent to System 2
Each vision reading becomes one citable row `V#`:
`{id, tool, kind, quantity, value, unit, confidence, trust, flags, bound, pairing, logged_id, logged_value, delta,
agrees}`.
- `trust` is `HIGH` when `confidence >= VISION_TRUST_MIN` (0.5), else `LOW`; a reading flagged `AMBIGUOUS_NEEDLE` or
  `DEFAULT_SWEEP` is always `LOW`.
- `flags`: the reading's flags plus, on the compared reading, the comparison's flags (uppercase tokens such as
  `CLIPPED`, `LABEL_OUTLIER`, `USED_HINT`, `RELATIVE_ONLY`, `VISION_CLIPPED`, `LOW_CONFIDENCE`; at most 8).
  `CLIPPED` keeps `HIGH` and adds `"bound": "lower"` (the value is a lower bound).
- Comparison (**`linked` images only**): the vision `comparison` block (logged vs vision value) is attached to the
  reading named by `comparison.vision_id` (else the first reading), with `logged_id` = the packet's reading id
  (e.g. `reading:R0042`). `logged` sent to the vision service is the packet's first reading (`event.readings[0]`).
- **Demo images never judge the asset.** For `pairing: "demo"` the orchestrator sends no `logged` reading to the
  vision service (so there is no comparison and no `vision.compare` alert), never puts `logged_*`/`delta`/`agrees`
  on a demo row, and moves the image's own `alert` (e.g. "Thermal hotspot 100 °C", severity 4, which describes the
  sample image) to `vision.demo_alert`; `vision.alert` is `null`. System 2 also ignores comparison fields on demo rows.
- Null fields are dropped; System 2 drops value/delta/agrees from LOW rows itself.
- Only rows produced here are sent: `vision`/`ocr` keys in the MCP packet or a caller's `context` are removed first.

OCR lines: the top `OCR_TOP_N` (8) by confidence, as `[{text, conf}]`. The image sent to System 2 is the annotated
image when the vision service returned one, else the original. Vision failure is tolerated (System 2 still gets the
original image, no `vision` rows).

### Response (200)
```json
{"flag_id": 42, "request_id": "r-123", "route": "full", "route_reasons": ["flag_escalated", "rules_fired"],
 "source": "system2", "question": "...", "answer": "...", "reasoning": "...",
 "recommended_action": "DISPATCH_TECHNICIAN", "recommended_action_code": "DISPATCH_TECHNICIAN",
 "severity_assessment": null, "confidence": 0.85, "model": "qwen3.5-9b", "latency_ms": 7900,
 "tokens_per_sec": 35.6, "insufficient_context": false, "evidence": [{"claim": "...", "ids": ["F1"]}],
 "citations": ["F1", "reading:R1"], "fallback_reason": null,
 "system2": { "...System 2 /v1/assess response verbatim (path, model, ...)..." },
 "system1": {"source": "packet", "model": null, "answers": [{"id": "s1:9", "when": "action", "q": "escalate",
             "answer": "A", "p": 0.83}]},
 "vision": {"pairing": "demo", "kind": "thermal", "rows": [{"id": "V1", "...": "..."}], "ocr": [{"text": "100", "conf": 0.9}],
            "key_results": [], "alert": null, "demo_alert": {"title": "Thermal hotspot ...", "severity": 4,
            "source": "vision.thermal"}, "router": {}, "latency_ms": 640, "version": "...", "annotated_image_b64": null},
 "context_source": "mcp", "graph": "assess", "contract_version": "2026-10-10.orchestrator.2",
 "deadline_s": 40, "elapsed_ms": 9100,
 "trace": [{"node": "load_context", "ms": 410, "status": "ok", "detail": "mcp packet, 14 citation ids"}]}
```
- `source`: `system2` (System 2's model answered; its answer and evidence pass through unchanged),
  `system2_template` (System 2 answered, but with its own checked template: `system2.path` is `fallback` or
  `insufficient_context`, or `system2.model` is `template`; passed through unchanged, `fallback_reason` says so; the
  backend stores it like `template`, never as a model answer), `template` (System 2 unset, down, invalid or out of
  time; the orchestrator's own template, `fallback_reason` says why), `system1` (routed `system1_only`).
- The orchestrator's template prints vision rows as follows: a LOW-trust row says the reading is unreliable and
  never prints its value or comparison; a HIGH row prints its value (`at least` for `bound: lower`) and one of three
  comparison states, `agrees`, `disagrees` or `not judged` (`agrees` null or missing); a demo row is always
  `not judged` and labelled as a sample image. Only HIGH-trust `linked` rows are cited.
- The answer fields mirror the backend's stored assessment (`backend/app/services/system2.py`
  `normalize_assessment` / `template_explanation`): `confidence` is numeric (high/medium/low -> 0.85/0.6/0.35);
  for System 2, `recommended_action` is the action code; for templates it is `"CODE: text"`.
- `trace[].status` ∈ `ok | skipped | error | timeout | fallback`. `system1`/`vision` are `null` when not run.
- 401 bad key, 422 malformed body. Dependency failures are never errors: they show in `trace` and `fallback_reason`.

## POST /v1/ask
```json
{"question": "What does the Spot manual say about docking at low battery?", "flag_id": 42, "max_steps": 4}
```
-> 200
```json
{"answer": "... [manual:12] ...", "citations": ["manual:12"], "cited": true,
 "retrieved": ["manual:12", "manual:3", "policy:battery_low"],
 "tool_calls": [{"name": "search_spot_manual", "args": {"query": "..."}, "ms": 220, "status": "ok", "by": "model"}],
 "model": "system2", "mode": "tools", "steps": 2, "latency_ms": 5100, "request_id": "r-1"}
```
- Tools: the MCP server's `tools/list`, filtered by `ASK_TOOL_ALLOWLIST` (default `search_*,get_*`) and never a tool
  whose `readOnlyHint` is false. A call to any other tool is refused (it still counts toward the cap).
- Bounded: at most `min(max_steps, ASK_MAX_TOOL_CALLS)` tool calls (default and max 4); after the cap the model is
  called once more without tools and must answer. Whole request within `ASK_DEADLINE_S` (30 s).
- `mode`: `tools` (the model used tools), `retrieval_fallback` (the model made no tool call on its first turn, or
  tool calling failed, e.g. llama-server started without `--jinja`: the orchestrator ran one retrieval step itself,
  `search_spot_manual` + `search_policy` + `get_flag_context(flag_id)` or `search_similar_incidents(text)`, and
  asked the model to answer from those results), `no_model` (the model was unreachable or out of time: the answer
  lists the most relevant retrieved sources, no generated text), `no_context` (no MCP tools and nothing retrieved:
  no model call, the answer says so).
- `citations`: ids from tool results (`results[].id`, `citation_ids`) that the answer actually cites, matched as a
  whole `[id]` (comma- or semicolon-separated inside the brackets) or a whole bare token, never as a substring
  (`manual:1` does not match `[manual:12]`). If the answer cites nothing, `citations` is `[]` and `cited` is `false`.
  `retrieved` lists every id the tools returned (at most 12 each) whether cited or not.
- `max_steps` 1-4 (default 4); `question` 2-2000 characters; optional `request_id`. Response also carries
  `max_tool_calls` (the effective cap) and `error` (why a degraded mode was taken, else null).
- `tool_calls[].status` ∈ `ok | error | timeout | skipped | refused | skipped_cap`; `by` ∈ `model | fallback`.

## GET /v1/graph
`{"assess": "<mermaid>", "ask": "<mermaid>"}` from `graph.get_graph().draw_mermaid()`. Open (no key).
`?format=text&graph=assess` returns the bare mermaid text.

## GET /health
Always 200 when the process is up: `{"status": "ok", "auth": true, "contract_version", "config": {mcp, gateway,
vision, system2: "set" | "unset"}, "demo_images": false}`. `?deep=true` also pings each dependency (2 s each) and
reports `up | down | degraded | unset`, without changing the status code.

## Environment
| Env var | Meaning | Default |
|---|---|---|
| `ORCHESTRATOR_API_KEY` | required X-API-Key secret (>= 16 chars) | none (refuses to start) |
| `ORCHESTRATOR_ALLOW_NO_AUTH` | `1` = start without a key (tests only) | `0` |
| `ORCHESTRATOR_HOST` / `ORCHESTRATOR_PORT` | bind address / port | `127.0.0.1` (image: `0.0.0.0`) / `8085` |
| `MCP_URL` / `MCP_AUTH_TOKEN` | MCP streamable HTTP endpoint / bearer token | `http://localhost:8090/mcp` / unset |
| `GATEWAY_URL` / `GATEWAY_KEY` | LiteLLM gateway base URL (with or without `/v1`) / bearer key (falls back to `LITELLM_MASTER_KEY`) | `http://localhost:4000` / unset |
| `SYSTEM1_ALIAS` / `ASK_MODEL` | gateway aliases for Laya and the ask model | `system1` / `system2` |
| `VISION_URL` / `VISION_API_KEY` | vision service (empty = no vision) / its `X-API-Key` (the vision service requires one since contract `vision.2`) | `http://localhost:8084` / unset |
| `SYSTEM2_URL` / `SYSTEM2_API_KEY` | System 2 (empty = always template) / its X-API-Key | `http://localhost:8083` / unset |
| `DEMO_IMAGES` / `DEMO_IMAGES_DIR` | `1` = pair kit sample images by action type / folder holding them | `0` / `web/public/kit/inspection` in a checkout, `/app/demo-images` in the image |
| `ORCH_DEADLINE_S` | global assess deadline | `40` |
| `ORCH_CONTEXT_BUDGET_S`, `ORCH_SYSTEM1_BUDGET_S`, `ORCH_VISION_BUDGET_S`, `ORCH_SYSTEM2_BUDGET_S` | per-node budgets | `15`, `6`, `12`, `20` |
| `ORCH_SYSTEM2_IMAGE_BUDGET_S` | System 2 node budget when an image is sent (keep >= System 2's `SYSTEM2_IMAGE_DEADLINE_S` + ~3 s) | `28` |
| `VISION_TRUST_MIN` / `OCR_TOP_N` | HIGH-trust confidence cut / OCR lines kept | `0.5` / `8` |
| `ORCH_MAX_IMAGE_B64` | max `image_b64` length (chars) | `12000000` |
| `ASK_DEADLINE_S` / `ASK_MAX_TOOL_CALLS` / `ASK_TOOL_ALLOWLIST` | ask deadline / tool-call cap (<= 4) / fnmatch patterns | `30` / `4` / `search_*,get_*` |
| `LOG_LEVEL` | | `INFO` |

Demo-image mapping (`DEMO_IMAGES=1`, no caller image): `THERMAL_INSPECTION` -> `thermal_pump_bearing_01.jpg` (kind
`thermal`), `GAUGE_READING` -> `gauge_pressure_01.jpg` (`gauge`), `ACOUSTIC_INSPECTION` -> `acoustic_valve_01.jpg`
(`acoustic`), `VISUAL_INSPECTION` -> `visual_pump_motor_01.jpg` (`visual`); `NAVIGATION` has none. No kit CSV row
links to an image (`research/tech-spot-vision-cv-2026-10-10.md`), so these rows are always `pairing: "demo"` and are
never compared with the flag's logged reading (see "Vision rows sent to System 2").
