# Databricks + Neon tech research (2026-10-09)

## 1. Scope

How to use Databricks and Neon in our Next.js SPOT dashboard well enough to compete for both prizes, with about 3 hours of Databricks work tonight. The dataset is 7 small files in `02_DATA/`: actions, anomalies, assets, locations, missions, readings and `replay.ndjson`. Everything below comes from current docs. Where a claim rests only on a community post, it says so.

**Can Databricks run on the AMD server? No.** Databricks is cloud-only on AWS, Azure and GCP: "you cannot set it up on your own cluster of machines (and there's no workaround)" ([community, Nov 2025](https://community.databricks.com/t5/administration-architecture/databricks-on-prem-version/m-p/140642/highlight/true)). Databricks runs the control plane, and serverless compute runs "in your Databricks account" ([architecture docs](https://docs.databricks.com/aws/en/getting-started/high-level-architecture)). The AMD box keeps doing System 2 inference. Databricks is a hosted workspace we call over HTTPS.

## 2. Findings

### 2.1 Free Edition vs. the 14-day trial
- **Free Edition** never expires and has daily usage limits. It gives "one serverless workspace" with no classic compute, and it is meant for "learning... non-commercial purposes." The **trial** lasts 14 days, includes up to $400 in credits and gives full platform access ([comparison](https://docs.databricks.com/aws/en/getting-started/free-trial-vs-free-edition)).
- **Limits** ([limitations page](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)):
  - **SQL warehouse:** one warehouse, capped at "2X-Small".
  - **Notebooks:** serverless notebook compute has "limited compute size and usage".
  - **Jobs:** at most 5 concurrent job tasks.
  - **Apps:** up to 3, each running up to 24 hours per start.
  - **Model serving:** a limit on active endpoints, and no GPU serving, provisioned throughput or GPU/batch custom models.
  - **Lakebase:** 1 project.
  - **Admin and languages:** no account console, no SSO/SCIM, and no R or Scala.
  - **Quotas:** going over a quota shuts compute down for the rest of the day. Data is kept.
- **Outbound internet** is "restricted to a limited set of trusted domains" (same page). No list is published ([community thread](https://community.databricks.com/t5/databricks-free-edition-help/whitelist-for-outbound-network-access/m-p/146636/highlight/true)), so **reaching Neon from a notebook is unverified.**
- **Included features:**
  - Notebooks, SQL, dashboards and "conversational data experiences" ([launch blog, Jun 2025](https://www.databricks.com/blog/introducing-databricks-free-edition)).
  - As of Jun 17, 2026, also Genie Code, serverless GPUs ("subject to availability"), Lakebase, Agent Bricks and Lakeflow Designer ([blog](https://www.databricks.com/blog/whats-coming-next-free-edition)).
  - Unity Catalog with a default `workspace` catalog. DBFS is disabled, so use volumes such as `/Volumes/workspace/default/...` ([community](https://community.databricks.com/t5/databricks-free-edition-help/can-load-read-file-in-databricks-free-edition-which-is-all-new/m-p/124848)).
- **AI Functions:** "querying Foundation Model APIs is enabled by default" in Free Edition, but you can't turn on preview features there ([Databricks community manager, Sep 2025](https://community.databricks.com/t5/machine-learning/how-to-enable-public-preview-features-in-databricks-free-edition/m-p/131649/highlight/true)).
- **PATs:** the docs never say whether Free Edition allows them. A Free Edition forum thread uses a PAT with the Genie API ([thread](https://community.databricks.com/t5/databricks-free-edition-help/how-to-connect-databricks-genie-ai-via-api/td-p/158022)). To create one: Settings → Developer → Access tokens → Generate ([PAT docs](https://docs.databricks.com/aws/en/dev-tools/auth/pat)).
- **Verdict: use Free Edition.** It doesn't expire mid-judging and needs no card, and it has the features we need. Keep the trial as a fallback only if the Neon-egress test fails and we want notebooks to write directly to Neon.

### 2.2 Getting the data in
- **UI:** upload to a Unity Catalog volume or use **Create table**. The UI accepts CSV, JSON and Parquet, with a 5 GB file limit ([upload docs](https://docs.databricks.com/aws/en/ingestion/file-upload/upload-data)). Free Edition volume steps: Catalog → workspace → default → Create → Volume ([community](https://community.databricks.com/t5/databricks-free-edition-help/can-load-read-file-in-databricks-free-edition-which-is-all-new/m-p/124848)).
- **CLI:**
  - Install: `brew tap databricks/tap && brew trust databricks/tap && brew install databricks`.
  - Log in: `databricks auth login --host <workspace-url>` ([CLI tutorial](https://docs.databricks.com/aws/en/dev-tools/cli/tutorial)).
  - Copy files: `databricks fs cp <dir> dbfs:/Volumes/<cat>/<schema>/<vol>/<path> -r --overwrite` ([fs commands](https://docs.databricks.com/aws/en/dev-tools/cli/reference/fs-commands)).
- **NDJSON:** Spark's JSON reader defaults to single-line mode, so `replay.ndjson` loads directly ([JSON docs](https://docs.databricks.com/aws/en/query/formats/json)).

### 2.3 ML and AI features: what's realistic in about 3 hours
| Feature | Free Edition? | Verdict |
|---|---|---|
| MLflow tracking + UC model registry | Hosted tracking server needs "no setup" ([tracking](https://docs.databricks.com/aws/en/mlflow/tracking)). Register with `mlflow.set_registry_uri("databricks-uc")` and a 3-level name. A signature is required ([UC models](https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle/)). | **Do it.** It's the core "prediction" for judges. |
| `ai_query` / `ai_summarize` | FMAPI is on by default (community, above). Not available on Classic warehouses ([ai_query](https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_query), [ai_summarize](https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_summarize)). | **Do it.** Anomaly briefs plus a mission debrief. |
| Genie space | Needs a pro or serverless warehouse, data in UC, at most 30 tables. The free API tier allows about 5 questions/min ([Genie set-up](https://docs.databricks.com/aws/en/genie/set-up)). | **Stretch goal.** 15 minutes to build, good live-demo value. |
| `ai_forecast` | Needs Pro or Serverless and enrollment in the "Predictive AI Functions" preview ([ai_forecast](https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_forecast)). Previews can't be enabled on Free Edition. | **Skip.** 27 missions is too thin to forecast anyway. |
| Model Serving / Vector Search | Limited, and there's no need for them. | Skip. Batch-score into a gold table instead. |

### 2.4 Connecting Databricks to Next.js, ranked by reliability tonight
1. **SQL Statement Execution REST API, called from a Next.js route handler. Best choice.**
   - Request: `POST https://{host}/api/2.0/sql/statements/` with `Authorization: Bearer <token>` and body `{warehouse_id, statement, parameters?, wait_timeout, disposition, format}`.
   - `wait_timeout` must be 5–50 s. INLINE results are capped at 25 MiB. Rows come back in `result.data_array` and columns in `manifest.schema.columns`. If the call times out it returns `PENDING`, so poll `GET /api/2.0/sql/statements/{id}` ([tutorial](https://docs.databricks.com/aws/en/dev-tools/sql-execution-tutorial)).
   - It's plain `fetch`, with no driver to bundle.
2. **`@databricks/sql` Node driver.**
   - `npm i @databricks/sql`, then `DBSQLClient.connect({token, host, path})` → `openSession` → `executeStatement` → `fetchAll` ([driver docs](https://docs.databricks.com/aws/en/dev-tools/nodejs-sql-driver)).
   - Works, but it adds more parts: an HTTP path, session lifecycle, and Node runtime only.
3. **Notebook writes to Neon over psycopg/JDBC.** Free Edition egress allows only "trusted domains", and no list is published (§2.1). **Unverified, so test it in 2 minutes before relying on it.**
4. **Embedded AI/BI dashboard.**
   - Basic embedding: "Users must sign in with their Databricks credentials."
   - External embedding: needs a service principal with OAuth, and the tokens last 1 hour ([embed docs](https://docs.databricks.com/aws/en/dashboards/embed)).
   - Free Edition has no account console, which makes this risky. Show the dashboard in Databricks during the demo instead.

### 2.5 The Databricks–Neon relationship
- **Acquisition:** Databricks announced it would acquire Neon on May 14, 2025 ([press release](https://www.databricks.com/company/newsroom/press-releases/databricks-agrees-acquire-neon-help-developers-deliver-ai-systems)) for about $1B ([TechTarget](https://www.techtarget.com/searchdatamanagement/news/366623864/Databricks-adds-Postgres-database-with-1B-Neon-acquisition)).
- **Lakebase is built on Neon:** "The serverless Postgres architecture that Neon pioneered is now the foundation of Lakebase Postgres... on Neon and on Databricks." The two run as separate deployments, and the docs describe no built-in sync between a Neon.com project and a workspace ([Neon docs](https://neon.com/docs/introduction/neon-and-lakebase)).
- **Synced tables are Lakebase-only:** they push UC Delta tables to *Lakebase* Postgres, not to an external Neon project ([synced tables](https://docs.databricks.com/aws/en/oltp/projects/sync-tables)).
- **Neon's GA "backend":** this covers Lakebase Postgres, Object Storage, Functions, Better Auth and an AI Gateway ([blog](https://neon.com/blog/neon-backend-is-ga)). The AI Gateway serves Databricks Foundation Model APIs, but it's in private preview, only in us-east-2, and needs a paid plan for models ([search summary of neon.com/docs/ai-gateway](https://neon.com/docs/ai-gateway/overview)). **Don't depend on it.**
- **Story:** "Neon is the operational system of record (live mission replay, operator acknowledgments, auth). Databricks is the lakehouse that turns that history into risk scores and AI briefs. The scores flow back into Neon, and the operator UI reads them at OLTP latency. That's the same OLTP/lakehouse split Databricks built Lakebase on, done with Neon.com."

### 2.6 Neon for Next.js tonight
- **Driver:** `@neondatabase/serverless`. Use `neon()` over HTTP for single queries, and `Pool` over WebSockets for interactive transactions ([driver](https://neon.com/docs/serverless/serverless-driver)). With Drizzle, use `drizzle-orm/neon-http` ([Drizzle guide](https://neon.com/docs/guides/drizzle)).
- **Branching:** branches are copy-on-write. A branch can be reset from its parent or restored to an earlier point in time ([branching](https://neon.com/docs/introduction/branching)). Reset command: `neon branches reset <id|name> --parent`. `--preserve-under-name` keeps a backup ([reset docs](https://neon.com/docs/guides/reset-from-parent)).
- **Neon Auth:** built on Better Auth, with users stored in the `neon_auth` schema. It branches with the database. Next.js setup uses `createNeonAuth` from `@neondatabase/auth/next/server` and `NEON_AUTH_BASE_URL` / `NEON_AUTH_COOKIE_SECRET` ([Neon Auth](https://neon.com/docs/neon-auth/overview)).
- **pg_cron:** supported, but jobs "only run when the compute is active" ([pg_cron](https://neon.com/docs/extensions/pg_cron)).
- **LISTEN/NOTIFY:** doesn't work on the pooled (PgBouncer transaction-mode) endpoint, so it needs the direct connection string ([pooling](https://neon.tech/docs/connect/connection-pooling/), [guide](https://neon.com/guides/pub-sub-listen-notify)).
- **Free plan:** 10 branches per project, 100 CU-hours, scale-to-zero after 5 minutes, and a 6-hour restore window ([pricing](https://neon.com/pricing)).

## 3. Recommended plan for tonight

**Owner A: Databricks (about 3 h)**
1. Sign up at login.databricks.com and choose Free Edition ([docs](https://docs.databricks.com/aws/en/getting-started/free-edition)). Create schema `workspace.spot` and volume `workspace.spot.raw`. Upload all 7 files in `02_DATA/` through the UI, or run `databricks fs cp ./02_DATA dbfs:/Volumes/workspace/spot/raw -r`.
2. **Smoke-test AI Functions** in the SQL editor: `SELECT ai_summarize('SPOT robot detected signal degradation at WP05.', 20);`. Also copy an exact foundation-model endpoint name from the Serving page for `ai_query`. The docs example uses `'system.ai.meta-llama-3-3-70b-instruct'`.
3. **Egress test (2 min):** in a notebook, run `%pip install psycopg[binary]`, then `psycopg.connect(NEON_URL)`. Note whether it passes or fails (see §2.4 option 3).
4. **Notebook `01_medallion`:**
   - **Bronze:** `spark.read.option("header",True).option("inferSchema",True).csv("/Volumes/workspace/spot/raw/actions.csv")`, and do the same for each CSV. Load replay with `spark.read.json(".../replay.ndjson")`. Save each as `bronze_*` with `saveAsTable`.
   - **Silver:** cast timestamps, cast `status = 'FAILED'` to a label, drop the `synthetic` column, and join actions with locations (to get `environment`) and missions.
   - **Gold:** `gold_failure_rates` (by location × action_type × configuration_version) and `gold_mission_kpis` (battery drop, failure count, anomaly count).
5. **Notebook `02_risk_model`:**
   - Features: location_id, action_type, battery_pct, configuration_version and environment. Label: FAILED.
   - Model: a sklearn `ColumnTransformer(OneHotEncoder)` + `LogisticRegression` pipeline with stratified 5-fold CV. With only 270 rows, report AUC honestly.
   - Logging: `mlflow.sklearn.autolog()`, then `mlflow.set_registry_uri("databricks-uc")` and `mlflow.sklearn.log_model(..., input_example=X[:5], registered_model_name="workspace.spot.action_failure_risk")`.
   - Output: batch-score all actions, plus a "what-if" grid over battery bands × config, into `gold_action_risk`. Log the coefficient-based top drivers too.
6. **Notebook or SQL `03_ai_briefs`:**
   - `CREATE TABLE gold_anomaly_briefs AS SELECT anomaly_id, mission_id, ai_query('<endpoint>', concat('You are a SPOT operator assistant. Summarize risk and next step: ', anomaly_type, ' severity ', severity, ' at ', location_id, ' asset ', asset_id, '. ', description)) AS brief FROM silver_anomalies`.
   - Add a mission debrief per mission using `ai_summarize` over the concatenated events.
7. Build an AI/BI dashboard on the gold tables to show in Databricks. If time allows, add a Genie space over the gold and silver tables.
8. Create a PAT (Settings → Developer → Access tokens). Note the host and the warehouse ID.

**Owner B: Next.js ↔ Databricks ↔ Neon (about 1.5 h)**
1. Set env vars: `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_WAREHOUSE_ID`, `DATABASE_URL` (pooled).
2. Write `lib/databricks.ts`:
   ```ts
   const r = await fetch(`https://${process.env.DATABRICKS_HOST}/api/2.0/sql/statements/`, {
     method: "POST",
     headers: { Authorization: `Bearer ${process.env.DATABRICKS_TOKEN}`, "Content-Type": "application/json" },
     body: JSON.stringify({ warehouse_id: process.env.DATABRICKS_WAREHOUSE_ID,
       statement: "SELECT * FROM workspace.spot.gold_action_risk", wait_timeout: "50s",
       disposition: "INLINE", format: "JSON_ARRAY" }) });
   const j = await r.json(); // if j.status.state is PENDING/RUNNING, poll GET .../statements/{j.statement_id}
   const cols = j.manifest.schema.columns.map((c: any) => c.name); const rows = j.result.data_array;
   ```
3. Write `app/api/sync/databricks/route.ts` (Node runtime). It pulls `gold_action_risk`, `gold_anomaly_briefs` and `gold_mission_kpis`, then upserts them into Neon tables `risk_scores`, `anomaly_briefs` and `mission_kpis` with `neon()`. The UI reads only from Neon, so it stays fast and still works if the 2X-Small warehouse is cold or over quota. Add a "Synced from Databricks at …" badge and a re-sync button. This is the visible Databricks → result link.
4. Optional live path: a `/api/ask` route that forwards to the Genie Conversation API or runs a parameterized statement.

**Neon features to make meaningful**
1. Use a `demo` branch for the live demo and run `neon branches reset demo --parent` before each judge, so every replay starts clean.
2. Use Neon Auth for operator sign-in. Acknowledgments FK to `neon_auth` users, so "who reviewed which anomaly" is SQL.
3. Write live replay events into Neon as they stream. The Databricks sync reads Neon history, and the gold scores come back to Neon. That closes the loop.

## 4. Open questions
- Does Free Edition serverless allow egress to `*.neon.tech`? Step 3's test decides whether notebooks write to Neon directly.
- Are PATs enabled in our Free Edition workspace? The community says yes, but no official doc confirms it. If not, look into OAuth (U2M/M2M).
- What are the exact foundation-model endpoint names in our workspace, and does `ai_query` stay within daily quotas for 40 rows? It should.
- Is the Genie API free tier (about 5 questions/min) enough for a live judge Q&A?
- The Neon free-plan storage figure conflicts: 1 GB on [pricing](https://neon.com/pricing) vs. 0.5 GB in the [GA blog](https://neon.com/blog/neon-backend-is-ga). This doesn't matter for our dataset size.
