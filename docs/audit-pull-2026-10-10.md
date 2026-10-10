# Light audit: the PR #2 / PR #3 pull (2026-10-10)

Scope: `8aaac30..0539d32`, which covers PR #2 (`amd/system2/`, the System 2 Analyst), PR #3 (`web/`, the Next.js
frontend) and the shared files it touched. Read-only. Findings from earlier audits (`docs/audit-2026-10-10.md`) are
excluded. Critical and high findings were each re-checked by an independent skeptic. None was refuted.

## Tests (all green)
| Suite | Result |
|---|---|
| `make test` (policy, backend, system1, mcp) | 194 passed, 7 skipped |
| `amd/system2` | 710 passed, 1 skipped (opt-in container test) |
| backend incl. the new `test_system2_integration.py` | 119 passed |
| `web/` | `npm run lint` 0 problems; `npm run build` OK |

## Findings
| ID | Sev | Finding | Where | Fix |
|---|---|---|---|---|
| P-1 | **High** | The default stack is broken. `system2` now starts in the `local/hybrid/neon` profiles with an empty `SYSTEM2_API_KEY`, so it exits 2 and restarts in a loop, `make up` exits 1, and `/explain` falls back to the template. | `docker-compose.yml:146-149,193,203`; `.env.example:47-48` | Add an uncommented `SYSTEM2_API_KEY=` (≥16 chars) to `.env.example` and the local `.env`, and fix the stale ".env.example:47" comment. |
| P-2 | **High** | The battery-cliff chart renders empty (bars are 0 px tall). | `web/src/components/BatteryCliff.tsx:26-37` | Give the bar container a definite height. |
| P-3 | Med | The backend's SQL-fallback context packet is rejected by System 2 with a 422 (`asset_history` is a dict), and that opens the System 2 breaker for 60 s. | `backend/app/services/flags.py:222-223` | Send the shape System 2's contract expects. |
| P-4 | Med | The mission debrief calls `/v1/debrief`, which System 2 doesn't serve. The 404 opens the breaker that `/explain` shares. | `backend/app/services/system2.py:170-217` | Use the template debrief until System 2 serves it, or give debrief its own breaker. |
| P-5 | Med | System 2 `stub`, `insufficient_context` and `template` replies are stored as final (DONE) and RAG-indexed, so turning on live mode never replaces them (the M10 regression path). | `backend/app/services/flags.py:246-283`; `amd/embed/ingest.py:281` | Treat those as non-final `TEMPLATE` and skip indexing them. |
| P-6 | Med | `make e2e` still asserts that `/explain` returns the template, but compose now wires a System 2 stub, so e2e fails after the pull. | `scripts/e2e.py:17,200-209` | Accept `stub` and `template`. |
| P-7 | Med | The web "V2 vs V1 +14 pts" tile shows the confounded headline. Our research (and the backend's insight) is +5.3 at matched battery. | `web/src/lib/analysis.ts:430-465` | Show the matched-battery number. |
| P-8 | Med | **The frontend is not integrated.** `web/` makes zero network calls: it reads static kit CSVs and re-implements System 1 in TypeScript, with no backend, live replay or System 2 path. | `web/src/lib/kit.ts:136`, `analysis.ts:417-428` | Fetch from `/api/v1` (flags, missions, insights, explain). |
| P-9 | Med | `web/` breaks the CLAUDE.md rules: no Dockerfile, no compose service, no ports-table or RUNNING.md row. | `docker-compose.yml:6-19` | Containerize it (port 3000) and add it to compose. |
| P-10 | Low | System 2: unpinned deps and base image; pytest ships in the runtime image; deep JSON gives a 500 instead of a 422; the error names `AMD_API_KEY` but compose sets `SYSTEM2_API_KEY`. | `amd/system2/requirements.txt`, `analyst/api.py:78,103-132` | Pin; split dev deps; add a body limit; fix the message. |
| P-11 | Low | Web: queue rows are no-op focusable buttons; "89% on a full charge" mislabels the 61%+ band; `web/db/schema.sql` is a stale subset of `db/migrations`; `@neondatabase/serverless` is unused. | `PriorityQueue.tsx:23-66`, `analysis.ts:232,455`, `web/db/schema.sql` | Small cleanups. |
| P-12 | Low | Docs: the ARCHITECTURE.md "Superseded" note describes the wrong wire shape; stale System 2 rows in the ports table and in decisions.md; `make test` skips the System 2 suite. | `docs/ARCHITECTURE.md:63-89`, `docs/backend-services-contract.md:12`, `Makefile:31` | Update; add `test-system2`. |

## Integration checks
- **System 2 ↔ backend ↔ MCP: works once a key is set.**
  - All 59 real flags were sent through the backend's own MCP client and System 2 client to the compose-built `system2`. Every reply was contract-valid: 58 `stub`, 1 `insufficient_context`.
  - Auth: no key → 401; wrong key → 401 (checked before the body is parsed); bad body → 422.
  - The image is 54 MB, runs as a non-root user, and is healthy.
- **CORS:** the backend allows `http://localhost:3000`, which matches Next dev.
- **Web:** holds no secrets and makes no admin-token calls, but it isn't wired to the backend at all (P-8).
- **Note:** `system2` is currently running with a scratch key the checker created. The backend container predates the pull, so it has no `SYSTEM2_URL`/key yet.

## CI added: `.github/workflows/ci.yml`
It runs on push to `main`, on pull requests and manually. It has 6 parallel jobs, needs no secrets, and has read-only permissions. Each job was proven locally in a fresh environment, and actionlint passes.

| Job | What | Local proof |
|---|---|---|
| backend | policy drift test + backend unit tests | 25 + 116 passed, 18 s |
| mcp | unit tests | 33 passed, 14 s |
| system2 | unit tests | 710 passed, 68 s |
| system1 | service tests in fast mode (no torch/model) | 18 passed, 9 s |
| web | `npm ci`, lint, build | pass, ~98 s |
| docker | builds the backend, db, mcp and system2 images (no push) | pass, 42 s |

Excluded on purpose:
- the real-Laya parity tests and the torch images (embed, system1), which are heavy;
- the DB-backed integration tests and e2e, which need a running stack;
- web tests (none exist) and a web image (no Dockerfile);
- dependency scanning.
