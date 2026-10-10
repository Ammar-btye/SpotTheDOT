-- target: logs
-- DESTRUCTIVE. Drops the raw.* and app.* schemas (verbatim SPOT data and application logs). Run only via
-- `python db/setup.py reset --yes --include-logs`; plain `reset --yes` keeps the logs.
DROP SCHEMA IF EXISTS raw CASCADE;
DROP SCHEMA IF EXISTS app CASCADE;
