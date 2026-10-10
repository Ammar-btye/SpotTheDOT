# Model gateway (LiteLLM proxy, port 4000)

One OpenAI-compatible endpoint in front of every model the project serves. Callers send `model: <alias>` and
`Authorization: Bearer $LITELLM_MASTER_KEY`, and the gateway routes each alias to its service.

The request asked for "LightLLM to route between the System 1 and System 2 models". We read that as
**LiteLLM** (BerriAI's routing proxy). LightLLM is a different project: an inference server, not a router.

| Alias | Upstream | Route | Timeout |
|---|---|---|---|
| `system2` | llama-server, Qwen3.5-9B (text) | `POST {LLAMA_URL}/v1/chat/completions` | 15 s |
| `system2-vision` | llama-server started with `--mmproj` (by default the same one) | `POST {VISION_LLAMA_URL}/v1/chat/completions` | 30 s |
| `system1` | Laya triage, through the custom provider `laya_provider.py` | `POST {SYSTEM1_URL}/v1/predict` | 10 s |
| `embed` | embedding service (`amd/embed`) | `POST {EMBED_URL}/v1/embeddings` | 10 s |

`qwen3.5-9b-q4km` is a hidden alias of `system2`. System 2 can therefore keep `SYSTEM2_MODEL=qwen3.5-9b-q4km`. Its
explanation-cache key includes the model name, so the explanations already cached for that name stay valid.

Routing policy (`config.yaml`):
- **Retries: 0 everywhere.** System 2's checked pipeline already retries once inside its 15 s budget, and a retry
  here would double that.
- **No fallbacks.** If `system2` fails, the failure reaches System 2, which then uses its checked template. A
  different model never answers in its place.
- **Cooldowns are off.** Each alias has a single deployment, so a cooldown would turn one slow call into a stretch
  of "no deployments available".
- **`drop_params: false`.** `response_format` with `json_schema` and `chat_template_kwargs` must reach llama-server
  unchanged.

## System 1 through the gateway

The last user message is JSON in one of two shapes: a single event, or the body `/v1/predict` takes
(`docs/backend-services-contract.md`). The reply's `content` is Laya's response JSON. `usage` is all zeros because
Laya is a classifier.

```json
{"model": "system1", "messages": [{"role": "user", "content":
  "{\"kind\": \"action\", \"event\": {...canonical event...}, \"questions\": [\"risk\"], \"id\": \"a-1\"}"}]}
{"model": "system1", "messages": [{"role": "user", "content": "{\"request_id\": \"r\", \"items\": [...]}"}]}
```

| Case | HTTP status |
|---|---|
| Laya returns a 4xx, or the message is not that JSON | 400, carrying Laya's own `error` text |
| Laya returns a 5xx or a body that isn't JSON | 502 |
| Laya can't be reached | 503 |
| Laya times out | 504 |

`stream: true` works, but the whole answer arrives as one chunk.

## Env

| Var | Default (native) | Meaning |
|---|---|---|
| `LITELLM_MASTER_KEY` | required | Bearer key for every caller. Must start with `sk-` and be at least 16 characters. Never logged. |
| `LLAMA_URL` | `http://127.0.0.1:8080` | llama-server base URL, without `/v1` |
| `VISION_LLAMA_URL` | = `LLAMA_URL` | llama-server that has `--mmproj` loaded |
| `LLAMA_API_KEY` | empty | the `--api-key` of llama-server, if it has one |
| `SYSTEM1_URL` | `http://127.0.0.1:8082` | Laya service |
| `EMBED_URL` / `EMBED_API_KEY` | `http://127.0.0.1:8081` / empty | embedding service |
| `SYSTEM2_TIMEOUT_S` `VISION_TIMEOUT_S` `SYSTEM1_TIMEOUT_S` `EMBED_TIMEOUT_S` | 15 / 30 / 10 / 10 | per-call timeout for each alias |
| `GATEWAY_HOST` `GATEWAY_PORT` `GATEWAY_WORKERS` `GATEWAY_CONFIG` | 0.0.0.0 / 4000 / 1 / ./config.yaml | |

The gateway reads `LLAMA_URL`, not `SYSTEM2_LLAMA_URL`, on purpose. System 2 uses `SYSTEM2_LLAMA_URL` to point *at
the gateway*, so one name for both would loop.

`serve.py` fills in these defaults. It derives the `GATEWAY_*` variables that `config.yaml` reads through
`os.environ/…`, then starts the stock LiteLLM CLI in the same process. It also switches off what we don't use:
- no database: it refuses to start if `DATABASE_URL` is set
- no admin UI
- no telemetry: `LITELLM_TELEMETRY=False` is forced
- no download of the cost map at startup
- no `.env` loading

The image starts and turns healthy with `--network none`.

## Run

```bash
# native (AMD Jupyter VM: no Docker, no root). Python 3.12.
cd amd/gateway
python3.12 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements.txt
LITELLM_MASTER_KEY=sk-... LLAMA_URL=http://127.0.0.1:8080 SYSTEM1_URL=http://127.0.0.1:8082 \
  EMBED_URL=http://127.0.0.1:8081 .venv/bin/python serve.py
# Docker
docker build -t spot-gateway amd/gateway
docker run --rm -p 127.0.0.1:4000:4000 -e LITELLM_MASTER_KEY=sk-... \
  -e LLAMA_URL=http://host.docker.internal:18080 spot-gateway
```

The lock covers Python 3.12 on Linux and macOS. If the box only has another Python 3, install the same pins without
hashes: `pip install "litellm[proxy]==1.104.1" prisma==0.15.0`.

Start the vision llama-server with `--mmproj mmproj-F16.gguf` (see `research/tech-spot-vision-cv-2026-10-10.md`). If
the text server already loads the mmproj, leave `VISION_LLAMA_URL` unset and both aliases share it.

## Pointing clients at it

- **System 2:** `SYSTEM2_LLAMA_URL=http://gateway:4000`, `SYSTEM2_LLAMA_API_KEY=$LITELLM_MASTER_KEY`,
  `SYSTEM2_MODEL=qwen3.5-9b-q4km` (or `system2`), `SYSTEM2_VISION_MODEL=system2-vision`. Its `LlamaGenerator` adds
  `/v1/chat/completions` itself. The e2e test checks that `parse_envelope` keeps everything it reads:
  - `choices[0].message.content` and `finish_reason`
  - `usage.*_tokens`
  - llama-server's `timings` block (`predicted_per_second`), which LiteLLM passes through
  - `model`, which becomes the requested alias rather than llama-server's own model name
- **Orchestrator, or any OpenAI SDK:** `base_url=http://gateway:4000/v1` with `api_key=$LITELLM_MASTER_KEY`. Tool
  calling (`tools`, `tool_choice`, `tool_calls`, `role: tool` turns) passes through to llama-server, which needs
  `--jinja` for tool calls.
- `GET /v1/models` lists the four aliases. `GET /health/liveliness` needs no auth and is the container
  healthcheck. `/health` asks every upstream and requires the key.

## Supply chain: why `litellm==1.104.1`

On 2026-03-24, litellm **1.82.7 and 1.82.8** on PyPI shipped credential-stealing malware
([GHSA-5mg7-485q-xm76](https://github.com/advisories/GHSA-5mg7-485q-xm76)). 1.82.7 ran it on import, and 1.82.8 added
a `litellm_init.pth` that runs at interpreter start. The attackers used PyPI credentials stolen through litellm's
CI. We pin **1.104.1** (released 2026-10-07 on the `stable/1.104.x` line) because:

1. It is far outside the malicious range. It also includes the fixes from every published advisory since then, up to
   the 2026-09-30 SSRF fix (GHSA-3cv6-jpf6-8222, fixed in ≥1.96.2). On 2026-10-10, OSV listed no vulnerabilities for
   it.
2. Its changes since 1.104.0 are only a dependency refresh and a pgbouncer bump (see its GitHub release notes). The
   matching GitHub release has a cosign-signed image.
3. We chose it over 1.104.2 (2026-10-08), which backports a new feature, and over a `.dev`/`rc` release.

`requirements.txt` is a hashed lock (`uv pip compile … --generate-hashes`) of `litellm[proxy]==1.104.1` and
`prisma==0.15.0`, and both the image and the native install use `--require-hashes`.

`prisma` is needed because the proxy's auth-error path imports it even without a database. Without it, a request
with no key returns 500 instead of 401.

The Docker build fails if any `litellm_init.pth` exists in the image. To bump the version: check the advisories,
edit `requirements.in`, regenerate the lock, then run the tests and `scripts/smoke.sh --stubs`.

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q          # 47 tests, offline, about 13 s
scripts/smoke.sh --stubs               # real proxy against tests/stubs.py; prints the gateway's overhead
LITELLM_MASTER_KEY=sk-... scripts/smoke.sh --only system2,system1 --image gauge.png   # running gateway, real models
```

The e2e test starts the real proxy as a subprocess against stub upstreams (`tests/stubs.py`). Every request runs over
local HTTP, with no model, GPU or network.

## Auth caveats

Probed 2026-10-10 against the real proxy (stub upstreams, `LITELLM_MASTER_KEY=sk-...`):

| Request | Status / body |
|---|---|
| no `Authorization` header | **401** `Authentication Error, No api key passed in.` |
| wrong key, with or without the `sk-` prefix | **400** `{"error": {"message": "No connected db.", "type": "no_db_connection"}}` |
| master key | 200 |
| `GET /`, `/openapi.json`, `/routes`, `/health/readiness`, `/health/liveliness` | 200 with no key (`/ui` redirects; `/docs` 404) |
| `GET /health`, `/v1/models`, `/metrics`, `/model/info`, `/get/config/callbacks`, `/debug/*` | 401 without a key |

- A wrong key is therefore a **400, not a 401/403**. LiteLLM looks the unknown key up as a virtual key, and with no
  database it answers "No connected db." The request is still rejected and never forwarded. Clients must not read
  a 400 as a bad request or a model limitation: System 2's text-only-retry classifier
  (`amd/system2/analyst/generation.py`, `AUTH_ERROR_WORDS`) treats "No connected db" / `no_db_connection` as an
  auth failure, so a wrong `SYSTEM2_LLAMA_API_KEY` falls back to the checked template instead of being hidden behind
  a text-only resend. If every System 2 answer is `path: "fallback"` and the gateway log shows `no_db_connection`,
  check the key.
- The open routes (`/`, `/openapi.json`, `/routes`) list the proxy's endpoints but no aliases, keys or upstream URLs.
  Still, publish the port on loopback or the internal compose network only (`BIND_ADDR`), never on a public interface.
- Neither the master key nor a wrong key appears in the gateway log (checked in the same probe).
- The key must start with `sk-` (LiteLLM's master-key rule); `serve.py` refuses to start otherwise.

## Known behaviour

- A non-master key gets **400 "No connected db."** rather than 401 (see "Auth caveats"). A missing key gets 401.
- A timeout on `system2`, `system2-vision` or `embed` returns **408**; on `system1` it returns 504. An
  unreachable llama-server or embed service returns 500 (LiteLLM's `InternalServerError`).
- Steady-state overhead against the stubs was about 5 ms per call. The first call after start costs about 300 ms.
- If a client gives up first (System 2's own deadline), llama-server may keep generating the abandoned request. With
  `-np 1`, the next request waits behind it. This was not measured on the AMD box.
