# Integration log, 2026-10-10

This is the integrator's record of what changed to make the four services (db + embed, system1, mcp, backend) run
together, and the proof that they do. Every change is listed with its file, what changed and why. Audit ids refer
to `docs/audit-2026-10-10.md`, which this log does not edit. Nothing is committed.

## How to run (three modes)
`docs/RUNNING.md` has the details. Run `cp .env.example .env`; `COMPOSE_PROFILES` in that file picks the mode.
There is one root `docker-compose.yml`, with profiles inside it. System 2 is a commented placeholder (port 8083;
the code is on branch `aatif/system2`). Until it lands, the backend uses `SYSTEM2_URL` from `.env`.

| Mode | In Docker | Elsewhere | `.env` |
|---|---|---|---|
| `local` (default) | db, db-init, embed, system1, mcp, backend, all on CPU | nothing | defaults |
| `hybrid` | db, db-init, mcp, backend | system1 and embed run natively on the AMD GPU VM (no root, no Docker), reached through an SSH tunnel | `SYSTEM1_URL`, `EMBED_URL` = `http://host.docker.internal:<tunnel port>` |
| `neon` | db-init, mcp, backend (`neon,models` adds embed and system1 on CPU) | Neon replaces `db` | `DATABASE_URL` (owner, for db-init), `BACKEND_DATABASE_URL`, `MCP_DATABASE_URL` |

**Startup order** is gated by healthchecks:
1. `db` (pg_isready) and `embed` (model loaded) become healthy.
2. `db-init` runs: migrate, login users, seed, ingest, status. It must exit 0.
3. `mcp` starts.
4. `backend` starts, once `system1` and `embed` are also healthy.

Any dependency outside the active profile is marked `required: false`.

**Database roles:**
- `db-init` runs as the owner.
- `backend` logs in as `spot_app_user` (in `spot_app`).
- `mcp` logs in as `spot_mcp_user` (in `spot_mcp_reader`). So does system1, for its `app.model_calls` logging.

## Changes (file: what, why)

### New files (owned by the integrator)
- `docker-compose.yml`: the one compose file for the whole project.
  - Contents: a header table (service, port, profile), the anchors `x-service` and `x-embed-env`, and the
    default URLs in `x-db-urls`.
  - Profiles: `local`, `hybrid`, `neon` and `models`. Service URLs use service names, never localhost.
  - Each service gets its own DB role. Timeouts are sized for CPU.
  - Volumes: a shared `hf-cache` volume, and a read-only checkpoint mount at `/models/checkpoints`.
  - A System 2 placeholder (coordinator requirement).
- `.env.example` (root): the mode, the build options, DB passwords, Neon URLs, AMD tunnel URLs and timeouts.
- `.gitignore` (root): `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.DS_Store`. The repo had no root
  ignore file, so a root `.env` holding passwords, or the new `amd/mcp/.venv`, could have been committed.
- `Makefile`, with these targets:
  - `up`, `down`, `wipe`
  - `test`: the policy guard, backend, system1 and mcp suites
  - `test-backend-integration`, `smoke`, `e2e`, `venvs`
- `scripts/db_login_roles.py`: creates or updates the LOGIN users inside 007's NOLOGIN group roles. It is idempotent
  and works on Neon. Without it, the services could only connect as the owner.
- `scripts/e2e.py`: the end-to-end proof (see Results).
- `tests/test_policy_consistency.py`: the cross-service drift guard (seam 2).
- `docs/RUNNING.md`: the three modes, the service table, how to extend the compose file, and CPU and GPU latencies.
- `amd/mcp/.venv` (local, gitignored): the MCP test venv, which did not exist before.

### Fixes inside service folders
| File | Change | Why |
|---|---|---|
| `db/migrations/008_spot_event_log_request_id.sql` (new) | Runs `ADD COLUMN IF NOT EXISTS request_id` on `raw.spot_event_log` and adds an index. | **Seam 1 / audit R1.** The contract listed the column, but no migration created it. The backend writes the column only when it exists, so the value was being dropped. 007's table-level grants already cover the new column. No backend change was needed: `append_raw` picks it up from its 60 s column cache. |
| `docs/backend-services-contract.md` | Adds the `SYSTEM1_INGEST_TIMEOUT_S` row, the effective breaker cooldown, and a "System 1 load and logging" paragraph. | Audit H1, H2 and M2. The contract is changed first, per CLAUDE.md. |
| `backend/app/deps.py` | Each breaker's cooldown is now `max(BREAKER_COOLDOWN_S, that client's timeout)`. | **H1.** The 10 s cooldown was shorter than the 30–60 s timeouts, so a hung service stalled the replay once every cooldown window. With the contract's GPU defaults (timeout 5, cooldown 10), nothing changes. |
| `backend/app/config.py` | Adds `SYSTEM1_INGEST_TIMEOUT_S`. It defaults to `SYSTEM1_TIMEOUT_S`, so existing behavior is unchanged. | **H1.** Ingest needs a short timeout and fails fast to rules-only. Explicit batch calls keep the long timeout. |
| `backend/app/services/system1.py` | Ingest calls use `skip_if_busy` and the ingest timeout. While a batch call (forecast or `/system1/predict`) is in flight, ingest raises `busy: ...` without touching the breaker. Successful calls are no longer logged here. | **H1, H2, M2.** |
| `backend/app/services/ingest.py` | Passes `skip_if_busy=True`. | **H2.** Ingest never queues behind a forecast; the event gets rules-only, marked `laya_unavailable` / `busy`. |
| `backend/app/routers/system1.py` | `FORECAST_LIVE_MAX = 5` live Laya items per forecast request. The rest get the baseline. | **H2.** On CPU an uncapped 10-action forecast held Laya for about 24 s or more. |
| `backend/tests/test_ingest.py` | One assertion now expects no backend `system1` success row. Two new tests cover the H1 cooldowns and the H2 busy-skip. | Follows the M2 contract change; the new tests cover the fixes. |
| `backend/tests/test_fallbacks.py` | The forecast test now expects 5 live items and the rest baseline. | Follows the H2 cap. |
| `backend/tests/test_integration.py` | Expects no backend `system1` rows when System 1 is mocked. | Follows M2. |
| `backend/README.md` | The resilience line and the env table now describe H1 and H2. | Docs follow the code. |
| `db/policy_rules.py` | `BASE_SCORE` is now P3 45 / P4 20, and the score formula is the backend's rules-only `base + 9·min(1, Σweights/6)`, capped at 99. Four detail texts (`failed_on_critical_asset`, `battery_low`, `action_failed`, `mission_reported_failed`) now use the backend's wording. | **M11 / score drift.** The backend validator is canonical because it scores live flags. Seeded and live flags now share one scale. |
| `amd/mcp/spot_mcp/domain.py` | `band_check`: a missing quality is now untrusted (`quality != "GOOD"`). | **L2.** This matches `policy.reading_state`. |

### Runtime fixes found while bringing the stack up (B)
- **`docker-compose.yml` `embed`.**
  - Set `EMBED_BATCH=8`. The server's encode batch defaults to 32.
  - Added `restart: unless-stopped` to the long-running services.
  - Why: during the `db-init` ingest, embed was OOM-killed (`OOMKilled=true`, exit 137). It reached about 3.4 GB,
    plus system1's 2.1 GB, in the 7.6 GB Docker VM.
  - After the fix, the peak was 3.9 GB with no OOM. Ingest is idempotent, so it resumed after the 297 event docs
    it had already committed.
- **Local `.env` only: `DB_PORT=5434`.** Another agent's `spot-pgvector` container holds 5433. The compose default
  is still the contract's 5433.
- **Operational: Laya's weights were copied** from `~/.cache/huggingface` into the `hf-cache` volume. The host's
  xet blob symlink was dereferenced. This saves an 842 MB download.

## Seam 2: triage rules in several places (drift report)
`tests/test_policy_consistency.py` is part of `make test` (`make test-policy`). It needs only the stdlib and pytest.
It runs over all 297 kit action and mission events and checks:
- **The MCP vendored `policy.py` against the canonical `amd/system1/triage/policy.py`:** every threshold and the
  full `label_*` output.
- **`db/policy_rules.py`:** priority and escalate.
- **`backend/app/services/validator.py`:** escalate, priority, category, top tier, and fired rule names compared
  with db's. This is a fourth copy: it restates the predicates.
- **Seeded vs live flags (`db/policy_rules.evaluate` vs backend `combine(mode, laya=None)`, both modes):** score and
  severity.
- **Per-rule detail texts:** db vs backend.
- **MCP `band_check`:** compared with `reading_state`, including a None, blank or non-GOOD quality.
- **MCP `battery_status`:** compared with the policy's battery cliffs.

**Drift found:**
- No threshold or verdict drift (all 297 events agree).
- **Scores:** before the fix, 138 events differed (P3 40 vs 45, P4 10 vs 20, and +3 per rule vs +9·p).
- **Detail texts:** 4 rules differed.
- **MCP null quality (L2):** `band_check` treated a missing quality as trusted.

All of these are fixed. **25 passed.**

Mutation checks:
- Vendored `BATTERY_LOW` 25 → 26: 16 tests fail.
- `BASE_SCORE` P3 → 40: 138 drifts reported.

## Results

### Test suites (D)
| Suite | Result |
|---|---|
| `tests/test_policy_consistency.py` | 25 passed |
| backend unit tests (`SKIP_INTEGRATION=1`) | 57 passed, 3 skipped |
| backend, all tests against the compose DB (`INTEGRATION_DATABASE_URL`) | 60 passed (3 integration tests, including the `spot_app` write path) |
| system1 service (real base Laya on CPU) | 20 passed (18–38 s) |
| mcp unit tests | 33 passed, 4 skipped |
| mcp tests with `DATABASE_URL` (the `spot_mcp_user` role) and `EMBED_URL` pointing at the stack | 36 passed, 1 skipped |
| `make smoke` (`db/smoke_test.py --roles`, inside the stack) | 3 RAG queries OK, `HX-204` gives `text_match` on HX-204 docs only, 9 of 9 role checks OK (spot_mcp_reader can SELECT and INSERT into `app.mcp_tool_calls`; UPDATE, DELETE, `app.model_calls` SELECT and `raw.kit_rows` are denied) |
| amd/embed, db | No unit tests exist (covered by smoke, ingest and e2e) |

### End-to-end (C): `make e2e`, both TRIAGE_MODEs: **70 checks, 0 failed**
Five kit replay events per mode go through `POST /api/v1/events?triage_mode=<mode>`. Each has its own
`X-Request-ID` and a source unique to the run and mode.

Trace for one request, `e2e-052515274b-s-0` (event E00063, the A0029 result, HX-204):

| Table | Row |
|---|---|
| `raw.spot_event_log` | `log_id` 2007, with `request_id` (the 008 column) |
| `events` | E00063, with `payload.triage.request_id`, `flag_id` 5 and `triage_event_id` `act-A0029` |
| `system1_predictions` | escalate=A, priority=P1, category=none, reading_trust=C |
| `flags` | flag 5, escalated; `reasons`: "Laya: escalate (0.52) · rules: confirmed", `triage_mode` serial |
| `app.model_calls` | exactly one `system1` row (written by the service), 2776 ms |
| `app.request_log` | `/api/v1/events` 200, 2797 ms |

`system1_predictions` and `flags` have no `request_id` column. They are reached through `events.payload.triage`
(`flag_id`, `triage_event_id`) and the prediction's `created_at`.

The other checks:
- **Context (A2):** `/flags/5/context` returned `source=mcp` with 20 `citation_ids` (`flag:5`, `action:A0029`,
  `asset:HX-204`, ...). `app.mcp_tool_calls` has a `get_flag_context` row under the context call's own request_id,
  with `top_similarity` 0.753. That row proves the packet came from the mcp container.
- **Explain (A3):** `/explain` returned `source=template` ("SYSTEM2_URL is not set") with `context_source=mcp`.
- **Search (A4):** `/search?q=HX-204` returned 8 hits in `mode=hybrid`; the top hit was `incident:flag-2`.

Per-hop latency on CPU, Docker Desktop on an arm64 Mac:

| Hop | Measured |
|---|---|
| ingest, action event (wall) | 2.29–2.99 s |
| ↳ System 1 server-side (`app.model_calls`) | 2.28–2.97 s, so Laya is about 99% of the time |
| ↳ backend pipeline overhead (raw, events, predictions, validator, flag; 6 SQL steps) | 3–20 ms |
| ingest, mission event | 1.82–1.91 s (Laya 1.81–1.90 s) |
| context via MCP, cold | 1069 ms (one query embedding: 923 ms) |
| context via MCP, warm (query embedding cached) | 21–22 ms (tool: 13 ms) |
| explain (template) | 20–25 ms |
| search, hybrid (embedding + SQL) | 166–214 ms |
| live forecast (5 actions, capped) | ~13 s |
| ingest while a forecast holds Laya (H2) | 40 ms, rules-only, `busy` |

**Serial vs parallel.** The verdicts below are base Laya's (not fine-tuned).

| Event | Laya | Rules | serial | parallel |
|---|---|---|---|---|
| E00063 (A0029) | escalate 0.52 | P2 | escalated P1, confirmed | same |
| E00005 (A0002) | log 0.46 | P4 | not escalated, **P2**, both_routine | same |
| E00131 (A0060) | log 0.45 | **P1** | **not escalated** (rules_only_escalate; the seeded flag is un-escalated) | **escalated P1** |
| E00003 (A0001) | escalate 0.60 | P3 | **not escalated**, P1 (rules_rejected) | **escalated P1** (new flag 241) |
| E00022 (M001) | escalate 0.62 | P2 | escalated P2, confirmed | same |

What differs:
- **Serial drops a rules-P1 event that base Laya misses** (A0060). Parallel catches it.
- **Parallel escalates a rules-P3 event on Laya's word alone** (A0001).
- **Both modes label non-escalated events P1 or P2.** This is audit M1, which is left for the user to decide.

## Still not integrated
- **System 2 and llama-server:** not on main (branch `aatif/system2`). `/explain` and debriefs are templates. The
  compose file has a placeholder; set `SYSTEM2_URL` in `.env` to use one running elsewhere.
- **Fine-tuned Laya:** the stack runs base `convaiinnovations/laya`. Its triage quality is weak: category=none on
  a P1 event, and P2 on routine events. The checkpoint mount is ready: set
  `LAYA_CHECKPOINT=/models/checkpoints/<run>/best`. Only `checkpoints/smoke` exists locally.
- **Neon:** the profile and role script are written but untested (no credentials). Only local PG17 was tested.
- **Hybrid against the real AMD box and the ROCm images:** untested.
- **Left to the user:** audit H3 (auth on destructive endpoints, CORS `*`) and M1 (parallel-mode escalation of P4/LOW).
- **Other open audit items:** M3–M10 and L1, L3–L12. In particular:
  - **M5:** `db-init` re-runs `seed` on every `make up`, which refreshes seeded flags and events.
  - **M10:** template explanations are cached as final.

## Audit fixes (fixer, 2026-10-10, user-approved: H3, M1, M4, M5, M10, M7)
Contracts were changed first (`docs/backend-services-contract.md`, `docs/system2-rag-contract.md` §4). Nothing is
committed. Per audit id, file: change.

**H3: admin token on destructive/ingest endpoints, CORS restricted**
- `docs/backend-services-contract.md`: new "Admin endpoints" section; env rows `ADMIN_TOKEN`, `CORS_ORIGINS` (default `http://localhost:3000`).
- `backend/app/config.py`: `ADMIN_TOKEN` setting; `CORS_ORIGINS` default is `http://localhost:3000` instead of `*`.
- `backend/app/deps.py`: `require_admin` dependency: `X-Admin-Token` compared with `hmac.compare_digest`; unset token → 503 `admin_token_unset`, missing/wrong → 401 `unauthorized`; no bypass.
- `backend/app/main.py`: `AdminAuthError` handler (same `{error, detail, request_id}` shape); CORS uses `CORS_ORIGINS` only.
- `backend/app/routers/ops.py`, `replay.py`: router-level `require_admin` (every `/ops/*` and `/replay/*` route).
- `backend/app/routers/events.py`: `require_admin` on `POST /events` and `POST /events/batch` (the `GET` feed stays open).
- `docker-compose.yml`: backend gets `ADMIN_TOKEN: ${ADMIN_TOKEN:-}` and `CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:3000}`; header comment updated.
- `.env.example`: `ADMIN_TOKEN=` (with how to generate it) and `CORS_ORIGINS`. Local `.env` (gitignored): a generated `ADMIN_TOKEN` and `CORS_ORIGINS`.
- `docs/RUNNING.md`, `backend/README.md`: setup step for the token, admin-endpoint note, curl examples send `X-Admin-Token`.
- `scripts/e2e.py`: sends `X-Admin-Token` (from `ADMIN_TOKEN` env, else `.env`); new A0 checks (no token → 401, wrong token → 401, token → 200, foreign CORS origin rejected).
- `backend/tests/conftest.py`: the harness client sends the test token; `backend/tests/test_integration.py` clients too.
- `backend/tests/test_auth.py` (new, 37 tests): every admin route × missing/wrong/empty token → 401 with nothing run; token unset → 503; token → 200; read/ack/explain routes stay open; CORS allows only the configured origin; env parsing.

**M1: priority consistent with escalation in both TRIAGE_MODEs**
- `docs/backend-services-contract.md` step 6: escalated ⇒ P1/P2, not escalated ⇒ P3/P4, severity/score follow.
- `backend/app/services/validator.py`: new `consistent_priority()` applied in `combine()` for both modes (escalated P3/P4 → the rules' P1/P2, else P2; not escalated P1/P2 → P3). Replaces the serial-only guard.
- `backend/tests/test_validator.py`: the audit's 3 probed cases + 8 serial/parallel cases (escalated, priority, severity, score band), and an exhaustive invariant sweep over every (mode, kind, Laya escalate/priority, rules priority, Laya down) combination; one old expectation (serial rules_rejected P1) is now P3. Mutation check: removing the clamp fails 12 tests.

**M4: one overall request deadline on `/flags/{id}/context` and `/explain`**
- `docs/backend-services-contract.md`: "Request deadline" section; env row `REQUEST_DEADLINE_S` (default 45).
- `backend/app/config.py`: `REQUEST_DEADLINE_S` setting; `backend/app/deps.py` passes it to `FlagService`.
- `backend/app/services/flags.py`: `_Deadline`; the flag read, the MCP call, the SQL fallback lookups, System 2 and the assessment write each run under `asyncio.wait_for` with what is left. `/context`: MCP over budget → SQL packet with `fallback_reason: "deadline: ..."` and a first `gaps` entry. `/explain`: context capped at 40 % of the deadline, System 2 gets the rest minus a reserve, over budget → template with `fallback_reason: "deadline: ..."`. Flag row unreadable in time → `RequestDeadlineExceeded`.
- `backend/app/main.py`: `RequestDeadlineExceeded` → 504 `deadline_exceeded`.
- `docker-compose.yml`: `REQUEST_DEADLINE_S: ${REQUEST_DEADLINE_S:-45}`; `.env.example`, `docs/RUNNING.md`, `backend/README.md` document it.
- `backend/tests/test_fallbacks.py`: hung MCP (60 s per-call timeout, 1 s deadline) → SQL packet in < 2 s; hung MCP + hung System 2 → template in < 2 s; hung flag read → 504 in < 2 s; env parsing.

**M5: non-destructive seed**
- `db/setup.py`: every seed write is insert-if-missing (`ON CONFLICT DO NOTHING`); the demo baseline (events + flags) loads only on a database's first seed (marker: a finished `seed` job in `app.job_runs` that counted flags), so a later `seed` never touches live, acknowledged or reset-away flags/events. New `seed --force-reseed` = the old destructive upserts. Counts now report rows actually written (`flags_written`, `demo_baseline`).
- `docker-compose.yml`: db-init comment (never `--force-reseed`); its command is unchanged (`db/job.sh seed`), as is `db/job.sh`.
- `db/README.md`, `docs/RUNNING.md`: seed semantics and the manual `--force-reseed` command.
- `backend/tests/test_integration.py`: setup/teardown use `seed --force-reseed` (it needs the 58-flag baseline).
- `tests/test_seed_nondestructive.py` (new) + `make test-db`: on a throwaway database in the compose Postgres: first seed loads 58 flags/500 events; after live edits, an ack and a live-only flag, `seed` leaves every flag byte-identical; after a demo reset, `seed` and `seed --no-events` refill nothing; `--force-reseed` restores the baseline; db-init/job.sh never pass `--force-reseed`. Mutation check: forcing the old upserts fails it.
- Live stack: `make up` (db-init re-ran) left all 59 flags and 500 events byte-identical (md5 of every flag row before/after); db-init logged `demo_baseline: skipped`.

**M10: template explanations are not final and not indexed**
- `docs/backend-services-contract.md` "Stored explanations"; `docs/system2-rag-contract.md` §4 excludes templates from `explanation` docs.
- `backend/app/services/flags.py`: templates are stored with `state='TEMPLATE'` (System 2 answers `DONE`). `/explain` returns a cached template only while `SYSTEM2_URL` is unset; when System 2 is configured it retries (also for pre-fix `DONE`/`model='template'` rows). Only `DONE` System 2 answers are indexed.
- `amd/embed/ingest.py`: `build_explanations` requires `state='DONE'` and `model <> 'template'`; the incident corpus also no longer quotes a template as "System 2 assessment".
- `backend/tests/test_fallbacks.py`: template stored as `TEMPLATE`, not indexed, retried without `refresh` once System 2 is back (then `DONE`, indexed, final); legacy `DONE`+template row retried.
- `scripts/e2e.py` A3: stored state is `TEMPLATE`; `ingest.build_explanations` on the live DB builds no doc from a template.

**M7: MCP `.env.example`**
- `amd/mcp/.env.example`: `MCP_HOST` removed (commented, with why), so `--env-file` no longer overrides the image's `0.0.0.0`.
- Verified: `docker run -p 127.0.0.1:18090:8090 --env-file amd/mcp/.env.example spot-mcp:compose` → `/healthz` 200 on the published port and `POST /mcp` with `Host: mcp:8090` → 200; the old value (`-e MCP_HOST=127.0.0.1`) → connection reset (000).

### Results after the fixes
| Suite | Result |
|---|---|
| backend unit (`SKIP_INTEGRATION=1`) | 113 passed, 3 skipped |
| backend all, incl. 3 integration tests (throwaway DB `spot_itest_fixer` on the compose Postgres, dropped after) | 116 passed |
| `tests/test_policy_consistency.py` | 25 passed |
| `tests/test_seed_nondestructive.py` (`make test-db`) | 2 passed |
| mcp unit / with `DATABASE_URL` + `EMBED_URL` | 33 passed, 4 skipped / 36 passed, 1 skipped |
| system1 service (real Laya, CPU) | 20 passed |
| `make smoke` (RAG + roles) | 3 queries OK, 9/9 role checks OK |
| `make e2e` (rebuilt backend, db-init, mcp images; both TRIAGE_MODEs) | **78 checks, 0 failed** (70 before + 4 A0 auth + 2×2 A3 M10) |

With M1, the e2e table now reads: E00005 (rules P4, Laya log P2) → P3 in both modes (was P2); serial E00131 and E00003 (not escalated) → P3 (were P1).

### Noticed, not fixed
- `POST /api/v1/system1/predict` is not behind `ADMIN_TOKEN` and can hold Laya (H2); ack/explain are open by design.
- The dashboard (`web/`) must send `X-Admin-Token` for replay/reset and for `/ops/model-calls` (the latency panel), which is now admin-only.
- A deadline-cancelled MCP/System 2 call neither trips its breaker nor writes a failed `app.model_calls` row; the MCP server's own `HttpEmbedder` still has no breaker (the rest of audit M4's fix).
- One pre-fix `assessments` row (`state='DONE', model='template'`) remains in the local DB. The backend and ingest now treat it as a template, but `amd/mcp/spot_mcp/service.py:250` still shows any `DONE` row as a past explanation. A one-off `UPDATE assessments SET state='TEMPLATE' WHERE model='template'` would clear it.
- `make test-backend-integration` still points at the compose `spot` DB, so it now runs `seed --force-reseed` there (destructive to a live demo); point `INTEGRATION_DATABASE_URL` at a throwaway DB.
- After `db/setup.py reset --yes` (which keeps `app.job_runs`), plain `seed` skips the baseline; use `seed --force-reseed`.
