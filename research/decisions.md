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
- **System 2 output mirrors Orbit's AI-inspection format** (question / answer / reasoning, plus a recommended action). NextEra operators already use Orbit (kit screenshots).

## Pending
- Exact ROCm serving stack on gfx1151 (research agent running).
- Roles.
