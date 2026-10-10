# web: SPOTlight operator console (Next.js)

The operator-facing UI. The system map is in `docs/ARCHITECTURE.md`.

```bash
cd web && npm install && npm run dev   # http://localhost:3000
```

## Current state (2026-10-10)
- One page, `/` (`src/app/page.tsx`): the shift-start briefing. It shows the hidden-failures headline, stat tiles, the priority queue and the battery-cliff chart.
- The other sidebar items (Missions, Analytics, Assets, AI review, Settings) are placeholders (`src/components/shell/nav.ts`).
- **Data comes from the kit CSVs in `data/kit/`, read on the server** (`src/lib/kit.ts`, `src/lib/analysis.ts`). The page doesn't call the backend yet.

## Next: wire it to the backend
The FastAPI backend (`backend/`, port 8000) already serves everything this page computes, plus the parts it can't compute itself:
- the live feed (`/api/v1/events`)
- Laya + rules flags (`/api/v1/flags`)
- explanations (`/api/v1/flags/{id}/explain`)
- forecasts, insights and search

Backend CORS allows `http://localhost:3000`. Routes are listed in `backend/README.md`.

## Design rules (Figma track)
- Never show status by color alone: use color + icon + word.
- Everything works from the keyboard.
- Text meets WCAG AA contrast.
- Dark operator theme, with a light toggle.

`db/schema.sql` here is a legacy schema that nothing runs. The real schema is `db/migrations/` at the repo root.
