# System 2 RAG contract: Neon pgvector + embedding service + MCP server

Two parts are built in parallel and must meet here. **Change this file first, then the code.**

| Part | Folder | Owner |
|---|---|---|
| Neon schema, pgvector, search functions, embedding service, ingestion, `raw` + `app` log schemas | `db/` and `amd/embed/` | pgvector agent |
| MCP server (tools the System 2 model calls) | `amd/mcp/` | MCP agent |

## 1. Embedding API (OpenAI-compatible)
Every component talks to the embedding model through the same HTTP contract, so the model and the server can be
swapped by changing configuration only. `llama-server --embedding`, Hugging Face TEI and Infinity all expose this API.

```http
POST {EMBED_URL}/v1/embeddings
{"model": "<EMBED_MODEL>", "input": ["text 1", "text 2"]}
→ {"data": [{"index": 0, "embedding": [..floats..]}, ...], "model": "...", "usage": {...}}
```

| Env var | Meaning | Default |
|---|---|---|
| `EMBED_URL` | base URL of the embedding service | `http://localhost:8081` |
| `EMBED_MODEL` | model id sent in requests | `Qwen/Qwen3-Embedding-0.6B` (Apache-2.0; fallback `Snowflake/snowflake-arctic-embed-l-v2.0`, also 1024-d). See `research/tech-embedding-model-amd-2026-10-10.md` |
| `EMBED_DIM` | vector dimension; must equal the `documents.embedding` column | `1024` |
| `EMBED_QUERY_PREFIX` | text prepended to search queries | Qwen3: `Instruct: Given an operator question about a SPOT robot inspection, retrieve relevant inspection events, anomaly notes, operator notes, and Spot manual passages\nQuery:` (a real newline). Arctic fallback: `query: ` |
| `EMBED_DOC_PREFIX` | text prepended to documents at ingestion | empty (both models take no document prefix) |
| `DATABASE_URL` | Neon (or local) Postgres connection string | none |
| `LOGS_DATABASE_URL` | where `raw.*` and `app.*` live | `DATABASE_URL` |

Clients normalize nothing themselves: the search functions use cosine distance.

## 2. Tables
- **Core relational tables** are the draft at `git show 19dff30:web/db/schema.sql`: `locations, assets, missions,
  actions, readings, anomalies, events, flags, assessments, acknowledgements, risk_scores, mission_kpis,
  anomaly_briefs, insights`. Keep those table and column names; adding columns or tables is fine.
  Added by the pgvector agent: `flags.triage_event_id` (unique, System 1 event id `act-A0001` / `mis-M001`),
  `flags.priority` (P1–P4), `flags.category`. Seeded flags' `reasons[].rule` names a `policy:<rule>` doc.
  Databricks was dropped, so `risk_scores` / `mission_kpis` / `insights` are filled by our own jobs (Laya, SQL).
- **Added: `system1_predictions`**: Laya's answers per event, one row per (event, question).
  ```sql
  CREATE TABLE system1_predictions (
    prediction_id bigserial PRIMARY KEY,
    event_kind  text NOT NULL,          -- pre_action | action | mission
    action_id   text, mission_id text,
    question    text NOT NULL,          -- will_fail, failure_mode, anomaly_expected, escalate, priority, category, reading_trust, mission_misleading
    answer      text NOT NULL,          -- the option key, e.g. 'A', 'P2', 'navigation'
    probs       jsonb NOT NULL,         -- {"A": 0.71, "B": 0.29}
    confidence  real,
    model       text NOT NULL,          -- e.g. 'convaiinnovations/laya' or a fine-tuned checkpoint name
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (event_kind, action_id, mission_id, question, model)
  );
  ```
- **Added: `documents`** (the RAG store):
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  CREATE TABLE documents (
    doc_id       text PRIMARY KEY,        -- stable citation id: 'event:act-A0123', 'incident:AN012', 'manual:p42-3', 'policy:battery_low'
    kind         text NOT NULL CHECK (kind IN ('event','incident','operator_note','explanation','manual','policy')),
    source_id    text,                    -- id of the source row (action_id, anomaly_id, flag_id, ack_id, page...)
    mission_id   text, action_id text, asset_id text, location_id text,
    action_type  text, status text, anomaly_type text, severity text,
    ts           timestamp,
    title        text,
    content      text NOT NULL,           -- exactly the text that was embedded (without EMBED_DOC_PREFIX)
    metadata     jsonb NOT NULL DEFAULT '{}',
    content_tsv  tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(title,'') || ' ' || content)) STORED,
    embedding    vector(EMBED_DIM),       -- dimension substituted at migration time
    embed_model  text,
    created_at   timestamptz NOT NULL DEFAULT now()
  );
  -- indexes: GIN (content_tsv), btree (kind, asset_id), (kind, location_id), (kind, mission_id), (embed_model)
  -- vector search is EXACT by default (a few thousand rows: exact is fast and never drops filtered results).
  -- Optional HNSW (embedding vector_cosine_ops) only if EXPLAIN shows it's slow; then the match functions must
  -- SET LOCAL hnsw.iterative_scan = strict_order so metadata filters still return k rows (pgvector >= 0.8; Neon ships 0.8.x).
  ```

## 3. Search functions (pgvector agent implements; MCP server calls)
```sql
-- Vector search with optional metadata filters. similarity = 1 - cosine distance.
match_documents(query_embedding vector, kinds text[] DEFAULT NULL, filter_asset text DEFAULT NULL,
                filter_location text DEFAULT NULL, filter_mission text DEFAULT NULL,
                match_count int DEFAULT 5, min_similarity real DEFAULT 0.0)
  RETURNS TABLE (doc_id text, kind text, title text, content text, metadata jsonb, asset_id text,
                 location_id text, mission_id text, action_id text, ts timestamp, similarity real)

-- Hybrid: vector + Postgres full-text (catches exact IDs like 'HX-204'), merged by reciprocal rank fusion.
match_documents_hybrid(query_embedding vector, query_text text, kinds text[] DEFAULT NULL,
                       filter_asset text DEFAULT NULL, filter_location text DEFAULT NULL,
                       filter_mission text DEFAULT NULL, match_count int DEFAULT 5, rrf_k int DEFAULT 60)
  RETURNS TABLE (doc_id text, kind text, title text, content text, metadata jsonb, asset_id text,
                 location_id text, mission_id text, action_id text, ts timestamp, score real,
                 similarity real, text_match boolean)   -- ADDED 2026-10-10 by MCP agent, see note
```
NULL filters mean "no filter". Results are ordered best first.

**Hybrid trailing columns (requested by the MCP agent, additive).** RRF `score` is rank-based, so it can't tell a weak
match from a strong one. Please append `similarity real` (1 - cosine distance for that row, the same value
`match_documents` would return) and `text_match boolean` (true if the row matched the full-text query). The MCP server
keeps a hybrid row only if `similarity >= MCP_MIN_SIMILARITY` or `text_match` is true. Until these columns exist, the MCP
server falls back to a second `match_documents` call plus an exact-ID check, so nothing breaks either way.
**Implemented (pgvector agent, 2026-10-10):** `text_match` is true when the row contains **every** query term
(`plainto_tsquery('english', query_text)`), so `HX-204` (indexed as `hx` + `-204`) is true only on HX-204 rows, not on
other heat exchangers. The lexical side of the RRF still ORs the terms (all-terms rows rank first). `similarity` is
NULL only if the row has no embedding. Vector search is exact (no ANN index) unless `migrate --hnsw` is run.

## 4. Corpora (`documents.kind`)
| kind | Source | doc_id pattern |
|---|---|---|
| `event` | every kit action and mission event, as prose (reuse `amd/system1/triage/render.py` `render_prose`) | `event:<event_id>` |
| `incident` | anomalies plus System 1 flags with outcome | `incident:<anomaly_id>` / `incident:flag-<flag_id>` |
| `operator_note` | `acknowledgements` rows with notes | `note:<ack_id>` |
| `explanation` | System 2 outputs (`assessments` with `state = 'DONE'`; template fallbacks, `state = 'TEMPLATE'` / `model = 'template'`, are excluded: audit M10) | `explanation:<assessment_id>` |
| `manual` | chunks of the Spot User Guide PDFs in `SPOTDATA/SPOT_KnightHacks_Challenge_Kit Part Two/` | `manual:p<page>-<chunk>` |
| `policy` | one doc per triage rule in `amd/system1/triage/policy.py` | `policy:<rule_name>` |

## 5. MCP tools (MCP agent implements; see the tool list agreed in chat)
Tier 1 `get_flag_context`. RAG tools: `search_similar_incidents`, `search_asset_history`, `search_spot_manual`,
`search_operator_notes`, `search_past_explanations`, `search_policy`. SQL tools: `get_flag`,
`get_system1_forecast`, `get_action`, `get_mission_summary`, `get_reliability_stats`, `get_battery_risk`,
`list_allowed_actions`, `get_raw_event_log` (verbatim `raw.spot_event_log` rows, id `log:<log_id>`). All read-only. No raw SQL from the model. Every returned row carries its `doc_id`
or a short stable id the model can cite.

## 6. Logs and raw SPOT data (added 2026-10-10)
Same Neon project and database, two extra Postgres schemas. `LOGS_DATABASE_URL` (defaults to `DATABASE_URL`) lets
logs move to a separate Neon database later without code changes. The existing tables stay in `public`.

**Roles:** the MCP server reads `public` (data + `documents`) read-only and may INSERT into `app.*` only.
It also needs `USAGE ON SCHEMA raw` + `SELECT ON raw.spot_event_log` for the `get_raw_event_log` tool (requested by the
MCP agent 2026-10-10; read-only, so still append-only for everyone else).
Implemented in `db/migrations/007_roles.sql` as NOLOGIN group roles `spot_mcp_reader` (also SELECT on
`raw.mission_event_log` / EXECUTE `raw.get_mission_event_log(mission_id, source)`, and SELECT on `call_id` of
`app.model_calls` / `app.mcp_tool_calls` so `INSERT ... RETURNING call_id` works) and `spot_app`. Helpers:
`app.get_model_call_stats(interval)` and `app.get_mcp_tool_stats(interval)` (p50/p95 latency, tokens/s).
Nothing ever UPDATEs or DELETEs `raw.*` (append-only).

### `raw`: SPOT data exactly as received (append-only, for audit, replay and re-derivation)
```sql
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE raw.spot_event_log (          -- every robot/replay event, verbatim
  log_id      bigserial PRIMARY KEY,
  source      text NOT NULL,               -- 'replay.ndjson' | 'live' | ...
  event_id    text, mission_id text, event_type text,
  event_ts    timestamp,                   -- time from the robot
  payload     jsonb NOT NULL,              -- the event exactly as received
  received_at timestamptz NOT NULL DEFAULT now(),
  sha256      text NOT NULL,               -- of the raw payload; UNIQUE (source, sha256) makes re-imports idempotent
  request_id  text,                        -- ADDED 2026-10-10 (backend agent): ties the event to app.* rows
  UNIQUE (source, sha256)
);
-- migration for existing DBs: ALTER TABLE raw.spot_event_log ADD COLUMN IF NOT EXISTS request_id text;
--                             CREATE INDEX IF NOT EXISTS spot_event_log_request ON raw.spot_event_log (request_id);
CREATE TABLE raw.kit_files (               -- provenance of every imported kit file
  file_id bigserial PRIMARY KEY, file_name text NOT NULL, sha256 text NOT NULL, row_count int,
  imported_at timestamptz NOT NULL DEFAULT now(), UNIQUE (file_name, sha256));
CREATE TABLE raw.kit_rows (                -- every CSV row verbatim, before typing/cleaning
  file_id bigint REFERENCES raw.kit_files, row_num int, data jsonb NOT NULL, PRIMARY KEY (file_id, row_num));
CREATE TABLE raw.inspection_media (        -- metadata + pointer for images/audio; blobs live in object storage or the repo
  media_id text PRIMARY KEY, action_id text, mission_id text, media_type text, uri text NOT NULL,
  sha256 text, bytes int, captured_at timestamp, metadata jsonb NOT NULL DEFAULT '{}');
-- indexes: (mission_id, event_ts), (event_type, event_ts), GIN (payload)
```

### `app`: application logs (append-only)
```sql
CREATE SCHEMA IF NOT EXISTS app;
CREATE TABLE app.model_calls (             -- every System 1 / System 2 / embedding call (the AMD latency evidence)
  call_id bigserial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(), request_id text,
  system text NOT NULL CHECK (system IN ('system1','system2','embed')), model text, endpoint text,
  flag_id bigint, action_id text, input_tokens int, output_tokens int, latency_ms int, tokens_per_sec real,
  device text, ok boolean NOT NULL, error text, metadata jsonb NOT NULL DEFAULT '{}');
CREATE TABLE app.mcp_tool_calls (          -- audit of every MCP tool call System 2 makes
  call_id bigserial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(), request_id text, flag_id bigint,
  tool text NOT NULL, args jsonb NOT NULL, result_count int, result_bytes int, top_similarity real,
  latency_ms int, ok boolean NOT NULL, error text);
CREATE TABLE app.request_log (             -- web/API requests
  req_id bigserial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(), request_id text, service text,
  route text, method text, status int, latency_ms int, error text);
CREATE TABLE app.job_runs (                -- seed / ingest / replay / fine-tune sync jobs
  run_id bigserial PRIMARY KEY, job text NOT NULL, started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz, status text NOT NULL DEFAULT 'running', counts jsonb NOT NULL DEFAULT '{}',
  error text, metadata jsonb NOT NULL DEFAULT '{}');
-- indexes: ts DESC on each; (system, ts) on model_calls; (tool, ts) on mcp_tool_calls; (request_id) everywhere
```
`request_id` ties one flag's whole journey together across tables.
