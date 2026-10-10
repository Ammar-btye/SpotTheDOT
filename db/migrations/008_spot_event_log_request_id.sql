-- target: logs
-- Contract §6 (added 2026-10-10 by the backend agent): raw.spot_event_log.request_id ties a verbatim event to its
-- app.* rows (model_calls, request_log, mcp_tool_calls). Additive and idempotent. The backend writes it as soon as
-- the column exists (backend/app/db/queries.py append_raw). Grants: 007's table-level grants already cover new
-- columns (spot_app: SELECT, INSERT; spot_mcp_reader: SELECT), and nothing UPDATEs raw.*.
ALTER TABLE raw.spot_event_log ADD COLUMN IF NOT EXISTS request_id text;
CREATE INDEX IF NOT EXISTS spot_event_log_request ON raw.spot_event_log (request_id);
