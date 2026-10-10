# Codex kickoff: vision fine-tune dataset + vision faithfulness eval set

> **Paused (2026-10-10):** the dataset waits until fine-tuning is back on the table (System 2 is Qwen3.8-27B with no fine-tune). Before reuse, rebase it on `main`'s vision service and System 2 `backend.2` (trust `HIGH`/`LOW`, pairing `linked`/`demo`), not on the `vision-service` branch.

**Prerequisite:** System 2 phase A, i.e. System 2 consumes `context.vision[]` (see
`docs/NOTE-aatif-system2-vision.md`), pushed to a branch (suggested `aatif/system2-vision`). Without it, this task
would have to guess the prompt format, so the training data would drift from serving.

**How to start:**
```
git fetch origin && git checkout -b vision-dataset origin/vision-service && git merge origin/aatif/system2-vision
```
Then give Codex: `Read AGENTS.md, CLAUDE.md and docs/CODEX-KICKOFF-vision-dataset.md, then do the task end to end. Push only to origin vision-dataset.`

---

## Goal
Build a dataset of (image + packet → System 2 JSON answer) examples. Its train split is for an optional LoRA
fine-tune of the System 2 VLM. Its held-out split is the **vision faithfulness eval**, which we need even if we never
fine-tune. Background: `docs/TEAMMATE-qwen-vision-finetune.md` §2–§3 and §6.2, and
`research/tech-spot-vision-cv-2026-10-10.md` §6–§7.

## Scope
**In:** a renderer option, a dataset builder, a dataset card, tests and counts.

**Out:**
- any change to `amd/system2/` (owner: Aatif; import it, never edit it);
- the backend and web;
- training;
- uploading anywhere (no tokens in this task).

## 1. Renderer: `--copies N` in `amd/vision/scripts/render_synth.py`
- `--copies 1` (the default) must reproduce today's 150 files **byte for byte**, keeping today's names and seeds.
- Copy k≥2 seeds with `sha1(reading_id + variant + str(k))`, names files `R0002-true-c2.jpg`, and adds `copy` to the
  manifest.
- Same split rule: the manifest's `split` comes from `amd/system1/data/manifest.json` `holdout_missions`.
- Unreadable variants stay limited to about 10 readings, as now.
- Write copies to a separate directory (`--out amd/vision/data/synth_x4`) so the committed 150 stay untouched.

## 2. Builder: `amd/vision/scripts/build_finetune_dataset.py`
For each manifest row:
1. Get the vision response: run the service in-process via FastAPI `TestClient` (no network), or read the
   `*.vision.json` written by `render_synth.py --with-vision-rows`. Request it with `logged` = the manifest's reading
   and `pairing: "synthetic"`.
2. Build a backend-style request (`BackendAssessRequest`):
   - `flag_id`: a unique positive int.
   - `context.facts`: the logged reading row from `readings.csv` (`id` = `reading_id`, `measurement_type`, `value`,
     `unit`, `quality`) plus the asset row from `assets.csv`.
   - `context.vision`: the V# rows.
   - `allowed_actions`: `MANUAL_READING, CHECK_SENSOR_PAYLOAD, MONITOR, DISPATCH_TECHNICIAN, MANUAL_REVIEW`.
   - `suggested_action`: `MANUAL_READING` when the first V# row has `agrees` false or trust is low, else `MONITOR`.
   - `question`: rotate 3 fixed phrasings, for example "Does the camera agree with the logged reading?".
3. `prepared = normalize_packet(request)`. Assert every V# id is in `prepared.content`. If not, System 2 phase A
   isn't in your branch: stop and report.
4. `messages = build_messages(...)` / `request_body(...)` from System 2, exactly as served, with the **annotated**
   image as the image part if System 2 phase B exists; otherwise text only, and record `image_path` for later.
5. `target = template_assessment(prepared)`, then `validate_generated(target, prepared)` and
   `check_assessment`-style grounding. **Drop and count** any example that fails; never patch it by hand.
6. Write `amd/vision/data/finetune/{train,heldout}.jsonl`, one line each:
   `{id, messages, target, image_path, meta: {reading_id, mission_id, split, variant, copy, measurement_type, agrees, trust, prompt_version, contract_version}}`.

**Guards (tests must cover all of them):**
- No train example comes from, or cites a row from, a held-out mission (M006, M009, M012, M013, M017, M018, M019,
  M020, M023; read them from the manifest file).
- **Never** a kit image (`SPOTDATA/…`) in any split.
- The same inputs give byte-identical JSONL.
- Every target passes `validate_generated`.
- A disagreement case cites both the V# row and the logged reading row.
- Low-trust targets contain no number from the V# row.

## 3. Dataset card: `amd/vision/data/finetune/README.md`
Cover:
- sources and licences: renders are ours, built from kit CSV values; no kit images; MeasureBench is never used;
- the generation command;
- counts per split, variant and measurement type;
- the held-out missions;
- `prompt_version` and `contract_version`;
- limits: synthetic images, template-quality targets, "the model does not read gauge values; code does".

## 4. Size and commits
- Target: ≥300 train examples (`--copies 4`).
- Commit the JSONL and the card. Commit images only if the total stays under ~20 MB; otherwise commit the manifest
  and the command, and note that the images are regenerated deterministically.
- **Done when:** the tests pass, `make test-vision` passes, and the card's counts match the files.
- **Final report:** the counts, the dropped-example count with reasons, and the exact commands to regenerate on the
  AMD box (Python 3.12 venv, `make vision-venv`; no Docker there).
