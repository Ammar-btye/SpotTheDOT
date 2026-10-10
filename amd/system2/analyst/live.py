"""Live /v1/assess: the checked pipeline behind the HTTP API (Phase 3, SRV-01/SRV-03).

The API stays a stub until SYSTEM2_LLAMA_URL is set (assessor_from_env returns None, so the stub path and its tests
are untouched). When it is set, LiveAssessor runs the same run_pipeline the offline eval harness scores: at most
two LlamaGenerator attempts inside one 15 s deadline, then the checked template (path 'fallback', model
'template'), so the live endpoint can never return an unchecked model answer. Insufficient packets short-circuit
before any generation. to_response() maps an AssessmentRun to the flat BackendAssessResponse exactly the way
evaluation._public does, so the numbers the backend logs to app.model_calls (model, latency_ms, tokens_per_sec)
are the same fields the eval measured.

The entity catalog is loaded once at construction (PipelineConfig.catalog), never per request. Configuration
errors become RuntimeError with the URL shown only through evaluation.endpoint() (no credentials or query); no
message here ever contains the X-API-Key. This module does not print.
"""
from __future__ import annotations

import os
from typing import Mapping, Optional, Tuple

from .backend_contract import BackendAssessRequest, BackendAssessResponse
from .evaluation import endpoint
from .grounding import default_catalog
from .packet import normalize_packet
from .pipeline import AssessmentRun, PipelineConfig, run_pipeline

DEADLINE_S = 15.0   # live-explain p95 target (PROJECT constraint); shared by both attempts
URL_ENV, MODEL_ENV = 'SYSTEM2_LLAMA_URL', 'SYSTEM2_MODEL'


def to_response(run: AssessmentRun, flag_id: int) -> BackendAssessResponse:
    """Flat public response for one pipeline run; a validation failure here is a bug and raises."""
    public = dict(run.assessment, flag_id=flag_id, model=run.model, latency_ms=run.latency_ms,
                  tokens_per_sec=run.tokens_per_sec, path=run.path)
    return BackendAssessResponse.model_validate(public)


class LiveAssessor:
    """assess(body) -> (response, cache_status) through run_pipeline with `generator` (e.g. LlamaGenerator)."""

    def __init__(self, generator, model: str, config: Optional[PipelineConfig] = None, cache=None):
        self.generator, self.model, self.cache = generator, model, cache
        self.config = config if config is not None else PipelineConfig(deadline_s=DEADLINE_S, catalog=default_catalog())

    def __repr__(self):  # never shows a key: LlamaGenerator's repr is endpoint + model only
        return 'LiveAssessor(%r, model=%r)' % (self.generator, self.model)

    def assess(self, body, refresh: bool = False) -> Tuple[BackendAssessResponse, str]:
        """ValueError for malformed consumed values (the API maps it to 422) before any generation."""
        body = body if isinstance(body, BackendAssessRequest) else BackendAssessRequest.model_validate(body)
        prepared = normalize_packet(body)
        run = run_pipeline(body, self.generator, self.config)
        return to_response(run, prepared.flag_id), 'off'


def assessor_from_env(environ: Mapping[str, str] = os.environ) -> Optional[LiveAssessor]:
    """None (stub) when SYSTEM2_LLAMA_URL is unset or blank; RuntimeError on an incomplete or unusable live config."""
    url = (environ.get(URL_ENV) or '').strip()
    if not url:
        return None
    model = (environ.get(MODEL_ENV) or '').strip()
    if not model:
        raise RuntimeError('%s is set but %s is empty; set the served model name (e.g. qwen3.5-9b-q4km)'
                           % (URL_ENV, MODEL_ENV))
    from .generation import LlamaGenerator   # deferred: stub mode never loads the few-shots
    try:
        generator = LlamaGenerator(url, model=model)
        return LiveAssessor(generator, model)
    except (ValueError, OSError) as exc:
        raise RuntimeError('live System 2 config unusable (%s %s): %s'
                           % (URL_ENV, endpoint(url), str(exc).splitlines()[0] if str(exc) else type(exc).__name__)
                           ) from None
