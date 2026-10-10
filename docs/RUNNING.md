# Running the stack

There is ONE `docker-compose.yml`, at the repo root, for the whole project. Modes are profiles inside it; there
are no per-service or per-environment compose files. Every new or changed container must update that file (its
header table too) and this page. Ports and contracts are in `docs/backend-services-contract.md` and
`docs/system2-rag-contract.md`. The integration history is in `docs/integration-log-2026-10-10.md`.

| Service | Port | Profiles | Image / folder | Notes |
|---|---|---|---|---|
| `db` | 5433 (host: `DB_PORT`) | local, hybrid | `pgvector/pgvector:pg17` | Local stand-in for Neon. Named volume `pgdata`. |
| `db-init` | n/a | local, hybrid, neon | `db/Dockerfile` | One-shot job: migrate, create login users, seed, ingest (embeds the RAG corpus), status. Idempotent and non-destructive: `seed` only inserts missing rows and loads the demo baseline (events + flags) on a database's first seed, so `make up` never overwrites live or acknowledged flags or refills a reset demo (audit M5). |
| `embed` | 8081 | local, models | `amd/embed/` | Qwen3-Embedding-0.6B. `TORCH_VARIANT` build arg. HF cache volume `hf-cache`. `EMBED_BATCH=8` (32 OOM-killed it). |
| `system1` | 8082 | local, models | `amd/system1/service/` | Laya. `TORCH_VARIANT` build arg. Same `hf-cache` volume. Fine-tuned checkpoints are mounted at `/models/checkpoints`. |
| `mcp` | 8090 | local, hybrid, neon | `amd/mcp/` | Logs in as `spot_mcp_user` (in `spot_mcp_reader`: read-only, plus INSERT on `app.*`). |
| `backend` | 8000 | local, hybrid, neon | `backend/` | Logs in as `spot_app_user` (in `spot_app`). API docs at http://localhost:8000/docs. `ADMIN_TOKEN` (header `X-Admin-Token`) guards `/ops/*`, `/replay/*` and `POST /events*`; CORS allows `CORS_ORIGINS` only (default `http://localhost:3000`); `REQUEST_DEADLINE_S` (45) bounds `/flags/{id}/context` and `/explain`. |
| `system2` | 8083 | local, hybrid, neon, system2 | `amd/system2/` | Non-root authenticated packet-grounded stub (`model: stub`), healthcheck inherited from image. Backend supplies context; no MCP/database access. |

Published ports bind to `127.0.0.1` by default (`BIND_ADDR`). Inside the network the services use service names
(`http://system1:8082`).

**Adding or changing a container:**
1. Add a service block under the right section (data / models / application).
2. Use `<<: *service` for the restart policy and `host.docker.internal`.
3. Use `<<: *embed-env` if it calls the embedder.
4. Every setting is `${VAR:-local default}`.
5. List it in the header table of `docker-compose.yml` and here.
6. Use `required: false` for any dependency that some profile doesn't start.

## Setup
```bash
cp .env.example .env                # pick COMPOSE_PROFILES; dev passwords are fine locally
sed -i.bak "s/^ADMIN_TOKEN=.*/ADMIN_TOKEN=$(openssl rand -hex 24)/" .env   # required for /ops, /replay, POST /events
unset DATABASE_URL EMBED_URL SYSTEM1_URL   # your shell environment overrides .env in compose
```
**Admin endpoints (audit H3).** `/api/v1/ops/*`, `/api/v1/replay/*` and `POST /api/v1/events` / `/events/batch`
need the header `X-Admin-Token: $ADMIN_TOKEN`. Without `ADMIN_TOKEN` in `.env` they answer 503 (closed, not open);
a missing or wrong header gets 401. `make e2e` reads the token from `.env`. Set `CORS_ORIGINS` to the dashboard's
origin (default `http://localhost:3000`); the dashboard sends `X-Admin-Token` only from the presenter's console.
If `db/local_pgvector.sh` already holds port 5433, set `DB_PORT=5434` in `.env`.

## Mode 1: `local` (default): everything in Docker on CPU
```bash
make up        # = docker compose up -d --build --wait
make e2e       # end-to-end proof, both TRIAGE_MODEs
make test      # unit suites + the cross-service policy drift guard
make down      # or `make wipe` to drop the database volume too
```
- The first start downloads ~1.2 GB (embedding model) and ~842 MB (Laya) into the `hf-cache` volume.
- `db-init` embeds ~500 documents on CPU, which takes a few minutes.
- This mode tests the wiring. It is not for the demo: Docker Desktop on a Mac has no GPU.
- Measured CPU latencies, 2026-10-10:

  | Step | Time |
  |---|---|
  | Laya, one action event | 2.3-3.0 s |
  | Laya, one mission event | 1.8-1.9 s |
  | Live forecast (5 actions) | ~13 s |
  | Query embedding (cold) | ~0.9 s |
  | Full ingest | ~8 min |

- Timeouts are sized for CPU:
  - `SYSTEM1_INGEST_TIMEOUT_S=10`: per replay or ingest event; it fails fast to a rules-only verdict.
  - `SYSTEM1_TIMEOUT_S=30`: forecast and batch predict.
  - `MCP_TIMEOUT_S=60` and `SEARCH_EMBED_TIMEOUT_S=8`.
  - Each breaker's cooldown is max(`BREAKER_COOLDOWN_S`, that service's timeout).
  - `REQUEST_DEADLINE_S=45`: `/flags/{id}/context` and `/explain` return their fallback (SQL packet / template,
    marked `fallback_reason: "deadline: ..."`) when it runs out, so a hung MCP or System 2 never spins the UI.
- **Laya serves one request at a time.** While a forecast holds it, replay events skip Laya: they get a
  rules-only verdict marked `busy`. A live forecast asks Laya for at most 5 actions.
- **GPU expectation:** on the AMD GPU a 64-event batch is one forward pass (well under a second), so none of
  this throttling shows. Run the demo in `hybrid` mode, with the contract-default timeouts.
- Memory: give Docker Desktop at least 8 GB. `LAYA_MAX_BATCH=16` keeps System 1 under ~3.5 GB on large batches.
- Fine-tuned Laya: put the run under `amd/system1/checkpoints/` (mounted read-only at `/models/checkpoints`), set
  `LAYA_CHECKPOINT=/models/checkpoints/<run>/best`, then run `docker compose up -d system1`.
  Check with `curl localhost:8082/v1/model`: it should show `fine_tuned: true`.

## Mode 2: `hybrid`: models native on the AMD GPU box
The AMD Radeon Cloud Jupyter VMs have no root and can't run Docker. Run `system1` and `embed` there natively (see
`amd/system1/service/README.md` "Native venv" and `amd/embed/README.md` "Run on the AMD VM"). Run `db`, `db-init`,
`mcp` and `backend` here in Docker.
```bash
# 1. On the AMD VM: python -m service (port 8082) and python amd/embed/server.py (port 8081)
# 2. Here, tunnel both ports:
ssh -N -L 18082:localhost:8082 -L 18081:localhost:8081 <amd-vm> &
# 3. In .env:
COMPOSE_PROFILES=hybrid
SYSTEM1_URL=http://host.docker.internal:18082
EMBED_URL=http://host.docker.internal:18081
SYSTEM1_TIMEOUT_S=5  SYSTEM1_INGEST_TIMEOUT_S=5  MCP_TIMEOUT_S=15  SEARCH_EMBED_TIMEOUT_S=4   # GPU: contract defaults
# 4.
make up && make e2e
```
- `db-init` ingests through the tunnelled embedder. The corpus and the queries must use the same embedding backend.
  If the AMD box's embedder differs from what was ingested before, run `DB_INGEST_ARGS=--force make up`.
- System 1's own `app.model_calls` logging needs a DB URL that the VM can reach. Neon works for that. The local
  `db` is not reachable from the VM, so with it the backend's client-side `system1` rows are the only ones.

## Mode 3: `neon`: Neon instead of the `db` service
```bash
# .env
COMPOSE_PROFILES=neon                 # models from SYSTEM1_URL/EMBED_URL (the AMD box), or:
# COMPOSE_PROFILES=neon,models        # plus embed + system1 on CPU in Docker
DATABASE_URL=postgresql://neondb_owner:<pw>@ep-xxxx-pooler.<region>.aws.neon.tech/neondb?sslmode=require
BACKEND_DATABASE_URL=postgresql://spot_app_user:<pw>@ep-xxxx-pooler.<region>.aws.neon.tech/neondb?sslmode=require
MCP_DATABASE_URL=postgresql://spot_mcp_user:<pw>@ep-xxxx-pooler.<region>.aws.neon.tech/neondb?sslmode=require
SPOT_APP_PASSWORD=<pw>  SPOT_MCP_PASSWORD=<pw>
make up
E2E_DATABASE_URL=$DATABASE_URL backend/.venv/bin/python scripts/e2e.py
```
`db-init` runs as the owner. It migrates, then `scripts/db_login_roles.py` creates `spot_app_user` and
`spot_mcp_user` with those passwords. If Neon refuses `CREATE ROLE`, create the users in the Neon console instead,
then re-run. Make a Neon branch before any `reset`.

## Useful commands
```bash
docker compose run --rm --no-deps --entrypoint db/job.sh db-init status        # row counts
make smoke                                                                     # 3 RAG queries + role checks
docker compose up -d --force-recreate backend                                  # after editing .env (e.g. TRIAGE_MODE)
curl -s localhost:8000/health | jq                                             # every dependency's status
ADMIN_TOKEN=$(sed -n 's/^ADMIN_TOKEN=//p' .env)
curl -s -XPOST localhost:8000/api/v1/replay/start -H "X-Admin-Token: $ADMIN_TOKEN" \
     -H 'content-type: application/json' -d '{"speed":600,"limit":20}'
docker compose run --rm --no-deps --entrypoint db/job.sh db-init seed --force-reseed   # DESTRUCTIVE: restore the
                                                                               # seeded events/flags (overwrites)
```

## System 2 stub on 8083

Set `SYSTEM2_API_KEY` in `.env` to a printable ASCII secret of at least 16 characters, without surrounding whitespace. The same secret is passed to backend and System 2; it is never baked into the image. Native launch accepts `AMD_API_KEY` as a backward-compatible alias; different values in both variables fail before binding.

```bash
docker compose --profile system2 up --build -d system2
docker compose --profile local config --quiet
curl http://127.0.0.1:8083/health
# Native (export SYSTEM2_API_KEY first):
uv run --no-project --with-requirements amd/system2/requirements.txt python amd/system2/scripts/serve.py
# Remote native service via tunnel:
ssh -L 8083:127.0.0.1:8083 <box>
```

`/health` is public; `POST /v1/assess` requires `X-API-Key` and accepts the request in `amd/system2/fixtures/backend/equipment.json` under `request`. Missing authentication returns 401. Native defaults are `127.0.0.1:8083`; `SYSTEM2_HOST`/`SYSTEM2_PORT` and `--host`/`--port` override them. Docker binds all container interfaces, while published ports bind `${BIND_ADDR:-127.0.0.1}`.

Local, hybrid and neon include the stub. Backend defaults `SYSTEM2_URL` to `http://system2:8083`; an explicit remote URL overrides it (for a host SSH tunnel use `http://host.docker.internal:18083`). Backend retains its template fallback when the service is unavailable or rejects the key. System 2 receives the prepared MCP packet from backend and does not retrieve packets itself. `model: stub` is deterministic packet evidence, not live LLM inference.
