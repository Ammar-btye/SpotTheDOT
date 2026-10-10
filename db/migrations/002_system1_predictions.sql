-- target: main
-- Laya's answers per event, one row per (event, question). Contract §2.
CREATE TABLE IF NOT EXISTS system1_predictions (
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
CREATE INDEX IF NOT EXISTS system1_predictions_action_idx  ON system1_predictions (action_id);
CREATE INDEX IF NOT EXISTS system1_predictions_mission_idx ON system1_predictions (mission_id);
