# Architecture: SPOT Operator Console

> **Working name: "SPOTlight".** It turns SPOT robot mission data into a clear, trustworthy operator view, live and after the mission.
> **Diagram:** [SPOTlight Architecture (FigJam)](https://www.figma.com/board/6atlFaPzNaSJWz14IthYxr). Source: `docs/architecture.mmd`.
> Every design choice cites the evidence that justified it: `research/…` files and specific winning projects.

## 1. The one-sentence pitch
**"SPOT says 26 of 27 missions were green. We show the 21 that weren't, explain why, and tell the operator what to do next."**
(Data: `research/spot-data-insights-2026-10-09.md` #1. A one-line opener followed by a live demo is how winners pitch: `winners-playbook-judging`.)

## 2. The big picture

```
                         ┌──────────────────────── LOCAL REPO: KNIGHTHACKS/ ────────────────────────┐
  SPOT replay.ndjson ──▶ │ replay streamer ──▶ /api/ingest ──▶ SYSTEM 1 "Triage" (rules + stats)     │
  (+ readings/anomalies  │  (scripts/replay)     (Next.js)        │ every event, <5 ms, explainable   │
   joined by action_id)  │                                        ▼                                    │
                         │                        ┌──────── NEON POSTGRES ────────┐                  │
                         │  Web UI (Next.js) ◀──▶ │ raw tables · events · flags   │ ◀── sync ──┐     │
                         │  Figma-designed        │ assessments · insights · risk │            │     │
                         │  Live / Review / Map   └──────────────┬────────────────┘            │     │
                         │                                       │ escalated flags             │     │
                         │                     system2 worker ◀──┘ (score ≥ threshold)         │     │
                         └──────────────────────────────┬──────────────────────────────────────┼─────┘
                                                        │ HTTPS + API key                      │
                         ┌──── AMD REPO: KNIGHTHACKS-AMD/ (Radeon Cloud, gfx1151, ROCm) ────┐ │
                         │ FastAPI "System 2 Analyst" ── HF open-source VLM/LLM on ROCm     │ │
                         │ /v1/assess  /v1/vision  /v1/debrief  /v1/bench  /health          │ │
                         └──────────────────────────────────────────────────────────────────┘ │
                         ┌──── DATABRICKS FREE EDITION (Databricks' cloud, not our server) ──┐ │
                         │ CSVs → Unity Catalog volume → bronze/silver/gold Delta tables     │─┘
                         │ failure-risk model (MLflow) → risk + insight tables               │
                         └───────────────────────────────────────────────────────────────────┘
```

## 3. Each piece: what it is, why it exists, and which prize it serves

### 3.1 Web UI: Next.js + Figma design → **Figma, NextEra, Most Useful**
- **What:** the operator console. The pages, in build priority order:
  1. **Overview:** True Mission Health vs reported status (the "green but broken" hero), a priority queue, V1-vs-V2 at matched battery, the battery cliff.
  2. **Live:** the replay player; the floor plan with SPOT's position moving through waypoints; an event timeline; flags appearing; System 2 cards.
  3. **Mission review:** after a mission, its timeline, actions, readings, anomalies and an AI debrief.
  4. **Map:** a floor-plan heat map of failure rate per waypoint. Click a waypoint for why it fails (environment).
- **Why:** NextEra's prompt literally asks for "locations, timestamps, readings, anomaly flags, both in real time and after a mission… without needing to become technical experts." Sponsor tracks reward literal answers: all three of last year's NextEra winners (DronePath, GridWatch, NE Drone Routing) solved the exact prompt with the provided data (`winners-knighthacks-history`).
- **Design rules (Figma track: navigation, flows, accessibility):** status is never shown by color alone (color + icon + word); keyboard-navigable; WCAG AA contrast; dark operator theme (like Orbit) with a light-mode toggle. Design prizes go to a cohesive identity, a named persona or mascot (`winners-design-creative-categories`), so give SPOT's AI a name and a consistent visual language.

### 3.2 Neon Postgres → **Neon**
- **What:** the single operational database. It holds the raw kit tables, live `events`, System 1 `flags`, System 2 `assessments`, the Databricks `insights`/`risk_scores`, and operator `acknowledgements`.
- **Why it's "meaningful", not a logo:** it's the real-time event store the Live page reads, the join point between all three systems, and the audit trail of every AI decision. Plus **Neon branching**: a `demo` branch we reset before each judge, so the replay starts clean every time.

### 3.3 System 1 "Triage": local, rules + statistics → **NextEra, Best AI**
- **What:** a TypeScript function run on every ingested event. It scores the event and attaches human-readable reasons:
  | Rule | Fires when | Evidence |
  |---|---|---|
  | Failed action | `ACTION_FAILED` (weighted by failure_type) | 21 of 26 completed missions hide failures |
  | Priority anomaly | severity × asset criticality ≥ threshold | severity ≠ priority (insight #6) |
  | Battery cliff | battery ≤ 30% | 33% success at ≤25% (insight #2) |
  | Risky location | Databricks risk score for (waypoint, action type) is high | WP09/WP02/WP15 (insight #4) |
  | Suspect reading | quality QUESTIONABLE, or value outside the band for its type | insight #7 |
  | Silent failure | `MISSION_COMPLETED` but the mission has failures or HIGH+ anomalies | insight #1 |
- **Escalation:** score ≥ threshold, any CRITICAL item, or any CRITICAL asset → the flag is queued for System 2.
- **Why rules first:** fast, free, explainable, and the "Explainability" criterion is in NextEra's brief. Winners put deterministic gates around the LLM. Autobelay (1st) and Killswitch Capital (3rd) at lablab's Alpaca hackathon both let "the LLM propose, deterministic code enforce" (`winners-lablab-ai`). Here the gates decide *what gets AI attention*.

### 3.4 System 2 "Analyst": Hugging Face model on AMD ROCm → **AMD, Hugging Face, Best AI**
- **What:** a FastAPI service in the **separate `KNIGHTHACKS-AMD` repo**, running an open-source HF vision-language model on the Radeon 8060S with ROCm. Endpoints:
  - `POST /v1/assess`: a flag + context packet (asset history, waypoint stats, risk score, optional image) → **Orbit-style JSON**: `question`, `answer`, `reasoning`, `recommended_action`, `confidence`, `severity_assessment`.
  - `POST /v1/vision`: an inspection image → structured reading (e.g., gauge psi, thermal hotspot °C) to cross-check against the logged value.
  - `POST /v1/debrief`: mission stats → a plain-English after-action summary for the Review page.
  - `GET /v1/bench`: tokens/sec, p50/p95 latency, and GPU memory on ROCm. **This is the AMD story in numbers.**
  - `GET /health`.
- **Why:** AMD-sponsored winners showed *measured* gains. RadeonFlow won AMD's Developer Challenge on benchmark speedups. Nota's PASCAL-MoE won because it "demonstrated… quantitative evaluation" (`winners-taikai-hackerearth-enterprise`). Last year at Knight Hacks, Restful Knights (Best Overall) and EchoAI (Best AI + AMD) both ran on ROCm, and Lawgorithm won AMD with ROCm + Hugging Face + Postgres, nearly our stack (`winners-knighthacks-history`).
- **The AMD/HF metric we'll show:** "System 1 handled X% of events; System 2 ran only on Y escalations, at Z tokens/s on Radeon." The model, dataset card and (stretch) LoRA adapter get published to the HF Hub for "meaningful use of the HF ecosystem."
- **Why a separate repo:** it runs on the AMD box with its own Python/ROCm environment. The local app only knows `AMD_API_URL` + `AMD_API_KEY`. If the server is down, the worker marks assessments `pending` and the UI shows System 1's reasons, so the demo never breaks.

### 3.5 Databricks: analytics + failure-risk model → **Databricks**
- **What:** three notebooks in `databricks/` (versioned here, run in Databricks Free Edition):
  1. `01_ingest_bronze`: upload the kit CSVs to a Unity Catalog volume, then bronze Delta tables.
  2. `02_silver_gold_insights`: joins; True Mission Health; reliability by waypoint, action type, battery band and config; **the V1-vs-V2-at-matched-battery analysis** (insight #3).
  3. `03_failure_risk_model`: train P(action fails | waypoint, action type, battery, config, environment), track it in MLflow, and write `risk_scores` (waypoint × action type × battery band).
  Gold tables sync into Neon (`npm run sync:databricks`), and System 1 uses `risk_scores` live. **That's the "connects Databricks to a useful result" line in the prompt.**
- **Why not on the AMD server:** Databricks is a managed cloud platform; it can't be installed on our box. Its job is the data and ML layer, and AMD's job is model inference.
- Databricks-sponsored winners used 4–5 platform features (`winners-taikai-hackerearth-enterprise`): volumes, Delta, SQL, MLflow, plus an AI/BI dashboard if time allows.

### 3.6 Replay streamer + System 2 worker (local scripts)
- `scripts/replay.ts`: reads `replay.ndjson`, enriches each action with its readings and anomalies, and POSTs to `/api/ingest` at a configurable speed (e.g., 20×). This is the "real time" half of the prompt.
- `scripts/system2-worker.ts`: polls Neon for escalated flags, builds the context packet, calls AMD `/v1/assess`, and stores the result. It's decoupled so a slow GPU never stalls the live feed.

## 4. The contract between the repos (keep it in sync)
```http
POST {AMD_API_URL}/v1/assess        Header: X-API-Key: {AMD_API_KEY}
{ "flag_id": "F-123", "event": {...}, "reasons": ["Battery 18% ≤ 30%", "..."],
  "context": { "asset": {...}, "asset_history": [...], "location": {...}, "location_stats": {...},
               "risk_score": 0.41, "mission_so_far": {...} },
  "image_b64": "<optional jpeg>" }
→ 200 { "question": "Is Electrical Panel 12 safe to leave until the next route?",
        "answer": "No, escalate.", "reasoning": "...", "recommended_action": "...",
        "severity_assessment": "HIGH", "confidence": 0.78,
        "model": "Qwen/...", "latency_ms": 840, "tokens_per_sec": 31.2 }
```

## 5. Neon schema (summary; full DDL in `web/db/schema.sql`)
Raw tables: `missions`, `actions`, `readings`, `anomalies`, `locations`, `assets` (loaded from the kit).
Live tables: `events` (ingested replay), `flags` (System 1 output: score, reasons[], escalated), `assessments` (System 2 output, with model, latency and tokens/s), `acknowledgements` (operator ack/resolve).
Analytics tables (from Databricks): `insights` (named metrics), `risk_scores`.

## 6. Build order (aim: end to end by Saturday noon, per `winners-playbook-judging`)
1. Neon schema + seed → 2. System 1 + ingest + replay → 3. Live + Overview pages (mocked System 2) → 4. AMD service up, worker connected → 5. Databricks notebooks + sync → 6. Map + Review pages → 7. Figma polish, accessibility, bench numbers, HF Hub push → 8. Devpost, video, pitch.
If time runs short, **cut depth, not the core loop**: replay → triage → explain → act.
