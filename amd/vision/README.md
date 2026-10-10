# Vision / OCR service (`amd/vision/`, port 8084)

CPU-only FastAPI service that turns a SPOT inspection image into **code-computed readings** plus OCR text, for the
orchestrator to hand to System 2 alongside the image and Laya's output. Contract: [`docs/vision-contract.md`](../../docs/vision-contract.md).
Research behind every design choice: `research/tech-spot-vision-cv-2026-10-10.md`.

**Rule: code produces every number; the VLM never reads values off pixels.** No model calls happen here.

| Reader | Input | What it computes |
|---|---|---|
| `thermal.py` | colour-mapped frame with a vertical colorbar | colorbar → LUT → OCR'd tick labels → RANSAC fit → nearest-colour inversion → max / p95 / median, hotspot blob, reference (scene median outside the hotspot), ΔT, `CLIPPED` |
| `gauge.py` | dial gauge | Hough dial → needle by ray darkness (+ ambiguity: second peak, two-ended needle) → OCR'd labels → angle↔value RANSAC (rejects mis-printed labels) → value; fallback hint range / 270° sweep |
| `spectrogram.py` | jet spectrogram with axes | OCR'd axes → calibration → jet inversion → band levels, peak kHz, HF ratio, burst times (relative only, no dB) |
| `orbit.py` | Orbit screenshot / acoustic imager frame | "Key Results" label…value rows by OCR; `anomaly = snr > threshold` computed; °F→°C; status badge |
| `router.py` | any | explicit kind > action_type > colour/size heuristic > visual (OCR only) |
| `textaxes.py` | shared | RapidOCR (onnxruntime CPU), `parse_num`, `find_ticks`, RANSAC `calibrate_axis` (linear/log/sqrt), `kv_rows` |
| `compare.py`, `annotate.py` | shared | vision-vs-log tolerances (4 °C, max(6 psi, 3 % FS), 3 dB) and Set-of-Mark annotation with `V#` labels |

## Measured on the kit (Mac M-series CPU, 2026-10-10)
| Image | Result | Time |
|---|---|---|
| `thermal_pump_bearing_01.jpg` | V1 max 100.0 °C `CLIPPED` (top of the 25–100 bar), hotspot (149, 66), reference 41.0 °C, ΔT 59 °C → alert severity 4 | 0.8 s |
| `gauge_pressure_01.jpg` | `AMBIGUOUS_NEEDLE` (two-ended: 1 psi vs 193 psi), confidence 0.30, `LABEL_OUTLIER` ("290" rejected), comparison `agrees=null` | 0.24 s |
| `acoustic_valve_01.jpg` | peak 1.78 kHz, 0–2 kHz band strongest (0.63 vs 0.02 above 10 kHz), HF ratio 0.27, `RELATIVE_ONLY` | 0.38 s |
| 3 visual samples | routed to `visual` by action type; no text | 0.15 s |
| Orbit acoustic 11.29.16 / .24 / .51 | SPL 68.06 / 84.24 / 91.16 dB; SNR 167 / 230 / 781 vs 200 → none / severity 2 / severity 4; matches Orbit's NOMINAL/ANOMALY badges | ~2.7 s |
| Orbit 11.29.20 | SNR values hidden under a screenshot thumbnail → `MISSING_VALUE`, not guessed; badge ANOMALY → status alert | 2.8 s |
| Orbit thermal 11.29.05 / 11.30.32 | Region max 415.85 °F = 213.2 °C, min 104.81 °F; 468.41 °F = 242.5 °C | ~2.7 s |
| Orbit gauges 11.30.53 / 11.31.07 / 11.31.42 | 34 psi, 35.6 psi, 73 square-root units; confidence 99 % | ~2.8 s |
| Orbit dashboards / map | `NO_KEY_RESULTS` (nothing invented) | ~2.2 s |

Synthetic ground truth (tests): gauge error ≤ 2 psi on a 0–300 dial (0.7 % FS) at 240 and 360 px, JPEG q60–90;
thermal max within ~2 °C (5×5 smoothing costs ~1.5 °C on a narrow peak), hotspot within 6 px; spectrogram peak
within 0.1 kHz and burst times within 0.05 s.

## Run natively (AMD Jupyter VM: no root, no Docker)
```bash
cd amd/vision
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python scripts/fetch_models.py      # verifies the OCR models (bundled in the rapidocr wheel)
export VISION_API_KEY=$(openssl rand -hex 16)   # required (>= 16 chars); the orchestrator sends the same key
.venv/bin/python scripts/serve.py             # http://127.0.0.1:8084  (VISION_HOST/VISION_PORT to change)
# from your laptop: ssh -L 8084:127.0.0.1:8084 <amd-box>
```
Python 3.12 or newer. Everything is CPU (onnxruntime dropped its ROCm provider in 1.23; OCR is 0.1–1 s here).

## Docker
```bash
docker build -t spot-vision amd/vision          # bakes + smoke-tests the OCR models at build time
docker run --rm -p 127.0.0.1:8084:8084 -e VISION_API_KEY=$VISION_API_KEY spot-vision
```
Non-root (uid 10001), `HEALTHCHECK` on `/health` at `$VISION_PORT`, no runtime internet needed (verified with
`--network none`).

Hardening (contract `vision.2`): `X-API-Key` required on every route but `/health` (start without a key only with
`VISION_ALLOW_NO_AUTH=1`, tests); JPEG/PNG/WebP only; at most `VISION_MAX_PIXELS` (12 MP) checked from the header
before decoding; request body capped before JSON parsing; at most `VISION_MAX_CONCURRENCY` (2) analyses at once,
then 503 after `VISION_QUEUE_TIMEOUT_S` (3 s). A 25 MP PNG used to peak at ~2.5 GB RSS; it is now refused (422)
before its raster is decoded.
Image ~660 MB (opencv-headless + onnxruntime + shapely).

## Try it
```bash
B64=$(base64 < "SPOTDATA/SPOT_KnightHacks_Challenge_Kit Part One/04_ASSETS/sample_inspection_images/thermal_pump_bearing_01.jpg")
curl -s localhost:8084/v1/vision -H 'content-type: application/json' -d "{\"action_type\":\"THERMAL_INSPECTION\",
  \"image_b64\":\"$B64\",\"logged\":{\"reading_id\":\"R1\",\"measurement_type\":\"TEMPERATURE_C\",\"value\":83.5},
  \"annotate\":false}" | python3 -m json.tool
.venv/bin/python scripts/run_kit.py --out /tmp/vision-kit   # every kit image + annotated JPEGs, offline
```

## Tests
```bash
.venv/bin/python -m pytest tests -q                 # ~80 s; kit tests skip when SPOTDATA/ is absent
.venv/bin/python -m pytest tests -q -m "not slow"   # ~30 s; skips the all-18-Orbit-screenshots sweep
```
`VISION_KIT_DIR` points the kit tests at another copy of `SPOT_KnightHacks_Challenge_Kit Part One`.

## Known limitations
- Kit images are ~240 px, synthetic and unlinked to CSV rows: any image-vs-log comparison is a demo pairing.
- Thermal: colorbar must be vertical and on the right; Orbit thermal panes have no colorbar (use the Key Results).
  The flat yellow/white end of ironbow is coarse (±2–5 °C). Reference = scene median outside the hotspot, not a
  chosen "similar component".
- Gauge: assumes the scale gap is at the bottom (angles in (−180°, 180°]); no perspective correction; needle colour
  must be darker than the face. Two-ended needles are flagged, never resolved.
- Spectrogram: relative levels only; jet palette assumed; the kit peak sits at ~1.3–1.8 kHz depending on smoothing.
- Orbit: OCR of the overview + table takes ~2.5 s per 3024 px screenshot on CPU; label set is the 2026-10 Orbit UI.
- OCR runs one request at a time (shared onnxruntime session behind a lock). Scale with more replicas, not threads.
