-- target: main
-- The RAG store (contract §2). Placeholders are substituted by db/setup.py from the environment:
--   {{EMBED_DIM}}  vector width (EMBED_DIM, default 1024)
--   {{VEC_TYPE}}   'vector', or 'halfvec' when EMBED_DIM > 2000 (pgvector indexes cap 'vector' at 2,000 dims)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
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
  embedding    {{VEC_TYPE}}({{EMBED_DIM}}),   -- dimension substituted at migration time
  embed_model  text,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- Vector search is EXACT by default (no ANN index): a few thousand rows scan in milliseconds and filtered
-- queries never drop results. Optional HNSW: db/migrations/optional/hnsw.sql (`python db/setup.py migrate --hnsw`).
CREATE INDEX IF NOT EXISTS documents_tsv_gin      ON documents USING gin (content_tsv);
CREATE INDEX IF NOT EXISTS documents_kind_asset   ON documents (kind, asset_id);
CREATE INDEX IF NOT EXISTS documents_kind_loc     ON documents (kind, location_id);
CREATE INDEX IF NOT EXISTS documents_kind_mission ON documents (kind, mission_id);
CREATE INDEX IF NOT EXISTS documents_embed_model  ON documents (embed_model);
