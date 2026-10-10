-- target: logs
-- Retrieval helpers over raw.* and app.* (the AMD judging evidence). Idempotent.

-- A mission's raw event log, in robot order, with a per-mission sequence number.
CREATE OR REPLACE VIEW raw.mission_event_log AS
SELECT row_number() OVER (PARTITION BY l.source, l.mission_id ORDER BY l.event_ts, l.event_id, l.log_id) AS seq,
       l.log_id, l.source, l.mission_id, l.event_id, l.event_type, l.event_ts, l.payload, l.received_at
FROM raw.spot_event_log l;

-- SELECT * FROM raw.get_mission_event_log('M014');           -- all sources
-- SELECT * FROM raw.get_mission_event_log('M014', 'live');   -- one source
CREATE OR REPLACE FUNCTION raw.get_mission_event_log(p_mission_id text, p_source text DEFAULT NULL)
RETURNS TABLE (seq bigint, log_id bigint, source text, event_id text, event_type text, event_ts timestamp,
               payload jsonb, received_at timestamptz)
LANGUAGE sql STABLE
AS $fn$
  SELECT row_number() OVER (ORDER BY l.event_ts, l.event_id, l.log_id), l.log_id, l.source, l.event_id,
         l.event_type, l.event_ts, l.payload, l.received_at
  FROM raw.spot_event_log l
  WHERE l.mission_id = p_mission_id AND (p_source IS NULL OR l.source = p_source)
  ORDER BY l.event_ts, l.event_id, l.log_id;
$fn$;

-- Model-call latency/throughput by system and model over a recent window.
-- SELECT * FROM app.get_model_call_stats();                    -- last 24 h
-- SELECT * FROM app.get_model_call_stats(interval '7 days');
CREATE OR REPLACE FUNCTION app.get_model_call_stats(since interval DEFAULT interval '24 hours')
RETURNS TABLE (system text, model text, device text, calls bigint, errors bigint,
               p50_latency_ms real, p95_latency_ms real, p50_tokens_per_sec real, p95_tokens_per_sec real,
               mean_tokens_per_sec real, total_input_tokens bigint, total_output_tokens bigint,
               first_ts timestamptz, last_ts timestamptz)
LANGUAGE sql STABLE
AS $fn$
  SELECT m.system, m.model, m.device, count(*), count(*) FILTER (WHERE NOT m.ok),
         (percentile_cont(0.5)  WITHIN GROUP (ORDER BY m.latency_ms) FILTER (WHERE m.ok))::real,
         (percentile_cont(0.95) WITHIN GROUP (ORDER BY m.latency_ms) FILTER (WHERE m.ok))::real,
         (percentile_cont(0.5)  WITHIN GROUP (ORDER BY m.tokens_per_sec) FILTER (WHERE m.ok))::real,
         (percentile_cont(0.95) WITHIN GROUP (ORDER BY m.tokens_per_sec) FILTER (WHERE m.ok))::real,
         (avg(m.tokens_per_sec) FILTER (WHERE m.ok))::real,
         coalesce(sum(m.input_tokens), 0)::bigint, coalesce(sum(m.output_tokens), 0)::bigint,
         min(m.ts), max(m.ts)
  FROM app.model_calls m
  WHERE m.ts >= now() - since
  GROUP BY m.system, m.model, m.device
  ORDER BY m.system, m.model, m.device;
$fn$;

-- Same, over the last 24 hours, as a view for dashboards.
CREATE OR REPLACE VIEW app.model_call_stats AS SELECT * FROM app.get_model_call_stats(interval '24 hours');

-- MCP tool-call stats (how System 2 used retrieval).
CREATE OR REPLACE FUNCTION app.get_mcp_tool_stats(since interval DEFAULT interval '24 hours')
RETURNS TABLE (tool text, calls bigint, errors bigint, p50_latency_ms real, p95_latency_ms real,
               mean_result_count real, mean_top_similarity real)
LANGUAGE sql STABLE
AS $fn$
  SELECT t.tool, count(*), count(*) FILTER (WHERE NOT t.ok),
         (percentile_cont(0.5)  WITHIN GROUP (ORDER BY t.latency_ms))::real,
         (percentile_cont(0.95) WITHIN GROUP (ORDER BY t.latency_ms))::real,
         avg(t.result_count)::real, avg(t.top_similarity)::real
  FROM app.mcp_tool_calls t
  WHERE t.ts >= now() - since
  GROUP BY t.tool ORDER BY count(*) DESC;
$fn$;
