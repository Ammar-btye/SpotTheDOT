# Decisions

Single source of truth. Each entry is the decision plus why, in one or two lines, updated in place.

## Made
- **Phase (2026-10-09):** Research done; now building.
- **Idea (2026-10-09):** an operator dashboard for NextEra's SPOT challenge (live replay + post-mission review). It's the only prompt with an internship prize, and sponsor tracks reward literal, on-prompt answers (winners-knighthacks-history).
- **Sponsor targets:** NextEra (core), Hugging Face, AMD, Neon, Figma, plus the auto-entered general tracks. Every sponsor's tech must be load-bearing, not a logo (synthesis §5: "sponsormaxxing").
- **Stack:** Next.js web app + Neon Postgres (operational DB) + AMD-hosted HF models (Laya for failure risk, an LLM/VLM for System 2). The user chose it; it maps one sponsor to each layer.
- **Two-tier AI:** System 1 = fast, explainable rule/statistics triage running locally; System 2 = an HF open-source model on AMD ROCm that explains escalated flags. This puts hard gates first and the LLM second (lablab "LLM proposes, gates decide"), and gives a measurable routing saving for AMD judges.
- **Repo layout (2026-10-10):** one repo (`SpotTheDOT`). AMD-side code lives in `amd/` with its own Python deps and runs on the Radeon Cloud box; the app talks to it only over HTTP. Judges review one public repo, and API-contract changes land in one commit.
- **Databricks dropped (2026-10-10).** We stick to AMD servers: Laya, fine-tuned on AMD, produces the failure-risk scores, and the analytics become SQL views in Neon. That's one fewer platform, and all model work stays on AMD.
- **System 2 context = custom read-only MCP server doing RAG on pgvector in Neon (2026-10-10).** Tools embed a query with an open-source embedding model hosted on AMD and retrieve from Neon pgvector with metadata filters; numeric stats stay plain SQL. Embedding model: **Qwen3-Embedding-0.6B** (1024-d, Apache-2.0; fallback snowflake-arctic-embed-l-v2.0), exact vector search at our scale (`research/tech-embedding-model-amd-2026-10-10.md`).
- **Logs + raw data in Neon (2026-10-10):** same database, schemas `raw` (SPOT data verbatim, append-only) and `app` (model calls, MCP tool calls, requests, jobs); `LOGS_DATABASE_URL` can split them out later. One connection string, and logs join to flags.
- **Containerize everything (2026-10-10):** every service ships a Dockerfile and joins a root docker-compose.yml, so the whole stack starts with one command; on the no-root AMD Jupyter VMs the same code runs in a venv.
- **Backend = FastAPI (2026-10-10)** in `backend/`, its own container: same language as Laya, the validator and the MCP client. Route tree in `docs/backend-services-contract.md`.
- **Laya runs in its own container (2026-10-10)** (`amd/system1/service/`, port 8082), called by the backend over HTTP; keeps the GPU/model concerns out of the API.
- **Keep LoRA for the Laya fine-tune (2026-10-10).** PEFT ports to other HF models. The gap vs full FT (run2 0.805 vs 0.733 real, 0.846 vs 0.602 counterfactual) most likely comes from setup (to be confirmed by the sweep): 3 epochs, LLRD on adapters, frozen norms, no training counterfactuals. Fixed in code and swept via `scripts/sweep_lora.sh`; compare on held-out F1/calib CE, never train loss.
- **System 2 output mirrors Orbit's AI-inspection format** (question / answer / reasoning, plus a recommended action). NextEra operators already use Orbit (kit screenshots).

## Pending
- Exact ROCm serving stack on gfx1151 (research agent running).
- Roles.
