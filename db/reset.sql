-- target: main
-- DESTRUCTIVE. Drops every table and function the migrations create in public. Run only via
-- `python db/setup.py reset --yes` (which then re-runs the migrations). Keeps the vector extension and the roles.
DROP FUNCTION IF EXISTS match_documents(vector, text[], text, text, text, int, real);
DROP FUNCTION IF EXISTS match_documents_hybrid(vector, text, text[], text, text, text, int, int);
DROP TABLE IF EXISTS documents, system1_predictions, acknowledgements, assessments, flags, events,
  risk_scores, mission_kpis, anomaly_briefs, insights,
  anomalies, readings, actions, missions, assets, locations CASCADE;
