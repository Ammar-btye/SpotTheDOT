# Note for Aatif: System 2 accepting vision evidence (V# rows, optional image)

> **Superseded (2026-10-10):** System 2 phase A and B already landed on `main` as contract `2026-10-10.backend.2` (`amd/system2/INTEGRATION-multimodal.md`, `PROMPT_FORMAT.md`). It differs from this note: trust is `HIGH`/`LOW`, and pairing is `demo`/`linked`. Kept for history only.

**From:** the team (drafted with Claude), Sat 2026-10-10. **You own this;** nothing here has been changed in
`amd/system2/`. It's a proposal grounded in the current code; adjust as you see fit.

## Why
The vision service is done on `vision-service`: `amd/vision`, :8084, contract in `docs/vision-contract.md`.
- It computes thermal/gauge readings in code and returns V# rows, for example:
  `{"id":"V1","tool":"vision.thermal","quantity":"max_temperature","value":99.8,"unit":"°C","confidence":0.8,"trust":"high","flags":["CLIPPED"],"logged_id":"R0042","logged_value":83.5,"delta":16.3,"agrees":false,"pairing":"demo"}`
- The demo moment: the camera and the log disagree, and System 2 says so, citing both.
- The vision fine-tune dataset and the vision faithfulness eval are blocked on System 2 consuming these rows. The
  dataset builder must use your `normalize_packet` / `build_messages` so training matches serving byte for byte.

## What the code does today (checked on `main`)
- `BackendAssessRequest` has `extra="ignore"`, and `normalize_packet` only reads `facts, manual, policy,
  similar_incidents, asset_history, system1, event, mission, flag`. **A `context.vision` list is silently dropped.**
- Of the V# fields, `_evidence_object` already keeps `value`, `unit` and `trust`. It drops `tool`, `quantity`,
  `pairing`, `logged_id`, `confidence`, `logged_value`, `delta`, `agrees` and `flags`. `flags` is a list of strings,
  and `LIST_FIELDS` only takes lists of objects.
- `template_assessment` cites `sorted(content)[:2]`, so V# rows would rarely be cited, even when they disagree.
- `packet_hash` covers the content only, so an image would not enter the cache key.
- Grounding already handles `°C` and psi in `UNIT_RE`/`UNITS`, so numeric checks on V# claims should work as-is.

## Proposed change, phase A (rows only, no image; small and additive)
1. **Contract:** `context.vision: [V# row]` optional. Bump `BACKEND_CONTRACT_VERSION` to `2026-10-10.backend.2` and
   update `docs/backend-services-contract.md`.
2. **`packet.py`:**
   - Read `vision` like the other list sections.
   - Add `tool`, `quantity`, `pairing` and `logged_id` to `TEXT_FIELDS`; `confidence`, `logged_value` and `delta` to
     `NUMBER_FIELDS`; and `agrees` to `BOOL_FIELDS`.
   - Allow `flags` as a list of strings.
   - **Low-trust rows:** consider turning `trust:"low"` rows into a text fact with no number, for example
     `"Camera reading unavailable (low confidence; flags: SCALE_LABEL_INCONSISTENT)."` The model then *cannot* state
     the value. That enforces the contract's "never stated as fact" rule structurally rather than by prompt.
   - Clipped readings: when `CLIPPED`, the value is the colour-bar maximum. Consider wording it as "at or above"
     (the kit sample reads 100.97 °C on a 100 °C bar).
3. **Logged row must be present:** when a V# row has `logged_id`, the packet should also contain that reading row
   (`id = reading_id`), so the model can cite both. The backend supplies it; reject or flag `citation_ids` if it's
   missing.
4. **`template.py`:** this is the baseline *and* the source of the fine-tune targets.
   - If any V# row has `agrees:false`: cite that V# row plus its logged row. Action `MANUAL_READING`, else
     `CHECK_SENSOR_PAYLOAD`, else `MANUAL_REVIEW` (first one in `allowed_actions`). Confidence `medium`.
   - If a V# row is low-trust: cite it, action `MANUAL_READING`/`MANUAL_REVIEW`, confidence `low`.
   - Otherwise: unchanged.
5. **`prompts.py`:** bump `PROMPT_VERSION` to `analyst-prompt-2026-10-10.2`, and add to `SYSTEM`:
   "V rows were computed by code from an inspection image. Never read numbers off an image. If a V row has
   agrees=false, cite it and the logged reading it names, and prefer a manual check. If a V row is unavailable or
   low confidence, say the image was unreadable."
   Few-shots: keep 3, but when the packet has V# rows, swap one example for a vision example from training missions
   only.
6. **Tests:**
   - V# rows survive normalisation.
   - A low-trust row has no number in its content.
   - A disagreement makes the template cite V# plus the logged row with `MANUAL_READING`.
   - An unknown `vision` field is still ignored.
   - **No regression:** `python scripts/report.py --rebuild results/report/template --out-dir /tmp/rb` must still
     print `rebuild: identical`. The held-out packets have no V# rows, so nothing should change.

## Phase B (optional, after A): the image itself
- Add `image_b64` to the request (the annotated image from the vision service).
- In `generation.request_body`, when present, make the final user message `[{"type":"image_url",…}, {"type":"text",…}]`:
  image first, packet text after, question last.
- Add `sha256(image)` to the cache key, either via `packet_hash` or `KEY_FIELDS`.
- The server needs `--mmproj`. Whether an image and `json_schema` work together on our llama.cpp build is tested by
  GPU D in `docs/AMD-RUNS-2026-10-10.md`; wait for that result.

## Who else is involved
- **Backend:** it calls `POST /v1/vision` and puts `vision[]` (plus the logged reading row) into `context`.
  - The kit has no image per reading, so the demo uses the synthetic render for a reading (`amd/vision/data/synth/manifest.jsonl`, by `reading_id`) or the kit sample by action type (`pairing:"demo"`).
  - That's a backend-owner change; say if you want it.
- **Dataset builder (Codex, `docs/CODEX-KICKOFF-vision-dataset.md`):** imports your phase-A code. Please push phase A
  to a branch (suggested `aatif/system2-vision`) and say when it's there.
