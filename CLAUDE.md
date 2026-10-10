# Knight Hacks project

**Phase: research done (2026-10-09). Waiting on sponsor tracks.** Next step: at the opening ceremony, record every prompt verbatim in `research/knighthacks-ix-tracks.md`, then score ideas with the synthesis §4 scorecard.
Current goal: learn what wins hackathons from past winners, so we can design a winning project once the tracks drop.

## Event
- **Knight Hacks IX**, Oct 9–11, 2026, in person in Orlando, FL (source: https://www.mlh.com/seasons/2027/events).
- Devpost: https://knight-hacks-ix.devpost.com/. Sponsor challenges are revealed at the opening ceremony (Fri 7 PM).
- **Devpost deadline: Sun Oct 11, 10:00 AM** (code freeze at 11 AM). A public repo and a demo video are required. Sponsor prizes must be ticked manually on Devpost. Judging runs 12–4 PM; prepare both a 3-minute and a 6-minute version (see the synthesis, §5b).
- Rubric: Originality, Technical Understanding (name the AI tools you used), Functionality, Design, Wow Factor.
- Hacker's Guide: https://knight-hacks.notion.site/knight-hacks-ix-hackers-guide
- Main prizes: Best Overall 1st–3rd, Most "Useful" Hack, Best Embedded, Best AI, Best Game Dev, Best First-Time Hacker.
- MLH prizes (https://www.mlh.com/events/knight-hacks-ix/prizes): ElevenLabs, Gemini API, Tiger Data, Solana, Presage, Vultr, GoDaddy Registry domain, DEV Writing Challenge.

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
- `research/winners-*.md`: per-topic winner logs with source links.
