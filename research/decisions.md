# Decisions

Single source of truth. Each entry is the decision plus why, in one or two lines, updated in place.

## Made
- **Phase (2026-10-09):** Research done; now building.
- **Idea (2026-10-09):** an operator dashboard for NextEra's SPOT challenge (live replay + post-mission review). It's the only prompt with an internship prize, and sponsor tracks reward literal, on-prompt answers (winners-knighthacks-history).
- **Sponsor targets:** NextEra (core), Hugging Face, AMD, Databricks, Neon, Figma, plus the auto-entered general tracks. Every sponsor's tech must be load-bearing, not a logo (synthesis §5: "sponsormaxxing").
- **Stack:** Next.js web app + Neon Postgres (operational DB) + an AMD-hosted HF model for System 2 + Databricks Free Edition for analytics/ML. The user chose it; it maps one sponsor to each layer.
- **Two-tier AI:** System 1 = fast, explainable rule/statistics triage running locally; System 2 = an HF open-source model on AMD ROCm that explains escalated flags. This puts hard gates first and the LLM second (lablab "LLM proposes, gates decide"), and gives a measurable routing saving for AMD judges.
- **Repos:** `KNIGHTHACKS/` (local: web app, System 1, Databricks notebooks, docs) and `KNIGHTHACKS-AMD/` (server: System 2 inference service). The AMD repo runs on the Radeon Cloud box, and the local app calls it over HTTP.
- **Databricks runs in Databricks' cloud (Free Edition), not on the AMD server.** Databricks is a managed SaaS platform and can't be self-hosted on our box. It does the analytics and the failure-risk model; AMD does inference.
- **System 2 output mirrors Orbit's AI-inspection format** (question / answer / reasoning, plus a recommended action). NextEra operators already use Orbit (kit screenshots).

## Pending
- Exact ROCm serving stack on gfx1151 (research agent running).
- Databricks↔app connection method (research agent running).
- Roles.
