# SPOTlight Neon database

This schema stores SPOT observations, prepared data, processing attempts, returned explanations, and validation history. A completed mission can still have failed actions or incident flags. `mission_health` preserves the reported status and displays `COMPLETED_WITH_ISSUES` when problems are recorded. Absence of recorded issues is not a guarantee of safety.

## Create the database

Use a new Neon development branch/database. Paste `schema.sql` into Neon's SQL Editor and run it, or use a PostgreSQL client with your connection string supplied securely as `DATABASE_URL`:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f web/db/schema.sql
```

The schema uses standard PostgreSQL and no extensions. It creates the `spotlight` namespace in one transaction. Run it once; it intentionally fails if the namespace already exists rather than silently hiding an incompatible schema. Use versioned migrations for later changes. Keep TLS enabled on the Neon connection and keep credentials outside source control. The schema has been checked with local PostgreSQL-compatible execution; deployment to Neon is a separate step.

Queries can use qualified names such as `spotlight.events`, or set `search_path TO spotlight, public` for the connection. Do not expose database credentials to the browser; the dashboard accesses data through your backend.

Run the rollback-only functional check after creating the schema:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f web/db/smoke_test.sql
```

It checks completed missions with incidents, accurate aggregate counts, duplicate ingestion, action/mission consistency, invalid measurement/confidence rejection, job deadlines, and pending/latest validation outcomes. Fixture IDs begin with `TEST_`; use a development database where those IDs are unused.

## Data flow

1. Register cameras, sensors, and replay feeds in `sensor_sources`. Load locations, assets, missions, and actions before normalized records that reference them.
2. Log the incoming envelope in `events.raw_payload` first. Use a stable, globally unique `event_id` and the source's message ID. `stream_id` identifies a real acquisition or replay run; reuse it for retries, change it for a genuinely new run. The unique source/stream/message key prevents duplicate ingestion. On conflict, compare the original payload and report mismatches; never overwrite original evidence. Missing or malformed mission/action references can be left NULL in this raw row and retained in the payload until resolved.
3. Clean and preprocess without changing the original payload. Record `prepared_payload`, `preprocessing_version`, `prepared_at`, input quality, and errors. Only accepted observations should become normalized `readings` or analysis jobs. Rejected inputs remain queryable. The backend must enforce this acceptance rule transactionally; the schema preserves evidence but does not perform cleaning or analysis.
4. Store measurements in `readings`; use `media` for image/video object-storage references. Multiple readings and files can belong to an event. Preserve original units in raw data and write standardized units in readings. Keep private object-storage references rather than expiring signed download URLs or image bytes. Link CSV anomalies to `anomalies`, and rule-detected incidents to `flags` with readable reasons and the rule version.
5. Insert a `processing_jobs` row in the same transaction as the data/flag that requires analysis. Store the exact request context, processor name, and stable `request_key`. A worker claims queued jobs, commits the claim, then calls the external processor outside the transaction. Do not hold database locks while waiting for an AI response.
6. Log the unmodified response in `assessments.raw_response`, even if it is malformed. Populate parsed fields only after parsing. A successfully returned response marks the job `succeeded`; it does not mean the explanation is supported. Save its evidence-event references in `assessment_evidence`.
7. Check response structure, evidence existence, claim support, conflicting readings, and required fields. Append an overall verdict to `validation_results`, with individual checks and reasons. Confidence is model output, not a validation verdict. Only a supported assessment should be presented as supported; pending, unsupported, and review-required responses must be labeled accordingly.
8. Read `assessment_review` and `mission_health` for the dashboard. Operator acknowledgements are a separate history; acknowledging an incident does not erase it or make an assessment true.

## Worker claim example

Use a short transaction or this single atomic statement. Set a timeout appropriate to the processor; the example is two minutes.

```sql
WITH next_job AS (
    SELECT job_id FROM spotlight.processing_jobs
    WHERE status = 'queued'
    ORDER BY created_at, job_id
    FOR UPDATE SKIP LOCKED LIMIT 1
)
UPDATE spotlight.processing_jobs j
SET status = 'running', started_at = now(), deadline_at = now() + interval '2 minutes'
FROM next_job n WHERE j.job_id = n.job_id
RETURNING j.*;
```

On error or timeout, record `error_message`, terminal status, and `finished_at`. A watchdog marks expired running jobs `timed_out`. Each retry creates a new job with `retry_of` and a new request key so previous attempts remain visible. Enforce transitions in the worker: complete jobs only while their status is `running`, and store the response and completion atomically. A late result must not overwrite a terminal attempt; reconcile it explicitly. Reuse a stable request key when repeating the same attempt and pass it as an idempotency key if the processor supports one.

## Existing challenge data

The six raw tables match CSV column names in `amd/system1/data/kit`: `locations`, `assets`, `missions`, `actions`, `readings`, and `anomalies`. Use explicit column lists when importing, map empty optional values to NULL, and load parents first. Raw CSV readings/anomalies may leave `source_event_id` NULL. Their action/mission links must agree.

Replay messages supply `event_id`, `mission_id`, `timestamp`, `event_type`, and `details`. Keep the complete message in `raw_payload`, extract recognized references, and use a run-prefixed event ID so subsequent replay runs do not collide. Preserve the original ID as `source_event_id`. The kit timestamps contain no timezone: establish the source timezone before converting them to `timestamptz`; do not silently guess UTC. For unresolved timestamps, retain the event with NULL `occurred_at` and `needs_review` status until resolved.

`OBSTACLE_DETECTION` means an obstacle was detected. It does not establish a collision. The database supports arbitrary event types, so a real collision event can be recorded when telemetry provides one. Preserve completion, obstacle, failure, and recovery events independently.

`risk_scores` stores model/version-specific forecasts for actions. The backend validates that failure-mode probabilities are numeric, bounded by 0–1, and sum to 1; PostgreSQL checks bounds on the two scalar probabilities. Do not use future outcomes when preparing prediction context.

## Useful queries

```sql
SELECT * FROM spotlight.mission_health WHERE mission_id = 'M001';

SELECT event_type, occurred_at, input_status, prepared_payload, raw_payload
FROM spotlight.events WHERE mission_id = 'M001'
ORDER BY occurred_at NULLS LAST, received_at, event_id;

SELECT answer, reasoning, recommended_action, validation_status, validation_reasons
FROM spotlight.assessment_review WHERE event_id = 'your-event-id';
```

This change supplies the database structure and worker contract. Sensor ingestion, storage uploads, cleaning, AI calls, validation logic, seeding, and dashboard endpoints still need backend implementation. No remote Neon database is created or modified by these files.
