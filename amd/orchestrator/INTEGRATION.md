# Orchestrator integration (for the integrator agent)

The orchestrator agent did not edit any of the files below; apply these changes in one commit. Spec:
`docs/orchestrator-contract.md`. Verified: 38 offline tests pass on Python 3.13 (venv) and 3.12 (inside the image);
`docker build amd/orchestrator` builds, the container refuses to start without a key, `/health` is healthy, and it runs as
uid 10001. Two of those tests send the orchestrator's real request into the real System 2 app (stub mode, including
`context.vision`, `context.ocr` and `image_b64`, all accepted) and check the rebuilt Laya events against System 1's
own event schemas.

## 1. `docker-compose.yml`: service block (application section, after `system2`, before `backend`)
```yaml
  # LangGraph orchestrator: /v1/assess (MCP context -> System 1 -> route -> vision -> System 2 -> template) and
  # /v1/ask (System 2 model + read-only MCP tools, <= 4 calls). No DB access. docs/orchestrator-contract.md.
  orchestrator:
    <<: *service
    build: {context: amd/orchestrator}
    image: spot-orchestrator:compose
    profiles: [local, hybrid, neon]
    depends_on:
      mcp: {condition: service_healthy}
      system2: {condition: service_healthy, required: false}
      gateway: {condition: service_healthy, required: false}
      vision: {condition: service_healthy, required: false}
    environment:
      ORCHESTRATOR_API_KEY: ${ORCHESTRATOR_API_KEY:?set ORCHESTRATOR_API_KEY in .env (>= 16 chars)}
      MCP_URL: ${MCP_URL:-http://mcp:8090/mcp}
      MCP_AUTH_TOKEN: ${MCP_AUTH_TOKEN:-}
      GATEWAY_URL: ${GATEWAY_URL:-http://gateway:4000}
      GATEWAY_KEY: ${LITELLM_MASTER_KEY:-}
      VISION_URL: ${VISION_URL:-http://vision:8084}
      VISION_API_KEY: *vision-key                       # same key as the vision service (required since vision.2)
      SYSTEM2_URL: ${SYSTEM2_URL:-http://system2:8083}   # same value the backend uses
      SYSTEM2_API_KEY: ${SYSTEM2_API_KEY:-}
      DEMO_IMAGES: ${DEMO_IMAGES:-0}                     # 1 = pair kit sample images by action_type (pairing "demo")
      ORCH_DEADLINE_S: ${ORCH_DEADLINE_S:-40}            # < backend REQUEST_DEADLINE_S (45) so the backend can store
      ORCH_SYSTEM2_IMAGE_BUDGET_S: ${ORCH_SYSTEM2_IMAGE_BUDGET_S:-28}   # >= System 2 SYSTEM2_IMAGE_DEADLINE_S (25) + checks
      ASK_DEADLINE_S: ${ASK_DEADLINE_S:-30}
      ASK_MAX_TOOL_CALLS: ${ASK_MAX_TOOL_CALLS:-4}
    ports: ["${BIND_ADDR:-127.0.0.1}:8085:8085"]
    volumes: ["./web/public/kit/inspection:/app/demo-images:ro"]
    # Non-root runtime (uid 10001) and healthcheck (/health) come from the image.
```
Validated with `docker compose config` on a scratch copy of the current compose file. **Compose rejects
`depends_on` on an undefined service even with `required: false`**, so keep the `gateway` / `vision` lines only
once those services exist in the file. Without them, the block validates as-is. If those services land under other
compose names, change only the two URLs and `depends_on` keys.
If `${VAR:?}` is too strict for `make up` without a `.env`, use `${ORCHESTRATOR_API_KEY:-}`. The container then
exits with a clear message instead (it never starts open).

In the `backend` service, add:
```yaml
      ORCHESTRATOR_URL: ${ORCHESTRATOR_URL:-}            # set to http://orchestrator:8085 to route /explain via LangGraph
      ORCHESTRATOR_API_KEY: ${ORCHESTRATOR_API_KEY:-}
```
and `orchestrator: {condition: service_healthy, required: false}` under its `depends_on`.

Header table line (after `system2`):
```
# orchestrator 8085 local, hybrid, neon      LangGraph: /v1/assess (context -> Laya -> route -> vision -> System 2 ->
#                                           template) and /v1/ask (bounded MCP tool loop). X-API-Key ORCHESTRATOR_API_KEY.
```

## 2. `.env.example`
```bash
# ── orchestrator (amd/orchestrator, :8085) ──
ORCHESTRATOR_API_KEY=change-me-at-least-16-chars      # X-API-Key for the orchestrator; the backend sends it too
# ORCHESTRATOR_URL=http://orchestrator:8085           # backend: route /flags/{id}/explain through the orchestrator
# DEMO_IMAGES=1                                       # pair kit sample images by action type (pairing "demo")
# ORCH_DEADLINE_S=40                                  # keep below REQUEST_DEADLINE_S
```

## 3. Ports table row (`docs/backend-services-contract.md`, "Services and ports")
```
| Orchestrator (LangGraph: assess + ask graphs) | `amd/orchestrator/` | 8085 | orchestrator agent |
```

## 4. `docs/RUNNING.md`
Service table row:
```
| `orchestrator` | 8085 | local, hybrid, neon | `amd/orchestrator/` | LangGraph. `POST /v1/assess`: MCP context -> System 1 (packet answers, else gateway `system1`) -> route (escalate / P1-P2 / rules / operator image -> full, else short System 1 answer) -> vision (with an image or `DEMO_IMAGES=1`) -> System 2 -> template fallback, all within `ORCH_DEADLINE_S` (40), with a per-node `trace`. `POST /v1/ask`: the System 2 model with the read-only MCP tools, at most 4 calls in 30 s. `X-API-Key: $ORCHESTRATOR_API_KEY` (refuses to start without it). `GET /v1/graph` = mermaid. Non-root, healthcheck from the image. |
```
Section (after "System 2 on 8083"):
````markdown
## Orchestrator on 8085 (LangGraph)
```bash
docker compose up -d --build orchestrator
curl -s localhost:8085/health?deep=true | jq
curl -s -H "X-API-Key: $ORCHESTRATOR_API_KEY" -H 'content-type: application/json' \
  localhost:8085/v1/assess -d '{"flag_id": 1}' | jq '{route, route_reasons, source, answer, trace}'
curl -s -H "X-API-Key: $ORCHESTRATOR_API_KEY" -H 'content-type: application/json' \
  localhost:8085/v1/ask -d '{"question": "How should Spot handle docking at low battery?"}' | jq
curl -s 'localhost:8085/v1/graph?format=text&graph=assess'      # paste into mermaid.live for the demo
```
Native on the AMD box: `cd amd/orchestrator && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
&& .venv/bin/python -m orchestrator` (env as in `amd/orchestrator/README.md`). `/v1/ask` tool calling needs
llama-server started with `--jinja`. Without it, ask degrades to one retrieval step plus an answer from the
retrieved context (`mode: retrieval_fallback`). The backend routes `/flags/{id}/explain` through the orchestrator
only when `ORCHESTRATOR_URL` is set; if it is unset or down, `/explain` uses its existing MCP -> System 2 -> template path.
````

## 5. `Makefile`
```make
PY_ORCH    ?= amd/orchestrator/.venv/bin/python

test-orchestrator: ## orchestrator graph tests (fakes; contract tests vs real System 2 app + System 1 schemas)
	cd amd/orchestrator && .venv/bin/python -m pytest -q -p no:cacheprovider
```
Add `test-orchestrator` to `.PHONY` and to the `test:` prerequisites. Add this line to `venvs:`:
```make
	test -x $(PY_ORCH) || (python3 -m venv amd/orchestrator/.venv && amd/orchestrator/.venv/bin/pip install -r amd/orchestrator/requirements-dev.txt)
```

## 6. Backend change (`backend/`): `/explain` calls the orchestrator when `ORCHESTRATOR_URL` is set
- `backend/app/config.py`: add `orchestrator_url` (`ORCHESTRATOR_URL`, rstrip `/`, empty means None),
  `orchestrator_api_key` (`ORCHESTRATOR_API_KEY`), and `orchestrator_timeout_s` (`ORCHESTRATOR_TIMEOUT_S`, default 45).
- `backend/app/services/system2.py` (or a new `orchestrator.py`): add `OrchestratorClient`, a copy of `System2Client`
  with `name = "orchestrator"`, header `X-API-Key`, `assess(body)` -> `POST /v1/assess`, and `ask(body)` ->
  `POST /v1/ask`, plus its own `Breaker`. Wire it in `deps.py` and pass it to `FlagService(..., orchestrator=...)`.
- `FlagService.explain`, after the cache check and before `_context(...)`:
```python
if self.orchestrator is not None and self.orchestrator.configured:
    try:
        out = await asyncio.wait_for(self.orchestrator.assess(
            {"flag_id": flag_id, "request_id": request_id, "refresh": refresh}, request_id=request_id,
            flag_id=flag_id, action_id=f.get("action_id")), deadline.remaining(reserve))
        if out.get("context_source") != "none" and out.get("answer"):
            result = {k: out.get(k) for k in ("question", "answer", "reasoning", "recommended_action",
                                              "severity_assessment", "confidence", "model", "latency_ms",
                                              "tokens_per_sec", "insufficient_context", "evidence",
                                              "fallback_reason", "source")}
            result["context_source"] = out.get("context_source")
            result["orchestrator"] = {k: out.get(k) for k in ("route", "route_reasons", "trace", "system1",
                                                             "vision", "elapsed_ms")}
            # then the existing store/index tail: state DONE only when source == "system2"
            # (template and system1 answers stay TEMPLATE: not final, never indexed as explanation RAG docs)
            ...
    except (ServiceUnavailable, asyncio.TimeoutError):
        pass   # fall through to the existing MCP -> System 2 -> template path (it has the SQL fallback)
```
  Factor the existing "store + index + cached=False" tail into a helper so both paths share it.
  `context_source == "none"` means the orchestrator could not reach MCP; the existing path then still gets
  its SQL fallback packet.
- `backend/app/schemas/flags.py` `Explanation`: widen `source` to `Literal["system2", "template", "system1"]` (the
  orchestrator also returns `system2_template` since contract orchestrator.2; storing it as `template` is correct), and
  add `orchestrator: Optional[Dict[str, Any]] = None` (route, route_reasons, trace, vision rows/OCR/alert,
  system1). The UI can then show the graph trace and the `V#` vision rows.
- Optional, same change: `POST /api/v1/flags/{id}/explain` takes an optional JSON body
  `{"image_b64", "image_kind"}` and forwards it to the orchestrator (operator upload -> `pairing: "linked"`).
  `POST /api/v1/ask {question, flag_id?}` proxies to the orchestrator's `/v1/ask` (503 when `ORCHESTRATOR_URL` is unset).
- Contract text to add to `docs/backend-services-contract.md`: list the env rows `ORCHESTRATOR_URL` (unset = the
  existing path), `ORCHESTRATOR_API_KEY` and `ORCHESTRATOR_TIMEOUT_S` (45), and add the sentence "When
  ORCHESTRATOR_URL is set, /explain asks the orchestrator first (docs/orchestrator-contract.md) and falls back to the
  existing path when it is down or has no context."
- Backend tests: a fake orchestrator returning `source: system2` gets stored as DONE; `source: system1/template` is
  stored as TEMPLATE; orchestrator down or `context_source: none` takes the old path.

## 7. `research/decisions.md` line (under "Made")
```
- **Orchestrator = LangGraph service on :8085 (2026-10-10).** `/v1/assess` is a fixed graph: MCP context -> Laya -> route (Laya/flag/validator escalate, P1/P2, fired rules or an operator image -> vision + System 2; else a short System 1 answer) -> template fallback, within one deadline. It stays tool-free, so "System 2 does not call tools on /explain" still holds. The tool loop exists only on the new `/v1/ask` chat path: read-only search_*/get_* MCP tools, at most 4 calls in 30 s, which keeps the ≤15 s explain p95 and the grounding checks intact.
```

## 8. Optional: `docs/ARCHITECTURE.md`
Add one box: backend `/explain` -> orchestrator :8085 -> {MCP :8090, gateway :4000 (`system1`, `system2`), vision
:8084, System 2 :8083}. The live diagram is `GET /v1/graph`.
