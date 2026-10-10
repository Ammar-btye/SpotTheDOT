-- Neon-compatible PostgreSQL. Run once against a new development database.
-- All application objects live in spotlight; no extensions are required.
BEGIN;
CREATE SCHEMA spotlight;
SET LOCAL search_path TO spotlight, public;

CREATE TABLE locations (
    location_id text PRIMARY KEY,
    location_name text NOT NULL,
    zone_type text,
    floor integer,
    x_coord double precision,
    y_coord double precision,
    environment text,
    synthetic boolean NOT NULL DEFAULT false
);

CREATE TABLE assets (
    asset_id text PRIMARY KEY,
    asset_name text NOT NULL,
    asset_type text NOT NULL,
    location_id text REFERENCES locations,
    criticality text CHECK (criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    synthetic boolean NOT NULL DEFAULT false
);

CREATE TABLE missions (
    mission_id text PRIMARY KEY,
    mission_name text NOT NULL,
    scenario text,
    configuration_version text,
    start_time timestamptz NOT NULL,
    end_time timestamptz,
    duration_min numeric CHECK (duration_min >= 0),
    start_battery_pct numeric CHECK (start_battery_pct BETWEEN 0 AND 100),
    end_battery_pct numeric CHECK (end_battery_pct BETWEEN 0 AND 100),
    mission_status text NOT NULL,
    operator_mode text,
    synthetic boolean NOT NULL DEFAULT false,
    CHECK (end_time IS NULL OR end_time >= start_time)
);

CREATE TABLE actions (
    action_id text PRIMARY KEY,
    mission_id text NOT NULL REFERENCES missions,
    sequence integer NOT NULL CHECK (sequence > 0),
    timestamp timestamptz NOT NULL,
    location_id text REFERENCES locations,
    asset_id text REFERENCES assets,
    action_type text NOT NULL,
    battery_pct numeric CHECK (battery_pct BETWEEN 0 AND 100),
    status text NOT NULL,
    failure_type text,
    duration_sec numeric CHECK (duration_sec >= 0),
    scenario text,
    configuration_version text,
    synthetic boolean NOT NULL DEFAULT false,
    UNIQUE (mission_id, sequence),
    UNIQUE (action_id, mission_id)
);

CREATE TABLE sensor_sources (
    source_id text PRIMARY KEY,
    robot_id text,
    source_name text NOT NULL,
    source_type text NOT NULL CHECK (source_type IN ('camera', 'sensor', 'robot_log', 'replay')),
    metadata jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(metadata) = 'object')
);

-- Save the original envelope before cleaning. Rejected input is retained here.
-- An event_id must be globally unique (e.g. robot + run + source + message ID).
CREATE TABLE events (
    event_id text PRIMARY KEY,
    source_id text NOT NULL REFERENCES sensor_sources,
    stream_id text NOT NULL,
    source_event_id text NOT NULL,
    mission_id text REFERENCES missions,
    action_id text,
    location_id text REFERENCES locations,
    asset_id text REFERENCES assets,
    event_type text NOT NULL,
    occurred_at timestamptz,
    received_at timestamptz NOT NULL DEFAULT now(),
    raw_payload jsonb NOT NULL,
    prepared_payload jsonb CHECK (jsonb_typeof(prepared_payload) = 'object'),
    input_status text NOT NULL DEFAULT 'received'
        CHECK (input_status IN ('received', 'accepted', 'rejected', 'needs_review')),
    input_errors jsonb NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(input_errors) = 'array'),
    preprocessing_version text,
    prepared_at timestamptz,
    UNIQUE (source_id, stream_id, source_event_id),
    CHECK (action_id IS NULL OR mission_id IS NOT NULL),
    CHECK (input_status <> 'accepted' OR
           (prepared_payload IS NOT NULL AND occurred_at IS NOT NULL AND prepared_at IS NOT NULL)),
    FOREIGN KEY (action_id, mission_id) REFERENCES actions (action_id, mission_id)
);

CREATE TABLE readings (
    reading_id text PRIMARY KEY,
    source_event_id text REFERENCES events,
    action_id text,
    mission_id text NOT NULL REFERENCES missions,
    asset_id text REFERENCES assets,
    location_id text REFERENCES locations,
    timestamp timestamptz NOT NULL,
    measurement_type text NOT NULL,
    value double precision NOT NULL,
    unit text NOT NULL,
    quality text NOT NULL,
    synthetic boolean NOT NULL DEFAULT false,
    CHECK (value NOT IN ('NaN'::float8, 'Infinity'::float8, '-Infinity'::float8)),
    FOREIGN KEY (action_id, mission_id) REFERENCES actions (action_id, mission_id)
);

-- Camera bytes belong in object storage, not in PostgreSQL rows.
CREATE TABLE media (
    media_id text PRIMARY KEY,
    event_id text NOT NULL REFERENCES events,
    storage_uri text NOT NULL,
    content_type text NOT NULL,
    sha256 text CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    captured_at timestamptz,
    metadata jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(metadata) = 'object')
);

CREATE TABLE anomalies (
    anomaly_id text PRIMARY KEY,
    source_event_id text REFERENCES events,
    action_id text,
    mission_id text NOT NULL REFERENCES missions,
    location_id text REFERENCES locations,
    asset_id text REFERENCES assets,
    timestamp timestamptz NOT NULL,
    anomaly_type text NOT NULL,
    severity text NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    operator_review_required boolean NOT NULL DEFAULT false,
    description text NOT NULL,
    synthetic boolean NOT NULL DEFAULT false,
    FOREIGN KEY (action_id, mission_id) REFERENCES actions (action_id, mission_id)
);

CREATE TABLE flags (
    flag_id text PRIMARY KEY,
    event_id text NOT NULL REFERENCES events,
    rule_code text NOT NULL,
    rule_version text NOT NULL,
    score numeric NOT NULL CHECK (score >= 0),
    severity text NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    reasons text[] NOT NULL CHECK (cardinality(reasons) > 0),
    escalated boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (event_id, rule_code, rule_version),
    UNIQUE (flag_id, event_id)
);

-- One row per outbound attempt; retries create new rows linked to the prior attempt.
CREATE TABLE processing_jobs (
    job_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id text NOT NULL REFERENCES events,
    flag_id text,
    retry_of bigint REFERENCES processing_jobs,
    request_key text NOT NULL UNIQUE,
    processor text NOT NULL,
    request_payload jsonb NOT NULL CHECK (jsonb_typeof(request_payload) = 'object'),
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'timed_out', 'cancelled')),
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    deadline_at timestamptz,
    finished_at timestamptz,
    error_message text,
    CHECK (status <> 'running' OR (started_at IS NOT NULL AND deadline_at IS NOT NULL)),
    CHECK (status NOT IN ('succeeded', 'failed', 'timed_out', 'cancelled') OR finished_at IS NOT NULL),
    CHECK (finished_at IS NULL OR finished_at >= created_at),
    CHECK (deadline_at IS NULL OR (started_at IS NOT NULL AND deadline_at > started_at)),
    FOREIGN KEY (flag_id, event_id) REFERENCES flags (flag_id, event_id)
);

-- Keep every returned response, including malformed/unsupported model output.
-- Structured columns may stay NULL until response parsing succeeds.
CREATE TABLE assessments (
    assessment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id bigint NOT NULL UNIQUE REFERENCES processing_jobs,
    raw_response text NOT NULL,
    parsed_response jsonb,
    question text,
    answer text,
    reasoning text,
    recommended_action text,
    severity_assessment text CHECK (severity_assessment IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    confidence numeric CHECK (confidence BETWEEN 0 AND 1),
    model text,
    model_version text,
    latency_ms numeric CHECK (latency_ms >= 0),
    tokens_per_sec numeric CHECK (tokens_per_sec >= 0),
    received_at timestamptz NOT NULL DEFAULT now()
);

-- Evidence links identify observations used to support specific claims.
CREATE TABLE assessment_evidence (
    assessment_id bigint NOT NULL REFERENCES assessments,
    event_id text NOT NULL REFERENCES events,
    claim text NOT NULL,
    PRIMARY KEY (assessment_id, event_id, claim)
);

-- Append new validation records rather than overwriting previous decisions.
CREATE TABLE validation_results (
    validation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    assessment_id bigint NOT NULL REFERENCES assessments,
    status text NOT NULL CHECK (status IN ('supported', 'unsupported', 'needs_review')),
    validator text NOT NULL,
    validator_version text NOT NULL,
    checks jsonb NOT NULL CHECK (jsonb_typeof(checks) = 'array'),
    reasons text[] NOT NULL DEFAULT '{}',
    validated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE acknowledgements (
    acknowledgement_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    flag_id text NOT NULL REFERENCES flags,
    operator_id text NOT NULL,
    action text NOT NULL CHECK (action IN ('acknowledged', 'resolved', 'reopened')),
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE risk_scores (
    risk_score_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    action_id text NOT NULL REFERENCES actions,
    model text NOT NULL,
    model_version text NOT NULL,
    scored_at timestamptz NOT NULL DEFAULT now(),
    will_fail numeric CHECK (will_fail BETWEEN 0 AND 1),
    anomaly_expected numeric CHECK (anomaly_expected BETWEEN 0 AND 1),
    failure_mode_probabilities jsonb NOT NULL DEFAULT '{}'
        CHECK (jsonb_typeof(failure_mode_probabilities) = 'object')
);

CREATE INDEX events_mission_timeline ON events (mission_id, occurred_at, received_at, event_id);
CREATE INDEX events_action ON events (action_id);
CREATE INDEX readings_action ON readings (action_id, timestamp);
CREATE INDEX anomalies_mission ON anomalies (mission_id, timestamp);
CREATE INDEX flags_event ON flags (event_id);
CREATE INDEX jobs_event ON processing_jobs (event_id);
CREATE INDEX jobs_queue ON processing_jobs (created_at, job_id) WHERE status = 'queued';
CREATE INDEX jobs_deadline ON processing_jobs (deadline_at) WHERE status = 'running';
CREATE INDEX validations_latest ON validation_results (assessment_id, validated_at DESC, validation_id DESC);
CREATE INDEX acknowledgements_latest ON acknowledgements (flag_id, created_at DESC, acknowledgement_id DESC);
CREATE INDEX risk_scores_action ON risk_scores (action_id, scored_at DESC);

-- Separate aggregates avoid multiplying counts when joining readings/anomalies/events.
CREATE VIEW mission_health AS
SELECT m.mission_id, m.mission_name, m.mission_status AS reported_status,
       COALESCE(a.failed_actions, 0) AS failed_actions,
       COALESCE(n.anomaly_count, 0) AS anomaly_count,
       COALESCE(f.flag_count, 0) AS flag_count,
       COALESCE(e.input_issues, 0) AS input_issues,
       CASE
           WHEN m.mission_status = 'COMPLETED' AND
                (COALESCE(a.failed_actions, 0) > 0 OR COALESCE(n.anomaly_count, 0) > 0 OR
                 COALESCE(f.flag_count, 0) > 0 OR COALESCE(e.input_issues, 0) > 0)
               THEN 'COMPLETED_WITH_ISSUES'
           WHEN m.mission_status = 'COMPLETED' THEN 'COMPLETED_NO_RECORDED_ISSUES'
           ELSE m.mission_status
       END AS observed_status
FROM missions m
LEFT JOIN (SELECT mission_id, count(*) FILTER (WHERE status = 'FAILED') AS failed_actions
           FROM actions GROUP BY mission_id) a USING (mission_id)
LEFT JOIN (SELECT mission_id, count(*) AS anomaly_count FROM anomalies GROUP BY mission_id) n USING (mission_id)
LEFT JOIN (SELECT e.mission_id, count(*) AS flag_count FROM flags f JOIN events e USING (event_id)
           GROUP BY e.mission_id) f USING (mission_id)
LEFT JOIN (SELECT mission_id, count(*) FILTER (WHERE input_status IN ('rejected', 'needs_review')) AS input_issues
           FROM events GROUP BY mission_id) e USING (mission_id);

-- Validation remains pending until a validator has recorded a verdict.
CREATE VIEW assessment_review AS
SELECT a.*, j.event_id, j.flag_id,
       COALESCE(v.status, 'pending') AS validation_status,
       v.reasons AS validation_reasons, v.validated_at
FROM assessments a
JOIN processing_jobs j USING (job_id)
LEFT JOIN LATERAL (
    SELECT status, reasons, validated_at
    FROM validation_results v
    WHERE v.assessment_id = a.assessment_id
    ORDER BY validated_at DESC, validation_id DESC LIMIT 1
) v ON true;

COMMIT;
