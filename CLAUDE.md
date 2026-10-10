# Knight Hacks project

**Phase: building (2026-10-10).** Project: SPOTlight, an operator console for NextEra's SPOT challenge (`research/decisions.md`).
System map: `docs/ARCHITECTURE.md`. How to run it: `docs/RUNNING.md`. Current goal: finish the core loop (replay → triage → explain → act) and submit by Sun 10:00 AM.

## Event
- **Knight Hacks IX**, Oct 9–11, 2026, in person in Orlando, FL (source: https://www.mlh.com/seasons/2027/events).
- Devpost: https://knight-hacks-ix.devpost.com/. Sponsor challenges are revealed at the opening ceremony (Fri 7 PM).
- **Devpost deadline: Sun Oct 11, 10:00 AM** (code freeze at 11 AM). A public repo and a demo video are required. Sponsor prizes must be ticked manually on Devpost. Judging runs 12–4 PM; prepare both a 3-minute and a 6-minute version (see the synthesis, §5b).
- Rubric: Originality, Technical Understanding (name the AI tools you used), Functionality, Design, Wow Factor.
- Hacker's Guide: https://knight-hacks.notion.site/knight-hacks-ix-hackers-guide
- Main prizes: Best Overall 1st–3rd, Most "Useful" Hack, Best Embedded, Best AI, Best Game Dev, Best First-Time Hacker.
- MLH prizes (https://www.mlh.com/events/knight-hacks-ix/prizes): ElevenLabs, Gemini API, Tiger Data, Solana, Presage, Vultr, GoDaddy Registry domain, DEV Writing Challenge.

## Engineering rules
- **Containerize every service.** Each new app or service gets its own `Dockerfile` + `.dockerignore` in its folder,
  configured only by env vars, with a HEALTHCHECK and a non-root user.
- **One unified `docker-compose.yml` at the repo root runs the whole project.** Whenever a container is added, removed
  or changed (new service, port, env var, volume, healthcheck, build arg, dependency), update `docker-compose.yml` in
  the same change, plus the ports table in `docs/backend-services-contract.md`, the header comment listing services,
  and `docs/RUNNING.md`. Never add a second compose file; use profiles inside the unified one.
- GPU services take a `TORCH_VARIANT` build arg (`cpu` | `rocm-gfx1151` | `rocm-gfx1201`). The AMD Radeon Cloud
  Jupyter VMs have no root and can't run Docker, so there the same code runs natively in a venv. The SSH box
  (`ssh spot-amd`) is a W7900D (gfx1100) with ROCm torch in `/opt/venv`; see `docs/AMD-GPU.md`.
- Services talk over HTTP using the contracts in `docs/` (e.g. `docs/system2-rag-contract.md`); change the contract first.

## Context protocol
- At the start of every session, read `research/INDEX.md` and `research/decisions.md`.
- Open individual research files only when the task needs them. Don't load them all.
- Never re-research a project already logged in an existing file. Grep `research/` first.

## Research rules
- Sources, in order of preference: Devpost project galleries, ETHGlobal showcase,
  lablab.ai, Kaggle solution write-ups, GitHub repos linked from submissions.
- Only log projects with a confirmed win. Every entry needs a source URL.
- If a page fails to load or comes back empty, note it under "Open questions"
  and move on. Don't guess at its contents.

## Output rules
After each research task, write `research/winners-<topic>-<YYYY-MM-DD>.md` with:
1. Scope: what was searched and what was skipped
2. Winners table: name | hackathon | prize/track | what it does | stack | repo | source URL
3. Patterns: what wins, recurring tech, what judges rewarded
4. Open questions / next searches

Keep each file under ~2,000 words. Split by topic rather than growing one file.
Then add a one-line entry for the new file to `research/INDEX.md`.
Keep every source URL. We'll come back to them for deep dives once the sponsor tracks are out.

## Decisions
When we decide something (idea, stack, roles), update `research/decisions.md` in place.
Record the decision and why in one or two lines. Don't log the discussion that led to it.
That file is the single source of truth for decisions.

## Layout
- `research/INDEX.md`: one line per research file. Start here.
- `research/decisions.md`: what we've decided and why.
- `research/synthesis-*.md`: cross-file patterns ("what wins"). Read this before brainstorming ideas.
- `research/winners-*.md`: winner logs we still use for the pitch, judging and prizes.
- `research/tech-*.md`: research behind the tech we built.
- `docs/`: architecture, service contracts and runbooks. Change the contract before the code.
