# Audit follow-ups for the integrator (2026-10-10)

The fixer changed only its own files (`amd/orchestrator/**`, `amd/vision/**`, `amd/system2/{analyst,tests,fixtures}`,
`amd/system2/{README,PROMPT_FORMAT}.md`, `amd/gateway/README.md`, `docs/vision-contract.md`,
`docs/orchestrator-contract.md`, `research/tech-spot-vision-cv-2026-10-10.md`). Everything below goes into files the
integrator owns. Items are ordered by urgency.

## P0: compose breaks without this (vision now fails closed)

The vision service refuses to start without `VISION_API_KEY` (contract `2026-10-10.vision.2`). Compose currently
passes `VISION_API_KEY: ${VISION_API_KEY:-}`, so the `vision` container would exit with code 2 on every `make up`.

`docker-compose.yml`:
- In the `x-keys` block, next to `system2:` / `orchestrator:`, add
  `vision: &vision-key ${VISION_API_KEY:-spot-vision-dev-key-change-me}   # X-API-Key orchestrator -> vision`.
- `vision` service: `VISION_API_KEY: *vision-key`. Change `VISION_MAX_PIXELS: ${VISION_MAX_PIXELS:-25000000}` to
  `${VISION_MAX_PIXELS:-12000000}` (compose's explicit 25 MP default would override the new 12 MP code default), and
  add `VISION_MAX_CONCURRENCY: ${VISION_MAX_CONCURRENCY:-2}` and `VISION_QUEUE_TIMEOUT_S: ${VISION_QUEUE_TIMEOUT_S:-3}`.
  Do not set `VISION_ALLOW_NO_AUTH` in compose (tests only).
- `orchestrator` service: `VISION_API_KEY: *vision-key` (same key; the orchestrator already sends it as `X-API-Key`).
- Header comment for `vision`: "Optional VISION_API_KEY." -> "Required VISION_API_KEY (X-API-Key; /health open)."
- The image's HEALTHCHECK now reads `VISION_PORT` (default 8084); nothing to change in compose.

## P1: new env vars (image latency, A-6)

`docker-compose.yml`:
- `system2` service: `SYSTEM2_IMAGE_DEADLINE_S: ${SYSTEM2_IMAGE_DEADLINE_S:-25}` (requests with `image_b64` only;
  text requests keep 15 s; must be in (0, 120] or System 2 refuses to start in live mode).
- `orchestrator` service: `ORCH_SYSTEM2_IMAGE_BUDGET_S: ${ORCH_SYSTEM2_IMAGE_BUDGET_S:-28}` (keep >= the System 2
  value + ~3 s).
- Gateway: `GATEWAY_VISION_TIMEOUT_S` (30) is already above 25 s; `GATEWAY_SYSTEM2_TIMEOUT_S` (15) is fine for the
  text-only resend (System 2 keeps 8 s for it).

`.env.example` (Vision block and Orchestrator block):
```
# VISION_API_KEY=                                    # REQUIRED by the vision service (>= 16 chars); compose default is a dev key
# VISION_MAX_IMAGE_BYTES=12000000  VISION_MAX_PIXELS=12000000  VISION_WORK_MAX_SIDE=1280  VISION_CACHE_SIZE=64
# VISION_MAX_CONCURRENCY=2  VISION_QUEUE_TIMEOUT_S=3  # at most 2 analyses at once, then 503 after 3 s
# SYSTEM2_IMAGE_DEADLINE_S=25                        # System 2 deadline for requests with an image (text: 15 s)
# ORCH_SYSTEM2_BUDGET_S=20  ORCH_SYSTEM2_IMAGE_BUDGET_S=28  ASK_DEADLINE_S=30  ASK_MAX_TOOL_CALLS=4
```

## P1: `docs/RUNNING.md`

- Service table, `vision` row: "Optional `VISION_API_KEY`" -> "Required `VISION_API_KEY` (header `X-API-Key`; the
  service refuses to start without one; `/health` open). JPEG/PNG/WebP only, 12 MP max, 2 concurrent analyses (503
  when busy)."
- "Timeouts and keys" table:
  - orchestrator nodes row: add "System 2 28 s when an image is sent (`ORCH_SYSTEM2_IMAGE_BUDGET_S`); vision is
    capped so that budget stays free (at least 3 s)".
  - System 2 generation row: "15 s over at most two attempts; **25 s for requests with an image**
    (`SYSTEM2_IMAGE_DEADLINE_S`): the image call keeps 8 s back and on a timeout the same attempt is re-sent
    text-only" (it is no longer "fixed").
  - Sentence under the table: "System 2 closes its own socket at 15 s (25 s with an image), so the gateway's 30 s
    vision timeout ..."
  - Keys table, `VISION_API_KEY` row: "orchestrator -> vision (required, >= 16 chars; refuses to start without one)".
  - Image chain, for reference: backend 45 s -> orchestrator call <= 42 s -> `ORCH_DEADLINE_S` 40 (reserve 3 s) ->
    vision <= min(12 s, time left - 28 s), at least 3 s -> System 2 node <= 28 s -> System 2 25 s -> gateway
    `system2-vision` 30 s (never binding). Also in `docs/orchestrator-contract.md` "Timeout chain".
- "Vision / OCR on 8084": `export VISION_API_KEY=...` before `scripts/serve.py`, and
  `curl -H "X-API-Key: $VISION_API_KEY"` for `/v1/*` (only `/health` is open).

## P1: `docs/backend-services-contract.md`, "System 2 multimodal inputs" section (System 2 contract follow-up)

Add after the `context.vision` bullet (contract stays `2026-10-10.backend.2`: additive, response unchanged; the
prompt version is now `analyst-prompt-2026-10-10.3`):
- "Optional `flags`: a list of uppercase reader caveats (`^[A-Z][A-Z_]{0,31}$`, no digits), de-duplicated and
  capped at 8; anything else is 422. `AMBIGUOUS_NEEDLE` or `DEFAULT_SWEEP` forces `trust: "LOW"`. `CLIPPED` keeps
  the trust but adds `bound: "lower"` (the value is the top of the scale; the true value is at least that).
  Optional `bound`: `lower | upper`."
- "`pairing: "demo"` rows come from an illustrative kit image chosen by action type, not from this asset: System 2
  drops their `agrees`, `delta`, `logged_id` and `logged_value`, and they never trigger the action restriction."
- Actions bullet: "when any HIGH-trust **`linked`** V# row has `agrees: false` ..." (demo rows never do).
- Prompt bullet: `VISION_RULES` now also says demo rows are illustrative and never compared, `bound=lower` values
  are lower bounds ("at least"), and `RELATIVE_ONLY` values are relative levels. Requests with no vision fields still
  get the byte-identical pre-multimodal prompt (golden test unchanged).
- Serving bullet: "Requests with `image_b64` use `SYSTEM2_IMAGE_DEADLINE_S` (default 25 s) instead of 15 s; the
  image call keeps 8 s back and, if it times out, the same attempt is re-sent text-only (`X-System2-Image:
  text_only`, not cached). A gateway 400 'No connected db.' (LiteLLM's answer to a wrong key) is an auth error, never
  an image rejection: no text-only resend."
- Vision row in the ports/services text (line ~13 area, if it mentions auth): the vision service now requires
  `VISION_API_KEY`.

## P2: `docs/TEAMMATE-qwen-vision-finetune.md` (must say)

- **Train disagreement (and agreement) behaviour only on `pairing: "linked"` rows.** `demo` rows never carry
  `agrees`, `delta` or `logged_*`; their target answer calls the image illustrative and does not judge the asset
  (worked example: `amd/system2/fixtures/multimodal/gauge_demo.json`, PROMPT_FORMAT.md §6b).
- The golden disagreement example `gauge_disagree.json` now uses `pairing: "linked"`.
- Prompt version is `analyst-prompt-2026-10-10.3`: the `VISION_RULES` text changed (three new sentences). Rebuild
  any training rows rendered with the `.2` system text (`scripts/prompt_example.py` / `request_body` do it).
- Include some rows with `flags` (e.g. `["CLIPPED"]` + `bound: "lower"`, target says "at least <value>") and
  `RELATIVE_ONLY` spectrogram rows; `AMBIGUOUS_NEEDLE` rows arrive as `trust: "LOW"` with no value.
- Line ~267 quotes the old rule text; quote PROMPT_FORMAT.md §2 instead (or the new sentences).

## P2: backend (`backend/**`, read only for the fixer)

- A-8: the orchestrator now returns `source: "system2_template"` when System 2 answered with its own checked template
  (`path` `fallback`/`insufficient_context` or `model` `template`). `services/flags.py::_via_orchestrator` already maps
  any source outside `("system2", "template", "system1")` to `"template"`, so it is stored as `TEMPLATE` and not
  indexed as a RAG doc: correct, no change required. Optional: keep `system2_template` in the API response (still
  stored as TEMPLATE) so the UI can say "System 2 fell back"; then widen `schemas/flags.py` `Explanation.source`.
- Same rule on the backend's own (non-orchestrator) path: `normalize_assessment` labels every System 2 reply
  `source: "system2"`, so a System 2 `path: "fallback"` (its template) is stored `DONE` and indexed as an
  `explanation` RAG doc. Suggest: `path in ("fallback", "insufficient_context") or model == "template"` -> TEMPLATE.
- A-9: `/api/v1/ask` returns the orchestrator body unchanged. `citations` can now be `[]` with `cited: false`; the new
  `retrieved` list holds every id the tools returned. If the UI showed `citations` as "sources", show `retrieved`
  when `cited` is false (labelled "consulted, not cited").
- A-10: the orchestrator now 422s an unknown `image_kind`; the backend's `ImageKind` Literal is already a subset of
  the allowed values (`auto` is also accepted by the orchestrator).
- Orchestrator `vision` block now has `demo_alert` (demo image's own alert); `alert` is `null` for demo images.

## P3: other

- `amd/system2/INTEGRATION-multimodal.md` (not in either ownership list), §5: "System 2's own generation deadline
  stays 15 s per request" -> "15 s, or `SYSTEM2_IMAGE_DEADLINE_S` (25 s) for requests with an image"; and the row
  field list should add `flags`, `bound` and the demo rule.
- `research/decisions.md`, one-liners under "Made" (suggested):
  - "**Demo images never judge the asset (2026-10-10).** With `DEMO_IMAGES=1` the kit sample is illustrative: no
    logged value is sent to vision, demo rows carry no comparison, System 2 ignores agrees/delta on them, and the
    fine-tune learns disagreement only from `linked` rows. A kit image of another pump must not escalate this one."
  - "**Vision service fails closed (2026-10-10).** `VISION_API_KEY` required, JPEG/PNG/WebP only, 12 MP, body cap,
    2 concurrent analyses: a 107 KB PNG of 25 MP had pushed one request to ~2.5 GB RSS."
- Residual memory note (not a regression): even a 3 MP image peaks at ~1.5 GB RSS in-process, because RapidOCR runs
  at up to 2000 px long side (onnxruntime arena); the 12 MP decode adds ~0.2 GB. With 2 concurrent analyses (OCR is
  already serialised by a lock) plan ~2 GB for the vision container. Lowering `OCR_MAX_SIDE` or disabling the ORT
  CPU arena would cut it further; not done here (it changes OCR accuracy on the Orbit screenshots).
