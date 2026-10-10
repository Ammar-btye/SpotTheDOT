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

- **System 2 plan (2026-10-10):** prompt + grammar-JSON + deterministic post-check first; LoRA is a gated stretch, shipped only if it beats the prompt baseline. Fine-tuning teaches format, not facts (research R5).
- **System 2 model (2026-10-10):** chosen by an on-box bake-off of Qwen3.5-9B / 27B / 35B-A3B, on grounded quality within ≤15 s p95. That gives measured numbers for the AMD/HF pitch.
- **System 2 owns the flag contract (2026-10-10):** typed Pydantic contract, with flags faked from `policy.py` until Laya output is wired in, so System 2 isn't blocked on System 1.
- **System 2 eval (2026-10-10):** headline numbers on real mission-held-out flags only, with bootstrap CIs and a human-checked judge; the templated explanation is both the fallback and the baseline. Only ~40 real anomalies, so synthetic data can't inflate the numbers.

## Pending
- Exact ROCm serving stack on gfx1151 (research agent running).
- Roles.
