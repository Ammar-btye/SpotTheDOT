# Integrating System 2 multimodal (contract `2026-10-10.backend.2`)

For the integrator agent. The System 2 code, tests and the System 2 section of
`docs/backend-services-contract.md` are done. The files below belong to other owners, so the edits are listed
here rather than made. All of them are additive: with none applied, System 2 still behaves exactly as `backend.1`.

## 1. `docker-compose.yml`, service `system2` (environment block)

Add three variables next to `SYSTEM2_MODEL`, and point live mode at the gateway when the `gateway` service exists:

```yaml
      # Live mode via the LiteLLM gateway (amd/gateway, :4000): SYSTEM2_LLAMA_URL=http://gateway:4000,
      # SYSTEM2_MODEL=system2, SYSTEM2_VISION_MODEL=system2-vision, SYSTEM2_LLAMA_API_KEY=<LITELLM_MASTER_KEY>.
      SYSTEM2_LLAMA_URL: ${SYSTEM2_LLAMA_URL:-}
      SYSTEM2_MODEL: ${SYSTEM2_MODEL:-}
      SYSTEM2_VISION_MODEL: ${SYSTEM2_VISION_MODEL:-}        # model for requests with an image; empty = SYSTEM2_MODEL
      SYSTEM2_LLAMA_API_KEY: ${LITELLM_MASTER_KEY:-}          # sent as Authorization: Bearer; empty = no header
      SYSTEM2_CACHE_DIR: ${SYSTEM2_CACHE_DIR:-}
```

- If `system2` is wired to the gateway, add `depends_on: {gateway: {condition: service_healthy, required: false}}`
  so stub mode still starts without it.
- No new port, volume, build arg or healthcheck. The image is unchanged (`analyst/`, `scripts/` and `data/` are
  already copied in).
- Update the compose header comment for `system2` to say it accepts optional `vision`/`ocr`/`image_b64` inputs.

## 2. `.env.example`

```dotenv
# System 2 live mode through the gateway (optional; empty SYSTEM2_LLAMA_URL = stub)
# SYSTEM2_LLAMA_URL=http://gateway:4000
# SYSTEM2_MODEL=system2
# SYSTEM2_VISION_MODEL=system2-vision     # used only when a request carries image_b64; empty = SYSTEM2_MODEL
# SYSTEM2_LLAMA_API_KEY=                  # compose passes LITELLM_MASTER_KEY; set by hand for a native run
```

## 3. `docs/RUNNING.md`

In the System 2 section, add:
- Images need a vision-capable server: llama-server started with `--mmproj <Qwen3.5-9B mmproj GGUF>` (the gateway's
  `system2-vision` upstream). Without it System 2 still answers: it re-sends the attempt text-only, and the
  response header `X-System2-Image: text_only` shows that (`used` = the accepted answer saw the image,
  `not_used` = stub, insufficient context or template fallback). The header appears only when the request had an
  image. A warning `image rejected by the model server` is logged (logger `system2.live`).
- Smoke test with the worked example:
  `python3 -c "import json; print(json.dumps(json.load(open('amd/system2/fixtures/multimodal/gauge_disagree.json'))['request']))" > /tmp/mm.json`
  then `curl -si -X POST http://127.0.0.1:8083/v1/assess -H "X-API-Key: $SYSTEM2_API_KEY" -H "Content-Type: application/json" --data @/tmp/mm.json`.
  Expect 200, `V1` in `evidence[].ids` and the `X-System2-Image` header.
- `python amd/system2/scripts/prompt_example.py` prints the exact chat request (PROMPT_FORMAT.md).

## 4. `docs/backend-services-contract.md`, ports table

No port change. Optionally change the System 2 row's note to "`/v1/assess`, contract `2026-10-10.backend.2`".

## 5. Backend / orchestrator (callers)

- The backend's current request is still valid; nothing breaks if it never sends the new fields.
- The orchestrator (or backend) adds, from the vision service's response (`docs/vision-contract.md`):
  `context.vision = [{id: "V1", tool, kind, quantity, value, unit, confidence, trust, logged_id, logged_value,
  delta, agrees, pairing, flags, bound}]` (at most 16 rows; IDs `V1`..`V999`; `flags` = uppercase reader caveats,
  at most 8, `AMBIGUOUS_NEEDLE`/`DEFAULT_SWEEP` force LOW trust, `CLIPPED` adds `bound: "lower"`; `pairing: "demo"`
  rows lose `agrees`, `delta`, `logged_id`, `logged_value` and never restrict actions), `context.ocr = [{text, conf}]`, and top-level
  `image_b64` (the **annotated** image with V#-labelled marks, JPEG/PNG, at most 2 MiB decoded; a
  `data:image/...;base64,` prefix is allowed). Bad image or malformed vision/ocr values return **422**; callers
  should then retry once without `image_b64` (and log it) rather than fail the explanation.
- `logged_id` should be the evidence ID of the logged reading as it appears in the packet (for example
  `reading:R0053`), so the model can cite both rows.
- Response body unchanged. New optional response header `X-System2-Image`. Request bodies with images are
  up to ~2.8 MB; keep `SYSTEM2_TIMEOUT_S` (60) as is. System 2's own generation deadline is 15 s per request
  across both attempts, or `SYSTEM2_IMAGE_DEADLINE_S` (25 s) for requests with an image (the image call keeps 8 s
  back for a text-only resend); watch for more `fallback` paths on image requests.
- Laya rows in `context.system1` may use the MCP shape (`q`, `p`) or Laya-native keys (`question`,
  `probability`/`confidence`, `probs`); both render as question, answer, meaning and probability.

## 6. `research/decisions.md` (one line, under "Made")

- **System 2 multimodal (2026-10-10):** contract `2026-10-10.backend.2` adds optional `context.vision` (citable V#
  rows, numbers computed by code), `context.ocr` (untrusted, never citable) and `image_b64` (context only, image
  first in the prompt); a tool/log disagreement removes MONITOR/NO_ACTION, and a server without `--mmproj` falls
  back to text-only. VLMs misread gauges and thermal values, so code makes the numbers and the model explains
  (research tech-spot-vision-cv §3, §7).

## 7. Web types

`amd/system2/schema/assess_request.schema.json` was regenerated (adds optional `image_b64`); the response schema
changed only in its version comment. Regenerate any web types built from these files.
