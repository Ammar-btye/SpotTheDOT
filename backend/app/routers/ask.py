"""POST /api/v1/ask: proxy to the orchestrator's /v1/ask (bounded read-only MCP tool loop over the System 2 model).
Only with ORCHESTRATOR_URL set (docs/backend-services-contract.md "Orchestrator path")."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..deps import Services, current_request_id, get_services
from ..schemas.flags import AskIn
from ..services.http import ServiceUnavailable

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("")
async def ask(body: AskIn, svc: Services = Depends(get_services)):
    """Free-text question answered by the System 2 model with at most 4 read-only MCP tool calls (manual, policy,
    similar incidents, flag context), with citations. The orchestrator's response is returned unchanged
    (`mode` = tools | retrieval_fallback | no_model | no_context). 503 when the orchestrator is unset or down."""
    rid = current_request_id()
    if not svc.orchestrator.configured:
        return JSONResponse(status_code=503, content={
            "error": "orchestrator_unset", "detail": "ORCHESTRATOR_URL is not set on the backend", "request_id": rid})
    try:
        return await svc.orchestrator.ask({**body.model_dump(exclude_none=True), "request_id": rid}, rid)
    except ServiceUnavailable as exc:
        return JSONResponse(status_code=503, content={"error": "orchestrator_unavailable", "detail": exc.reason,
                                                      "request_id": rid})
