"""Live /v1/assess: the checked pipeline behind the HTTP API, plus the explanation cache (Phase 3, SRV-01..03).

The API stays a stub until SYSTEM2_LLAMA_URL is set (assessor_from_env returns None, so the stub path and its tests
are untouched). When it is set, LiveAssessor runs the same run_pipeline the offline eval harness scores: at most
two LlamaGenerator attempts inside one 15 s deadline, then the checked template (path 'fallback', model
'template'), so the live endpoint can never return an unchecked model answer. Insufficient packets short-circuit
before any generation. to_response() maps an AssessmentRun to the flat BackendAssessResponse exactly the way
evaluation._public does, so the numbers the backend logs to app.model_calls (model, latency_ms, tokens_per_sec)
are the same fields the eval measured.

Cache (SRV-02): one JSON file per key (flag_id, packet_hash, model, prompt_ver). packet_hash is
evaluation.packet_hash, the same hash the eval harness gates on, so a changed fact regenerates; prompt_ver folds in
the system prompt + few-shot pool hash, so a prompt change regenerates. File names are the sha256 of the canonical
key, never caller strings (no path traversal). Only llm/retry results are stored (fallback and insufficient_context
stay non-final, like the backend's TEMPLATE rows), and a stored entry is served only after it re-validates and
re-passes check_assessment against the current packet; anything else is a miss and is overwritten. The API and
scripts/precompute.py share this one module, so they cannot disagree on the key. Cached explanations never feed
prompts or eval datasets (prompts.py and evaluation.py do not read the cache).

The entity catalog is loaded once at construction (PipelineConfig.catalog), never per request. Configuration
errors become RuntimeError with the URL shown only through evaluation.endpoint() (no credentials or query); no
message here ever contains the X-API-Key. This module does not print.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Mapping, Optional, Tuple

from pydantic import ValidationError

from .backend_contract import MODEL_PATHS, BackendAssessRequest, BackendAssessResponse
from .evaluation import endpoint, packet_hash
from .grounding import EntityCatalog, GENERATION_FIELDS, check_assessment, default_catalog
from .packet import PreparedPacket, normalize_packet
from .paths import repo_root
from .pipeline import AssessmentRun, PipelineConfig, run_pipeline
from .prompts import PROMPT_VERSION, prompt_identity

DEADLINE_S = 15.0   # live-explain p95 target (PROJECT constraint); shared by both attempts
URL_ENV, MODEL_ENV, CACHE_ENV = 'SYSTEM2_LLAMA_URL', 'SYSTEM2_MODEL', 'SYSTEM2_CACHE_DIR'
KEY_FIELDS = ('flag_id', 'packet_hash', 'model', 'prompt_ver')


def to_response(run: AssessmentRun, flag_id: int) -> BackendAssessResponse:
    """Flat public response for one pipeline run; a validation failure here is a bug and raises."""
    public = dict(run.assessment, flag_id=flag_id, model=run.model, latency_ms=run.latency_ms,
                  tokens_per_sec=run.tokens_per_sec, path=run.path)
    return BackendAssessResponse.model_validate(public)


# ── cache ────────────────────────────────────────────────────────────────────────────────────

def cache_key(flag_id: int, packet_hash: str, model: str, prompt_ver: str) -> str:
    """sha256 hex of the canonical key JSON; also the cache file stem."""
    fields = {'flag_id': flag_id, 'packet_hash': packet_hash, 'model': model, 'prompt_ver': prompt_ver}
    raw = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def prompt_version(generator) -> str:
    """PROMPT_VERSION plus the first 16 hex of the system prompt + few-shot pool hash when the generator has one."""
    examples = getattr(generator, 'examples', None)
    if examples is None:
        return PROMPT_VERSION
    return '%s:%s' % (PROMPT_VERSION, prompt_identity(examples)['prompt_sha256'][:16])


def cache_dir_from_env(environ: Mapping[str, str] = os.environ) -> Optional[Path]:
    """SYSTEM2_CACHE_DIR, else amd/system2/cache in a checkout, else None (the image has no writable default)."""
    env = (environ.get(CACHE_ENV) or '').strip()
    if env:
        return Path(env)
    root = repo_root()
    return root / 'amd' / 'system2' / 'cache' if root is not None else None


class ExplanationCache:
    """File cache of checked llm/retry responses; see the module docstring for what is stored and served."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def path(self, key_fields: dict) -> Path:
        return self.root / ('%s.json' % cache_key(*(key_fields[k] for k in KEY_FIELDS)))

    def get(self, key_fields: dict, prepared: PreparedPacket,
            catalog: Optional[EntityCatalog] = None) -> Optional[BackendAssessResponse]:
        """The stored response, or None for missing, unreadable, mismatched, invalid or no-longer-grounded entries."""
        try:
            with open(self.path(key_fields), encoding='utf-8') as f:
                entry = json.load(f)
        except (OSError, ValueError):
            return None
        if not isinstance(entry, dict) or entry.get('key') != {k: key_fields[k] for k in KEY_FIELDS}:
            return None
        try:
            resp = BackendAssessResponse.model_validate(entry.get('response'))
        except ValidationError:
            return None
        if resp.flag_id != prepared.flag_id or resp.path not in MODEL_PATHS:
            return None
        assessment = {k: v for k, v in resp.model_dump(mode='json').items() if k in GENERATION_FIELDS}
        if check_assessment(assessment, prepared, catalog):
            return None
        return resp

    def put(self, key_fields: dict, response: BackendAssessResponse) -> bool:
        """Atomically store an llm/retry response; False (never raises) for other paths or an unwritable dir."""
        if response.path not in MODEL_PATHS:
            return False
        entry = {'key': {k: key_fields[k] for k in KEY_FIELDS}, 'response': response.model_dump(mode='json'),
                 'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
        target, tmp = self.path(key_fields), None
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix='.tmp-', suffix='.json', dir=self.root)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
            os.replace(tmp, target)
            return True
        except OSError:
            if tmp is not None:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            return False


# ── assessor ─────────────────────────────────────────────────────────────────────────────────

class LiveAssessor:
    """assess(body) -> (response, cache_status) through run_pipeline with `generator` (e.g. LlamaGenerator)."""

    def __init__(self, generator, model: str, config: Optional[PipelineConfig] = None,
                 cache: Optional[ExplanationCache] = None):
        self.generator, self.model, self.cache = generator, model, cache
        self.config = config if config is not None else PipelineConfig(deadline_s=DEADLINE_S, catalog=default_catalog())
        self.prompt_ver = prompt_version(generator)

    def __repr__(self):  # never shows a key: LlamaGenerator's repr is endpoint + model only
        return 'LiveAssessor(%r, model=%r)' % (self.generator, self.model)

    def key_fields(self, prepared: PreparedPacket) -> dict:
        return {'flag_id': prepared.flag_id, 'packet_hash': packet_hash(prepared), 'model': self.model,
                'prompt_ver': self.prompt_ver}

    def assess_detail(self, body, refresh: bool = False) -> Tuple[BackendAssessResponse, str, bool]:
        """(response, 'hit'|'miss'|'off', stored); ValueError for malformed consumed values before any generation."""
        body = body if isinstance(body, BackendAssessRequest) else BackendAssessRequest.model_validate(body)
        prepared = normalize_packet(body)
        key = self.key_fields(prepared) if self.cache is not None else None
        if key is not None and not refresh:
            cached = self.cache.get(key, prepared, self.config.catalog)
            if cached is not None:
                return cached, 'hit', True
        response = to_response(run_pipeline(body, self.generator, self.config), prepared.flag_id)
        if key is None:
            return response, 'off', False
        return response, 'miss', self.cache.put(key, response)

    def assess(self, body, refresh: bool = False) -> Tuple[BackendAssessResponse, str]:
        response, status, _ = self.assess_detail(body, refresh)
        return response, status


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
    cache_dir = cache_dir_from_env(environ)
    try:
        generator = LlamaGenerator(url, model=model)
        return LiveAssessor(generator, model, cache=ExplanationCache(cache_dir) if cache_dir is not None else None)
    except (ValueError, OSError) as exc:
        raise RuntimeError('live System 2 config unusable (%s %s): %s'
                           % (URL_ENV, endpoint(url), str(exc).splitlines()[0] if str(exc) else type(exc).__name__)
                           ) from None
