-- target: both
-- Group roles (NOLOGIN) and their grants. Runs on the main DB and, if separate, the logs DB.
-- Guarded: if this role may not CREATE ROLE (some managed setups), it warns instead of failing.
-- Neon: the project owner (e.g. neondb_owner) can create roles in SQL. Alternative: create the roles in the
-- Neon console (Roles page), then re-run `python db/setup.py migrate` to apply the grants. Login users:
--   CREATE ROLE mcp_user LOGIN PASSWORD '...' IN ROLE spot_mcp_reader;   (or create in the console + GRANT)
--
--   spot_mcp_reader : SELECT on public.* (data + documents + search functions); INSERT on app.* only;
--                     SELECT on raw.spot_event_log + raw.mission_event_log + raw.get_mission_event_log() (for the
--                     MCP get_raw_event_log tool). Also SELECT on the call_id column so
--                     `INSERT ... RETURNING call_id` works.
--   spot_app        : read/write public.*; SELECT + INSERT on raw.* (append-only: no UPDATE/DELETE);
--                     SELECT + INSERT on app.*, plus UPDATE on app.job_runs (to close a run).

DO $roles$
DECLARE r text;
BEGIN
  FOREACH r IN ARRAY ARRAY['spot_mcp_reader', 'spot_app'] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      BEGIN
        EXECUTE format('CREATE ROLE %I NOLOGIN', r);
      EXCEPTION WHEN insufficient_privilege THEN
        RAISE WARNING 'cannot create role % here (%); create it in the Neon console, then re-run migrate', r, SQLERRM;
      END;
    END IF;
  END LOOP;
END
$roles$;

DO $grants$
DECLARE
  has_reader boolean := EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'spot_mcp_reader');
  has_app    boolean := EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'spot_app');
  has_main   boolean := to_regclass('public.documents') IS NOT NULL;
  has_raw    boolean := EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'raw');
  has_logs   boolean := EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'app');
BEGIN
  IF has_main THEN
    IF has_reader THEN
      GRANT USAGE ON SCHEMA public TO spot_mcp_reader;
      GRANT SELECT ON ALL TABLES IN SCHEMA public TO spot_mcp_reader;
      GRANT EXECUTE ON FUNCTION match_documents(vector, text[], text, text, text, int, real),
        match_documents_hybrid(vector, text, text[], text, text, text, int, int) TO spot_mcp_reader;
      ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO spot_mcp_reader;
    END IF;
    IF has_app THEN
      GRANT USAGE ON SCHEMA public TO spot_app;
      GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO spot_app;
      GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO spot_app;
      GRANT EXECUTE ON FUNCTION match_documents(vector, text[], text, text, text, int, real),
        match_documents_hybrid(vector, text, text[], text, text, text, int, int) TO spot_app;
      ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO spot_app;
      ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO spot_app;
    END IF;
  END IF;

  IF has_logs THEN
    IF has_reader THEN
      GRANT USAGE ON SCHEMA app TO spot_mcp_reader;
      GRANT INSERT ON ALL TABLES IN SCHEMA app TO spot_mcp_reader;
      GRANT USAGE ON ALL SEQUENCES IN SCHEMA app TO spot_mcp_reader;
      GRANT SELECT (call_id) ON app.model_calls, app.mcp_tool_calls TO spot_mcp_reader;
      ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT INSERT ON TABLES TO spot_mcp_reader;
      ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT USAGE ON SEQUENCES TO spot_mcp_reader;
    END IF;
    IF has_app THEN
      GRANT USAGE ON SCHEMA app TO spot_app;
      GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA app TO spot_app;
      GRANT UPDATE ON app.job_runs TO spot_app;
      GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO spot_app;
      GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA app TO spot_app;
      ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT SELECT, INSERT ON TABLES TO spot_app;
      ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT USAGE, SELECT ON SEQUENCES TO spot_app;
    END IF;
  END IF;

  IF has_raw AND has_reader THEN
    GRANT USAGE ON SCHEMA raw TO spot_mcp_reader;
    GRANT SELECT ON raw.spot_event_log TO spot_mcp_reader;
    IF to_regclass('raw.mission_event_log') IS NOT NULL THEN
      GRANT SELECT ON raw.mission_event_log TO spot_mcp_reader;
    END IF;
    IF to_regprocedure('raw.get_mission_event_log(text, text)') IS NOT NULL THEN
      GRANT EXECUTE ON FUNCTION raw.get_mission_event_log(text, text) TO spot_mcp_reader;
    END IF;
  END IF;

  IF has_raw AND has_app THEN
    GRANT USAGE ON SCHEMA raw TO spot_app;
    GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA raw TO spot_app;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA raw TO spot_app;
    GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA raw TO spot_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT, INSERT ON TABLES TO spot_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT USAGE, SELECT ON SEQUENCES TO spot_app;
  END IF;
EXCEPTION WHEN insufficient_privilege THEN
  RAISE WARNING 'could not apply role grants (%); apply them as the database owner', SQLERRM;
END
$grants$;
