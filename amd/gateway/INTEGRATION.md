# Gateway integration (for the integrator agent)

Apply these changes to the shared files. Nothing below has been applied yet; this agent edited only `amd/gateway/`.

## 1. `docker-compose.yml`

### Header table row

Add it after `system2`:

```
# gateway    4000  local, hybrid, neon, system2  LiteLLM proxy: one OpenAI-compatible endpoint, Bearer LITELLM_MASTER_KEY.
#                                           Aliases system2 / system2-vision -> llama-server (LLAMA_URL, VISION_LLAMA_URL;
#                                           an SSH tunnel to the AMD box by default), system1 -> Laya /v1/predict,
#                                           embed -> embed. No DB, UI or telemetry. GET /health/liveliness is public.
```

### Service block

Put it under `# ── models` or next to `system2`:

```yaml
  # LiteLLM gateway (amd/gateway/README.md). llama-server is never in compose: LLAMA_URL defaults to the SSH tunnel
  # (ssh -N -L 18080:127.0.0.1:8080 <amd-box>). Retries 0, no fallbacks, no cooldowns (config.yaml).
  gateway:
    <<: *service
    build: {context: amd/gateway}
    image: spot-gateway:compose
    profiles: [local, hybrid, neon, system2]
    depends_on:
      system1: {condition: service_healthy, required: false}
      embed: {condition: service_healthy, required: false}
    environment:
      <<: *embed-env                      # EMBED_URL (EMBED_MODEL/EMBED_DIM are ignored here)
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY:-}
      LLAMA_URL: ${LLAMA_URL:-http://host.docker.internal:18080}
      VISION_LLAMA_URL: ${VISION_LLAMA_URL:-}   # empty = same llama-server as LLAMA_URL (started with --mmproj)
      LLAMA_API_KEY: ${LLAMA_API_KEY:-}
      SYSTEM1_URL: ${SYSTEM1_URL:-http://system1:8082}
      SYSTEM2_TIMEOUT_S: ${GATEWAY_SYSTEM2_TIMEOUT_S:-15}
      VISION_TIMEOUT_S: ${GATEWAY_VISION_TIMEOUT_S:-30}
      SYSTEM1_TIMEOUT_S: ${GATEWAY_SYSTEM1_TIMEOUT_S:-10}
      EMBED_TIMEOUT_S: ${GATEWAY_EMBED_TIMEOUT_S:-10}
    ports: ["${BIND_ADDR:-127.0.0.1}:${GATEWAY_PORT:-4000}:4000"]
    # Non-root runtime (uid 10001) and HEALTHCHECK (/health/liveliness) are inherited from the image.
```

Notes:
- Leave out `DATABASE_URL`. The gateway refuses to start when it is set, and none of the compose anchors inject it.
- An empty `LITELLM_MASTER_KEY` makes the container exit with a clear message. That matches how `SYSTEM2_API_KEY`
  is handled.

### `system2` service

Point it at the gateway. The System 2 agent's env names are `SYSTEM2_LLAMA_API_KEY` and `SYSTEM2_VISION_MODEL`
(`amd/system2/analyst/live.py`). Keep the stub as the default:

```yaml
      SYSTEM2_LLAMA_URL: ${SYSTEM2_LLAMA_URL:-}                     # live via gateway: http://gateway:4000
      SYSTEM2_LLAMA_API_KEY: ${SYSTEM2_LLAMA_API_KEY:-${LITELLM_MASTER_KEY:-}}
      SYSTEM2_MODEL: ${SYSTEM2_MODEL:-}                             # qwen3.5-9b-q4km (hidden gateway alias) or system2
      SYSTEM2_VISION_MODEL: ${SYSTEM2_VISION_MODEL:-system2-vision}
    depends_on:
      gateway: {condition: service_healthy, required: false}
```

Sending the Bearer key straight to a llama-server that has no `--api-key` does no harm (it ignores the header), so
the same block works without the gateway.

### `orchestrator` service

Its owner's names are `GATEWAY_URL` and `GATEWAY_KEY` (which falls back to `LITELLM_MASTER_KEY`):

```yaml
      GATEWAY_URL: ${GATEWAY_URL:-http://gateway:4000}
      GATEWAY_KEY: ${LITELLM_MASTER_KEY:-}
    depends_on:
      gateway: {condition: service_healthy, required: false}
```

## 2. `.env.example`

```bash
# ── model gateway (amd/gateway, :4000) ──
LITELLM_MASTER_KEY=sk-spot-gateway-dev-change-me   # Bearer for every gateway caller; sk- prefix, >= 16 chars
# LLAMA_URL=http://host.docker.internal:18080       # llama-server (System 2 text) via ssh -L 18080:127.0.0.1:8080
# VISION_LLAMA_URL=                                  # separate llama-server with --mmproj; empty = LLAMA_URL
# LLAMA_API_KEY=                                     # llama-server --api-key, if set
# GATEWAY_PORT=4000
# Live System 2 through the gateway:
# SYSTEM2_LLAMA_URL=http://gateway:4000
# SYSTEM2_MODEL=qwen3.5-9b-q4km
```

## 3. Ports table in `docs/backend-services-contract.md`

```
| Model gateway (LiteLLM: system1 / system2 / system2-vision / embed) | `amd/gateway/` | 4000 | gateway agent |
```

## 4. `docs/RUNNING.md`

Add a new section:

````markdown
## Model gateway on 4000 (LiteLLM)

One OpenAI-compatible endpoint for every model: `model` = `system2` | `system2-vision` | `system1` | `embed`,
`Authorization: Bearer $LITELLM_MASTER_KEY`. System 2 and the orchestrator call models through it. Details,
aliases, the System 1 message format and the supply-chain pin (litellm 1.104.1, hashed lock) are in
`amd/gateway/README.md`.

```bash
# compose: set LITELLM_MASTER_KEY in .env; llama-server reached through the tunnel on 18080
ssh -N -L 18080:127.0.0.1:8080 <amd-box>
docker compose up -d gateway
curl -s localhost:4000/health/liveliness
curl -s localhost:4000/v1/chat/completions -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H 'content-type: application/json' -d '{"model":"system2","messages":[{"role":"user","content":"hi"}]}'
amd/gateway/scripts/smoke.sh                       # one call per alias against the running gateway

# native on the AMD box (no Docker): Python 3.12 venv, hashed install
cd amd/gateway && python3.12 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements.txt
LITELLM_MASTER_KEY=sk-... LLAMA_URL=http://127.0.0.1:8080 SYSTEM1_URL=http://127.0.0.1:8082 \
  EMBED_URL=http://127.0.0.1:8081 .venv/bin/python serve.py
# then System 2 live through it:
SYSTEM2_LLAMA_URL=http://127.0.0.1:4000 SYSTEM2_LLAMA_API_KEY=$LITELLM_MASTER_KEY SYSTEM2_MODEL=qwen3.5-9b-q4km \
  SYSTEM2_VISION_MODEL=system2-vision python scripts/serve.py
```

For the vision alias, start llama-server with `--mmproj mmproj-F16.gguf` (or run a second one and set
`VISION_LLAMA_URL`). The gateway never retries and never falls back to another model: a System 2 failure reaches
System 2, which then serves its checked template.
````

Also add one line to the `hybrid` mode section: "`LLAMA_URL` in `.env` → the llama-server tunnel; the gateway runs in
Docker".

## 5. `Makefile`

```make
PY_GATEWAY ?= amd/gateway/.venv/bin/python

test-gateway: ## gateway unit + e2e tests (real LiteLLM proxy against offline stubs, ~13 s)
	cd amd/gateway && .venv/bin/python -m pytest -q -p no:cacheprovider
```

- Add `test-gateway` to the `test:` prerequisites and to `.PHONY`.
- In `venvs:`, add:

```make
	test -x $(PY_GATEWAY) || (python3 -m venv amd/gateway/.venv && amd/gateway/.venv/bin/pip install --require-hashes \
	  -r amd/gateway/requirements.txt && amd/gateway/.venv/bin/pip install -r amd/gateway/requirements-dev.txt)
```

`python3` must be 3.12. The lock is compiled for 3.12, so on another version use the unhashed fallback in the
README.

## 6. `.github/` CI (if a workflow runs the per-service suites)

```yaml
- run: python3.12 -m venv amd/gateway/.venv && amd/gateway/.venv/bin/pip install --require-hashes -r amd/gateway/requirements.txt -r amd/gateway/requirements-dev.txt
  # requirements-dev.txt has no hashes, so install it in a second pip call if pip complains
- run: cd amd/gateway && .venv/bin/python -m pytest -q -p no:cacheprovider
```

## 7. `backend/`

No backend change is required. The backend keeps calling System 2 (`SYSTEM2_URL`) and System 1 (`SYSTEM1_URL`)
directly. Routing the backend's System 1 calls through the gateway is optional and was not proposed.

## 8. System 2

The System 2 agent already has this in progress. The gateway e2e test (`test_system2_llama_generator_and_parse_envelope_through_gateway`)
runs the real `LlamaGenerator` + `run_pipeline` through the proxy and confirms:
- `json_schema` (the packet-scoped schema, byte for byte) and `chat_template_kwargs` arrive unchanged
- `parse_envelope` still gets `content`, `finish_reason`, `usage` and llama-server's `timings.predicted_per_second`
- `model` becomes the requested name, `system2` or `qwen3.5-9b-q4km`. Use the second to keep existing cache keys.
- no key → 401 → `GenerationError('http')` → checked template

The only thing System 2 needed was a Bearer key in `LlamaGenerator`, read from env. It now has that as
`SYSTEM2_LLAMA_API_KEY`, plus `SYSTEM2_VISION_MODEL` in `live.py`. `scripts/precompute.py`, `evaluate.py` and
`report.py` still build `LlamaGenerator(url, model=…)` without a key. They work against llama-server directly; to run
them through the gateway, they would need the same `api_key=os.environ.get('SYSTEM2_LLAMA_API_KEY')`.
