# Codex kickoff: vision service, phase 1 (code readers + synthetic renders)

> **Superseded (2026-10-10):** `main` has its own vision service (`amd/vision/vision/`, contract `2026-10-10.vision.2`) wired to System 2 `backend.2`. The Codex branch `vision-service` built from this kickoff is **not merged and conflicts with it**. Don't merge it; salvage only its synthetic renders and manifest if needed. Kept for history only.

**How to start Codex.** From the repo root, after `git fetch origin && git checkout -b vision-service origin/claude/cool-darwin-edc92u`:

```
Read AGENTS.md, CLAUDE.md and docs/CODEX-KICKOFF-vision.md, then do the task in the kickoff file end to end.
```

Everything below is the task.

---

## Why this, and why first

We're adding vision to SPOTlight. The plan is in `docs/TEAMMATE-qwen-vision-finetune.md` (the fine-tune brief) and
`research/tech-spot-vision-cv-2026-10-10.md` (the research; §4 readers, §5 OCR, §6 data, §8 architecture). Read both.
Today's date is Sat 2026-10-10 and the Devpost deadline is **Sun 2026-10-11 10:00 AM ET**.

The core rule: **code computes every number; the VLM only explains.** The Qwen fine-tune is blocked until a vision
service produces the readings it trains on ("V# rows") and the annotated images. Nothing for that exists yet
(`amd/vision/` and `docs/vision-contract.md` are missing). That is this task.

## Scope

**In:**
1. `docs/vision-contract.md` (contract first, its own commit).
2. `amd/vision/`: a CPU-only FastAPI service on **port 8084** with the thermal and gauge readers, OCR, V# rows and
   an annotated image.
3. A synthetic renderer that turns `readings.csv` into images with exact ground truth, plus a manifest.
4. A reader evaluation script with committed results.
5. Wiring: `docker-compose.yml`, the ports table, `docs/RUNNING.md`, `Makefile`, `.env.example`, tests.

**Out (don't touch; if you think one needs a change, write it under "Needs owner" in your final report):**
- `amd/system2/` and its contract or schemas (owner: branch `aatif/system2`).
- `amd/system1/` (Laya).
- `backend/`, `amd/mcp/`, `amd/embed/`, `db/`, `web/`.
- The LiteLLM gateway and the LangGraph orchestrator mentioned in the brief. They're not decided yet (see
  `research/decisions.md`, Pending). If `amd/gateway/` or `amd/orchestrator/` appear on origin, leave them alone.
- The fine-tune itself, any GPU work, the acoustic spectrogram reader, route maps.

## Facts you can rely on (checked 2026-10-10)

- Kit: `SPOTDATA/SPOT_KnightHacks_Challenge_Kit Part One/`.
  - `02_DATA/readings.csv` columns: `reading_id, action_id, mission_id, asset_id, location_id, timestamp,
    measurement_type, value, unit, quality, synthetic`.
  - 40 `TEMPERATURE_C` rows (39.8–83.5 °C) and 30 `PRESSURE_PSI` rows (68.6–150.6 psi).
  - **No row links to an image.**
- Kit samples (`04_ASSETS/sample_inspection_images/`, ~240×166 JPEG):
  - `thermal_pump_bearing_01.jpg`: ironbow image with a colour bar labelled 25–100 °C. The hotspot clips at the
    top of the bar (~99.8 °C), so expect a `CLIPPED` flag.
  - `gauge_pressure_01.jpg`: AI-generated, with "290" printed where 250 belongs and a two-ended needle.
  - These 6 images are **eval/demo only**. Never train on them, and never put them in any published dataset.
- Held-out missions (fold 2 in `amd/system1/data/manifest.json`, `holdout_missions`): **M006, M009, M012, M013,
  M017, M018, M019, M020, M023**. Read the list from that file; don't hard-code it.
- Service template to copy: `amd/embed/`.
  - Dockerfile: python:3.12-slim, non-root uid 10001, env-only config, HEALTHCHECK.
  - Plus `.dockerignore`, a compose block using the `*service` anchor, and a header comment in `docker-compose.yml`.
  - This service has no torch, so it takes no `TORCH_VARIANT` build arg. Say so in the Dockerfile header.
- OCR: **RapidOCR on onnxruntime CPU** (`rapidocr-onnxruntime`, Apache-2.0). The research found it reads the kit's
  colour-bar and gauge labels (including the "290"). Upscale 3× when the image height is under 300 px.

## 1. Contract: `docs/vision-contract.md`

Write and commit this before any code. It must cover:

- `GET /health` → `{status, versions: {service, readers, ocr}}`.
- `POST /v1/vision`. Request:
  `{image_b64, action_type?: "THERMAL_INSPECTION"|"GAUGE_READING"|…, asset_id?, logged?: {reading_id,
  measurement_type, value, unit}, calibration?: {unit, min_value, max_value, theta_min_deg, theta_max_deg}}`.

  Response:
  - `router`: `{modality, source: "action_type"|"heuristic"}`. Route on `action_type` when given; otherwise use the
    colour heuristic in research §5.
  - `key_results`: `[{name, units, value}]`, Orbit-style.
  - `vision`: the V# rows (format below).
  - `ocr`: `[{text, conf, quad}]`.
  - `alert`: `{title, severity 0–4, source} | null`.
  - `annotated_image_b64`, `versions`, `latency_ms`.
- **V# row format.** Match this example from the brief exactly:

  ```json
  {"id":"V1","tool":"vision.thermal","quantity":"max_temperature","value":99.8,"unit":"°C","confidence":0.8,
   "trust":"high","flags":["CLIPPED"],"logged_id":"R0042","logged_value":83.5,"delta":16.3,"agrees":false,
   "pairing":"demo"}
  ```

  Rules:
  - `agrees` is `null` when `confidence < 0.5`, and then `trust` is `"low"`.
  - Otherwise `agrees = |delta| <= tolerance`, with tolerance **4 °C** for thermal and **6 psi** for gauges. Make
    both configurable by env var.
  - `pairing` is `"demo"` for kit images and `"synthetic"` for renders.
  - Low-trust rows must never be stated as fact downstream; say this in the contract.
- `POST /v1/ocr` → `{ocr: [...]}`.
- Errors: 400 for bad or undecodable images; 413 above `VISION_MAX_PIXELS` (images are downscaled to at most 1280 px
  on the longest side before anything else).
- A "Feeding System 2" section describing how `vision[]` and `ocr[]` become citable rows. Mark it as a proposal: the
  System 2 owner decides the final rendering.

## 2. Service: `amd/vision/`

- Layout:
  - `app.py` (FastAPI)
  - `readers/thermal.py`, `readers/gauge.py`
  - `textaxes.py` (OCR wrapper, `parse_num`, `calibrate_axis` with RANSAC, `min_samples=2`, failing below 3 inliers)
  - `annotate.py`, `config.py` (env vars)
  - `requirements.txt`, `requirements-dev.txt`, `Dockerfile`, `.dockerignore`, `README.md`, `tests/`
- **Thermal reader** (research §4):
  - Find the colour bar and build a LUT from the median of its centre columns, ends trimmed.
  - OCR the tick labels and fit a line; fall back to the bar's end labels.
  - Map scene pixels to the nearest LUT colour with a distance cut-off, then 5×5 smoothing.
  - Hotspot = the largest blob within max−3 °C. Report max °C, hotspot box, reference-region °C and ΔT.
  - Set `CLIPPED` when the max sits at the top of the bar.
- **Gauge reader** (research §4):
  - Hough circle for the dial centre; needle = the argmax of ray darkness from the centre.
  - Ambiguity = peak / second-peak ratio. A two-ended needle must lower confidence.
  - Calibration chain: OCR'd scale labels → RANSAC `value = a·θ + b` → the request's `calibration` → a per-asset
    file `amd/vision/config/gauges.json` → a default 270° sweep (low confidence).
  - Flag OCR labels that break monotonic spacing (the kit's "290") as `SCALE_LABEL_INCONSISTENT`.
- **Annotated image:** draw the needle line, hotspot box and labels with their V# IDs (Set-of-Mark style), and return
  it as JPEG base64.
- **Cache:** in-process LRU keyed on `sha256(image) + reader versions`.
- **Config:** env vars only (`VISION_HOST`, `VISION_PORT=8084`, tolerances, `VISION_MAX_PIXELS`, `VISION_LOG_LEVEL`).
  - Optional `VISION_LLAMA_URL` is read but unused in phase 1 (VLM label reading comes later); document that.
  - Add examples to `.env.example`.

## 3. Synthetic renderer: `amd/vision/scripts/render_synth.py`

- **One image per `TEMPERATURE_C` and `PRESSURE_PSI` reading, at its logged value.**
  - Gauges: a matplotlib dial (0–200 psi, 270° sweep, labelled ticks) with the needle at the value.
  - Thermal: a Gaussian hotspot at the value over an ambient ~30–40 °C scene, ironbow 25–100 °C, with a labelled
    colour bar.
- **Perturbed twin of every reading** (research §6, brief §3.2): rendered at ±15–40% of full scale, or a stuck
  needle. Plus about 10 **unreadable** cases (heavy glare or occlusion).
- **Domain randomisation:** ~240 px, JPEG quality 40–90, blur, ±8° rotation, glare.
- Seed each image with `sha1(reading_id + variant)` so the output is byte-reproducible.
- **Output:** `amd/vision/data/synth/` plus `manifest.jsonl`, one line per image:
  `{image, reading_id, mission_id, split: "train"|"heldout", measurement_type, unit, logged_value, rendered_value,
  variant: "true"|"perturbed"|"unreadable", calibration, hotspot_box?, seed, renderer_version}`.
  - `split` comes from the manifest's held-out missions.
  - Commit the images if the total stays under ~10 MB; otherwise commit only the manifest and the script.
- **Optional, behind `--with-vision-rows`:** call the running service on each image and write the response next to
  it (`*.vision.json`). The fine-tuner trains on exactly these outputs, so they must come from the service, never be
  hand-written.

## 4. Evaluation: `amd/vision/scripts/eval_readers.py`

Run the readers in-process on the renders. Report the train and held-out splits separately:
- **Gauge:** MAE as % of full scale, and the share within ±2% FS.
- **Thermal:** max-°C MAE, and hotspot-centre error in px.
- **Both:** low-confidence rate, `agrees` accuracy on true vs perturbed twins, unreadable-correctly-flagged rate,
  and p50/p95 latency.
- **The 6 kit samples:** the thermal sample must return `CLIPPED`; the gauge sample must return low confidence
  and/or `SCALE_LABEL_INCONSISTENT`. Record what each returns.

Write `amd/vision/results/readers/{metrics.json, report.md}`. State in `report.md` where it ran (CPU, which
machine). Use only numbers you actually measured.

## 5. Wiring and tests

- **`docker-compose.yml`:** a `vision` service, port 8084, profiles `local, hybrid, neon`, built from `amd/vision`.
  Update the header comment table.
- **Docs:** add `vision` to the ports table in `docs/backend-services-contract.md` and a section to
  `docs/RUNNING.md` (Docker, plus the venv run on the AMD VM).
- **`Makefile`:** add a `test-vision` target to the `test` aggregate.
- **Tests:** `amd/vision/tests/` with pytest, offline, no network:
  - the reader on several renders with known values (tolerances from your eval);
  - contract shape and status codes via FastAPI `TestClient`;
  - the `agrees` / `trust` rules;
  - renderer determinism (same seed gives the same bytes);
  - both kit-sample expectations.
- **`research/decisions.md`:** under "Made", add one or two lines: vision readings are computed in code by
  `amd/vision` (:8084) and the VLM only explains. Leave the gateway and orchestrator under Pending.

## Order, commits, stop

1. **Order:** contract → `textaxes` + thermal reader + tests → gauge reader + tests → renderer → eval → service and
   annotated image → Docker and compose → docs.
2. **Commits:** one per step, pushed to `vision-service` as you go so teammates can pull early. No PR, no merge to
   `main`.
3. **Done when:**
   - `make test-vision` passes;
   - `docker compose --profile local config --quiet` passes;
   - the image builds and `/health` is healthy;
   - the eval report is committed.
4. **Final report:**
   - what works, with measured numbers;
   - what's stubbed;
   - "Needs owner" items (for example, System 2 accepting `context.vision[]` and `image_b64`);
   - exact commands for the fine-tuner to generate renders plus `.vision.json` files.
5. **Time box:** if the gauge reader isn't within ±5% FS on renders after about 5 hours, ship it with honest numbers
   and low confidence rather than stalling. The thermal reader and renderer are the critical path.
