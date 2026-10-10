-- Execute after schema.sql on a development database. All fixture rows roll back.
BEGIN;
SET LOCAL search_path TO spotlight, public;

INSERT INTO locations (location_id, location_name) VALUES ('TEST_WP', 'Test waypoint');
INSERT INTO sensor_sources (source_id, source_name, source_type)
VALUES ('TEST_SENSOR', 'Test navigation log', 'robot_log');
INSERT INTO missions (mission_id, mission_name, start_time, mission_status)
VALUES ('TEST_MISSION', 'Completed route with obstacle', '2026-01-01T10:00:00Z', 'COMPLETED'),
       ('TEST_OTHER', 'Another mission', '2026-01-01T10:00:00Z', 'COMPLETED');
INSERT INTO actions (action_id, mission_id, sequence, timestamp, location_id, action_type, status, failure_type)
VALUES ('TEST_ACTION', 'TEST_MISSION', 1, '2026-01-01T10:01:00Z', 'TEST_WP', 'NAVIGATION', 'FAILED', 'OBSTACLE_DETECTION');
INSERT INTO events (event_id, source_id, stream_id, source_event_id, mission_id, action_id,
                    event_type, occurred_at, raw_payload, prepared_payload, prepared_at, input_status)
VALUES ('TEST_EVENT', 'TEST_SENSOR', 'test-run', 'message-1', 'TEST_MISSION', 'TEST_ACTION',
        'ACTION_FAILED', '2026-01-01T10:01:00Z', '{"failure_type":"OBSTACLE_DETECTION"}',
        '{"failure_type":"OBSTACLE_DETECTION"}', now(), 'accepted');
INSERT INTO readings (reading_id, source_event_id, mission_id, action_id, timestamp, measurement_type, value, unit, quality)
VALUES ('TEST_READING_1', 'TEST_EVENT', 'TEST_MISSION', 'TEST_ACTION', '2026-01-01T10:01:00Z', 'BATTERY', 75, '%', 'GOOD'),
       ('TEST_READING_2', 'TEST_EVENT', 'TEST_MISSION', 'TEST_ACTION', '2026-01-01T10:01:00Z', 'TEMPERATURE', 30, 'C', 'GOOD');
INSERT INTO anomalies (anomaly_id, mission_id, action_id, timestamp, anomaly_type, severity, description)
VALUES ('TEST_ANOMALY', 'TEST_MISSION', 'TEST_ACTION', '2026-01-01T10:01:00Z', 'OBSTACLE', 'MEDIUM', 'Obstacle detected.');
INSERT INTO flags (flag_id, event_id, rule_code, rule_version, score, severity, reasons, escalated)
VALUES ('TEST_FLAG', 'TEST_EVENT', 'ACTION_FAILED', '1', 50, 'MEDIUM', ARRAY['Obstacle detected near test waypoint.'], true);
INSERT INTO processing_jobs (event_id, flag_id, request_key, processor, request_payload)
VALUES ('TEST_EVENT', 'TEST_FLAG', 'test-request-1', 'system2', '{"event_id":"TEST_EVENT"}');
INSERT INTO assessments (job_id, raw_response, answer, confidence)
SELECT job_id, '{"answer":"Obstacle detected."}', 'Obstacle detected.', 0.8
FROM processing_jobs WHERE request_key = 'test-request-1';
INSERT INTO assessment_evidence (assessment_id, event_id, claim)
SELECT assessment_id, 'TEST_EVENT', 'Obstacle detected.' FROM assessments a
JOIN processing_jobs j USING (job_id) WHERE j.request_key = 'test-request-1';

DO $$
DECLARE assessment bigint;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM mission_health WHERE mission_id = 'TEST_MISSION'
                   AND reported_status = 'COMPLETED' AND observed_status = 'COMPLETED_WITH_ISSUES'
                   AND failed_actions = 1 AND anomaly_count = 1 AND flag_count = 1) THEN
        RAISE EXCEPTION 'Mission health lost an incident or multiplied counts';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM mission_health WHERE mission_id = 'TEST_OTHER'
                   AND observed_status = 'COMPLETED_NO_RECORDED_ISSUES') THEN
        RAISE EXCEPTION 'Empty mission health is incorrect';
    END IF;
    SELECT a.assessment_id INTO STRICT assessment FROM assessments a JOIN processing_jobs j USING (job_id)
    WHERE j.request_key = 'test-request-1';
    IF (SELECT validation_status FROM assessment_review WHERE assessment_id = assessment) <> 'pending' THEN
        RAISE EXCEPTION 'Unvalidated model response must remain pending';
    END IF;
    INSERT INTO validation_results (assessment_id, status, validator, validator_version, checks, reasons)
    VALUES (assessment, 'unsupported', 'test-validator', '1',
            '[{"check":"claim_support","passed":false}]', ARRAY['Requires further evidence.']);
    INSERT INTO validation_results (assessment_id, status, validator, validator_version, checks)
    VALUES (assessment, 'supported', 'test-validator', '2', '[{"check":"claim_support","passed":true}]');
    IF (SELECT validation_status FROM assessment_review WHERE assessment_id = assessment) <> 'supported' OR
       (SELECT count(*) FROM validation_results WHERE assessment_id = assessment) <> 2 THEN
        RAISE EXCEPTION 'Latest validation or validation history is incorrect';
    END IF;
    BEGIN
        INSERT INTO events (event_id, source_id, stream_id, source_event_id, event_type, raw_payload)
        VALUES ('TEST_DUPLICATE', 'TEST_SENSOR', 'test-run', 'message-1', 'ACTION_FAILED', '{}');
        RAISE EXCEPTION 'Duplicate source message was accepted';
    EXCEPTION WHEN unique_violation THEN NULL;
    END;
    BEGIN
        UPDATE events SET mission_id = 'TEST_OTHER' WHERE event_id = 'TEST_EVENT';
        RAISE EXCEPTION 'Mismatched action and mission were accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;
    BEGIN
        UPDATE assessments SET confidence = 1.5 WHERE assessment_id = assessment;
        RAISE EXCEPTION 'Invalid confidence was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        UPDATE readings SET value = 'NaN'::float8 WHERE reading_id = 'TEST_READING_1';
        RAISE EXCEPTION 'Nonfinite measurement was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        UPDATE processing_jobs SET status = 'running' WHERE request_key = 'test-request-1';
        RAISE EXCEPTION 'Running job without a deadline was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
END $$;

-- Malformed input remains stored, even when no mission/timestamp can be resolved.
INSERT INTO events (event_id, source_id, stream_id, source_event_id, event_type, raw_payload, input_status, input_errors)
VALUES ('TEST_BAD_INPUT', 'TEST_SENSOR', 'test-run', 'message-2', 'UNKNOWN',
        '{"timestamp":"bad timestamp"}', 'rejected', '["Invalid timestamp"]');

ROLLBACK;
