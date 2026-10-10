# Integrating `amd/vision/` (for the integrator agent)

Everything below goes into shared files this agent did not touch. Contract: `docs/vision-contract.md` (new, owned
by this folder). Verified: `docker build -t spot-vision amd/vision` builds on python:3.12-slim, runs as uid 10001,
turns healthy in ~5 s, and OCR works with `--network none`.

## 1. `docker-compose.yml`
Header table row (keep the column alignment):
```
# vision     8084  local, hybrid, neon, vision  CPU OCR + code readers (thermal/gauge/spectrogram/Orbit Key Results),
#                                           POST /v1/vision, /v1/ocr. No model calls. Required VISION_API_KEY (X-API-Key)
```
Profiles comment block, add:
```
#   vision  vision/OCR service only, for independent checks (COMPOSE_PROFILES=vision)
```
Service block (application section, after `system2`):
```yaml
  vision:
    <<: *service
    build: {context: amd/vision}
    image: spot-vision:compose
    profiles: [local, hybrid, neon, vision]
    environment:
      VISION_HOST: 0.0.0.0
      VISION_PORT: "8084"
      VISION_API_KEY: *vision-key     # x-keys: vision: &vision-key ${VISION_API_KEY:-spot-vision-dev-key-change-me}
      VISION_MAX_IMAGE_BYTES: ${VISION_MAX_IMAGE_BYTES:-12000000}
      VISION_MAX_PIXELS: ${VISION_MAX_PIXELS:-12000000}
      VISION_MAX_CONCURRENCY: ${VISION_MAX_CONCURRENCY:-2}
      VISION_QUEUE_TIMEOUT_S: ${VISION_QUEUE_TIMEOUT_S:-3}
      VISION_WORK_MAX_SIDE: ${VISION_WORK_MAX_SIDE:-1280}
      VISION_CACHE_SIZE: ${VISION_CACHE_SIZE:-64}
      VISION_OCR_THREADS: ${VISION_OCR_THREADS:--1}
      VISION_LOG_LEVEL: ${VISION_LOG_LEVEL:-info}
    ports: ["${BIND_ADDR:-127.0.0.1}:8084:8084"]
    # Non-root runtime and healthcheck are inherited from the image. OCR models are baked in at build time.
```
The orchestrator service should get `VISION_URL: ${VISION_URL:-http://vision:8084}` and the same
`VISION_API_KEY` plus `depends_on: {vision: {condition: service_healthy, required: false}}`.

## 2. `.env.example`
```
# Vision/OCR service (amd/vision, :8084). Hybrid: run natively on the AMD box and tunnel 8084.
VISION_URL=http://vision:8084
VISION_API_KEY=change-me-vision-key-0123456789   # required, >= 16 chars; vision and orchestrator share it
# VISION_MAX_IMAGE_BYTES=12000000
# VISION_MAX_PIXELS=12000000
# VISION_MAX_CONCURRENCY=2
# VISION_QUEUE_TIMEOUT_S=3
# VISION_WORK_MAX_SIDE=1280
# VISION_CACHE_SIZE=64
# VISION_OCR_THREADS=-1
```

## 3. Ports table in `docs/backend-services-contract.md`
```
| Vision / OCR (code readers, `/v1/vision`, `/v1/ocr`; contract `docs/vision-contract.md`) | `amd/vision/` | 8084 | vision agent |
```

## 4. `docs/RUNNING.md`
Service table row:
```
| `vision` | 8084 | local, hybrid, neon, vision | `amd/vision/` | CPU-only OCR (RapidOCR/onnxruntime) + code readers: thermal colorbar, dial gauge, spectrogram, Orbit Key Results. `POST /v1/vision` returns `V#` readings, vision-vs-log `comparison`, Orbit-style `key_results`/`alert` and an annotated JPEG; never calls a model. Required `VISION_API_KEY` (header `X-API-Key`). Models baked into the image; no runtime internet. Contract: `docs/vision-contract.md`. |
```
New section:
````markdown
## Vision / OCR on 8084
```bash
docker compose --profile vision up -d --build vision
curl -s localhost:8084/health            # {"status":"ok","ocr_ready":true,...}
# Native (AMD VM, no Docker):
cd amd/vision && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python scripts/serve.py        # 127.0.0.1:8084; tunnel with ssh -L 8084:127.0.0.1:8084 <box>
# Every kit image through every reader, offline, with annotated JPEGs:
.venv/bin/python scripts/run_kit.py --out /tmp/vision-kit
```
Readings are computed by code; System 2 gets them as `context.vision[]` `V#` rows (see the contract's last section).
````

## 5. `Makefile`
```make
PY_VISION := amd/vision/.venv/bin/python

test-vision: ## vision/OCR unit tests (offline; kit-image tests skip without SPOTDATA/), ~80 s
	cd amd/vision && .venv/bin/python -m pytest tests -q -p no:cacheprovider

test-vision-fast: ## vision tests without the all-Orbit-screenshots sweep, ~30 s
	cd amd/vision && .venv/bin/python -m pytest tests -q -m "not slow" -p no:cacheprovider
```
Add `test-vision` to the `test:` prerequisites and `.PHONY`, and to `venvs:`:
```make
	test -x $(PY_VISION) || (python3 -m venv amd/vision/.venv && amd/vision/.venv/bin/pip install \
	  -r amd/vision/requirements.txt -r amd/vision/requirements-dev.txt)
```

## 6. `.github/` CI (if a workflow runs the per-service suites)
`pip install -r amd/vision/requirements.txt -r amd/vision/requirements-dev.txt` then
`cd amd/vision && python -m pytest tests -q -m "not slow"`. SPOTDATA is git-tracked, so the kit tests run in CI
too; they skip cleanly if a sparse checkout drops it.

## 7. `docs/ARCHITECTURE.md`
The old sketch put `/v1/vision` on System 2's port. It now lives in `amd/vision/` on 8084 (CPU, no VLM); the VLM step
is System 2 `/v1/assess` with `context.vision[]` + `image_b64` (the annotated image), called by the orchestrator.

## 8. `research/decisions.md` (one line, if the team agrees)
- Vision readings come from a separate CPU service (`amd/vision`, :8084) that never calls a model; System 2 gets
  `V#` rows + the annotated image. Why: VLMs score 25–30 % on gauges/thermal; code is deterministic and testable.
