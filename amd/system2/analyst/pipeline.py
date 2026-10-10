"""Checked generation with one bounded retry and the shared checked template as fallback (offline only).

run_pipeline(request, generator, config) normalizes the packet and short-circuits insufficient packets to
the template without calling the generator. Otherwise it makes at most two generation attempts: the first
attempt's sanitized errors enter the second call, with the same evidence. Every failure kind — transport,
deadline, oversized body, truncation (finish_reason 'length'), JSON parse, schema or grounding — counts as
an attempt. A model output is accepted only when check_assessment() finds nothing AND it passes the strict
generation model (generation.GeneratedAssessment: claim/answer lengths, claim and ID counts), so the bounds never
depend on the server honouring the JSON-schema grammar; a strict-model failure is a 'schema' rejection.
After two failures (or when the deadline leaves no time) the result is template_assessment(),
checked by the same checker and labelled path 'fallback' / model 'template' — never LLM success. If no
template claim passes the checker, the result is an explicit insufficient_context MANUAL_REVIEW.

Generator protocol: generator(packet, errors, timeout_s=...) -> Generation, raising GenerationError (or
TimeoutError/OSError) on transport failure. `packet` is a private copy; `errors` is () or a tuple of
single-line strings from describe_errors(). The checks are mechanical consistency checks; an accepted
output is not certified as entailed by its evidence or as safe for autonomous robot operation.
Not wired into the live API in this phase.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import math
import re
import time
from typing import Callable, Optional, Tuple

from pydantic import ValidationError

from .backend_contract import BackendAssessRequest
from .grounding import (EntityCatalog, GroundingError, _clip, _err, check_assessment, default_catalog,
                        describe_errors)
from .packet import PreparedPacket, normalize_packet
from .template import template_assessment

PATHS = ('llm', 'retry', 'fallback', 'insufficient_context')
MAX_ATTEMPTS = 2
INSUFFICIENT_ANSWER = 'Insufficient supplied context; request manual review.'
# keyword, then `=`/`:` (optionally inside JSON/Python quotes) or whitespace, then any auth scheme word, then the value
SECRET_RE = re.compile(r'(?i)\b(bearer|basic|digest|x-api-key|api[-_ ]?key|authorization|token|secret|password)\b'
                       r'(["\']?\s*[:=]\s*["\']?|\s+)((?:bearer|basic|digest|token)\s+)?[^\s,;&"\'}]+')
URL_AUTH_RE = re.compile(r'(?i)(//)[^/\s@]+@')
QUERY_RE = re.compile(r'(?i)([?&](?:key|api_key|apikey|token|access_token|secret)=)[^&\s]+')


class GenerationError(Exception):
    """Transport-level generator failure: kind is a short label (http, timeout, ...)."""

    def __init__(self, kind: str, detail: str = ''):
        super().__init__('%s: %s' % (kind, detail))
        self.kind, self.detail = kind, detail


@dataclass(frozen=True)
class Generation:
    text: str
    model: str
    finish_reason: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    tokens_per_sec: Optional[float] = None


@dataclass(frozen=True)
class PipelineConfig:
    deadline_s: float = 15.0          # total generation budget; matches the 15 s p95 live-explain target
    max_response_bytes: int = 65536   # completion bodies above this are rejected unparsed
    catalog: Optional[EntityCatalog] = None
    clock: Callable[[], float] = time.monotonic


@dataclass(frozen=True)
class Attempt:
    index: int
    status: str  # accepted | rejected | parse_error | truncated | oversized | transport_error | timeout
    errors: Tuple[GroundingError, ...] = ()
    detail: str = ''
    latency_ms: int = 0
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    tokens_per_sec: Optional[float] = None
    response_bytes: Optional[int] = None

    def to_dict(self) -> dict:
        return {'index': self.index, 'status': self.status, 'errors': [e.to_dict() for e in self.errors],
                'detail': self.detail, 'latency_ms': self.latency_ms, 'model': self.model,
                'finish_reason': self.finish_reason, 'prompt_tokens': self.prompt_tokens,
                'completion_tokens': self.completion_tokens, 'tokens_per_sec': self.tokens_per_sec,
                'response_bytes': self.response_bytes}


@dataclass(frozen=True)
class AssessmentRun:
    """Final six-field assessment plus metadata; raw per-attempt results are kept in `attempts`."""
    _assessment: str
    model: str
    path: str
    latency_ms: int
    tokens_per_sec: Optional[float]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    attempts: Tuple[Attempt, ...]
    final_errors: Tuple[GroundingError, ...] = ()
    template_errors: Tuple[GroundingError, ...] = field(default=())

    @property
    def assessment(self) -> dict:
        return json.loads(self._assessment)

    def to_dict(self) -> dict:
        return {'assessment': self.assessment, 'model': self.model, 'path': self.path,
                'latency_ms': self.latency_ms, 'tokens_per_sec': self.tokens_per_sec,
                'prompt_tokens': self.prompt_tokens, 'completion_tokens': self.completion_tokens,
                'attempts': [a.to_dict() for a in self.attempts],
                'final_errors': [e.to_dict() for e in self.final_errors],
                'template_errors': [e.to_dict() for e in self.template_errors]}


def redact(text: str) -> str:
    text = SECRET_RE.sub(lambda m: '%s=[REDACTED]' % m.group(1), text)
    text = URL_AUTH_RE.sub(r'\1[REDACTED]@', text)
    return _clip(QUERY_RE.sub(r'\1[REDACTED]', text), 160)


def _count(v) -> Optional[int]:
    return v if type(v) is int and v >= 0 else None


def _rate(v) -> Optional[float]:
    return float(v) if type(v) in (int, float) and math.isfinite(v) and v >= 0 else None


def _ms(seconds: float) -> int:
    return max(0, int(round(seconds * 1000)))


def _reject_constant(name):
    raise ValueError('non-finite JSON constant %s' % name)


def _unique_object(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate JSON key')
    return dict(pairs)


def _parse(text: str):
    return json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_unique_object)


def _ordered(candidate: dict) -> dict:
    return {k: candidate[k] for k in ('evidence', 'answer', 'question', 'recommended_action', 'confidence',
                                      'insufficient_context')}


def _strict_errors(candidate, prepared: PreparedPacket) -> Tuple[GroundingError, ...]:
    """() when the candidate passes the strict generation model; else one 'schema' error naming the first fault."""
    from .generation import validate_generated  # deferred: generation imports this module
    try:
        validate_generated(candidate, prepared)
    except ValidationError as exc:
        e = exc.errors()[0]
        where = '.'.join(str(x) for x in e['loc']) or 'candidate'
        return (_err('schema', 'candidate', None, '%s: %s' % (where, e['msg'])),)
    except ValueError as exc:
        return (_err('schema', 'candidate', None, (str(exc).splitlines() or ['generation model'])[0]),)
    return ()


def _attempt(index, generator, prepared, errors, config, start, catalog) -> Tuple[Attempt, Optional[dict]]:
    clock = config.clock
    t0 = clock()
    remaining = config.deadline_s - (t0 - start)
    packet = replace(prepared, content=dict(prepared.content))  # generator cannot alter checked evidence
    try:
        g = generator(packet, errors, timeout_s=remaining)
    except GenerationError as exc:
        status = 'timeout' if exc.kind == 'timeout' else 'transport_error'
        return Attempt(index, status, detail=redact('%s %s' % (exc.kind, exc.detail)),
                       latency_ms=_ms(clock() - t0)), None
    except (TimeoutError, OSError) as exc:
        status = 'timeout' if isinstance(exc, TimeoutError) else 'transport_error'
        return Attempt(index, status, detail=redact(type(exc).__name__), latency_ms=_ms(clock() - t0)), None
    if not isinstance(g, Generation):
        raise TypeError('generator must return Generation')
    t1 = clock()
    text = g.text if isinstance(g.text, str) else ''
    size = len(text.encode('utf-8'))
    meta = dict(latency_ms=_ms(t1 - t0), model=_clip(g.model) if isinstance(g.model, str) and g.model.strip() else None,
                finish_reason=_clip(g.finish_reason, 32) if isinstance(g.finish_reason, str) else None,
                prompt_tokens=_count(g.prompt_tokens), completion_tokens=_count(g.completion_tokens),
                tokens_per_sec=_rate(g.tokens_per_sec), response_bytes=size)
    if t1 - start > config.deadline_s:
        return Attempt(index, 'timeout', detail='deadline exceeded', **meta), None
    if size > config.max_response_bytes:
        return Attempt(index, 'oversized', detail='response over %d bytes' % config.max_response_bytes, **meta), None
    if meta['finish_reason'] == 'length':
        return Attempt(index, 'truncated', detail='completion hit the token limit', **meta), None
    try:
        candidate = _parse(text)
    except ValueError as exc:  # json.JSONDecodeError, duplicate keys, NaN/Infinity
        return Attempt(index, 'parse_error', detail=redact(str(exc)), **meta), None
    found = check_assessment(candidate, prepared, catalog) or _strict_errors(candidate, prepared)
    if found:
        return Attempt(index, 'rejected', errors=found, **meta), None
    return Attempt(index, 'accepted', **meta), _ordered(candidate)


def _retry_errors(a: Attempt) -> Tuple[str, ...]:
    if a.errors:
        return describe_errors(a.errors)
    return ('response: %s (return exactly one complete JSON object matching the schema, citing only packet IDs)'
            % a.status,)


def _template(prepared: PreparedPacket, catalog):
    """Checked template; failing claims are dropped; nothing safe left → explicit manual review."""
    t = template_assessment(prepared)
    first = check_assessment(t, prepared, catalog)
    if not first:
        return t, 'insufficient_context' if prepared.insufficient_context else 'fallback', (), ()
    bad = {e.claim for e in first if e.field == 'evidence' and e.claim is not None}
    kept = [e for i, e in enumerate(t['evidence']) if i not in bad]
    if kept and not prepared.insufficient_context:
        t2 = dict(t, evidence=kept, answer=' '.join(e['claim'] for e in kept))
        second = check_assessment(t2, prepared, catalog)
        if not second:
            return t2, 'fallback', (), first
    safe = {'evidence': [], 'answer': INSUFFICIENT_ANSWER, 'question': prepared.question,
            'recommended_action': 'MANUAL_REVIEW', 'confidence': 'low', 'insufficient_context': True}
    return safe, 'insufficient_context', first, first


def run_pipeline(request, generator, config: Optional[PipelineConfig] = None) -> AssessmentRun:
    config = config or PipelineConfig()
    catalog = config.catalog if config.catalog is not None else default_catalog()
    body = request if isinstance(request, BackendAssessRequest) else BackendAssessRequest.model_validate(request)
    prepared = normalize_packet(body)
    start = config.clock()
    attempts, accepted, errors = [], None, ()
    if not prepared.insufficient_context:
        for index in range(1, MAX_ATTEMPTS + 1):
            if config.clock() - start >= config.deadline_s:
                break  # no budget left: never start an attempt that cannot finish in time
            a, accepted = _attempt(index, generator, prepared, errors, config, start, catalog)
            attempts.append(a)
            if accepted is not None:
                break
            errors = _retry_errors(a)
    if accepted is not None:
        final, path, model, final_errors, template_errors = accepted, PATHS[len(attempts) - 1], attempts[-1].model, (), ()
        rate = attempts[-1].tokens_per_sec
    else:
        final, path, final_errors, template_errors = _template(prepared, catalog)
        model, rate = 'template', None
    prompt = [a.prompt_tokens for a in attempts if a.prompt_tokens is not None]
    completion = [a.completion_tokens for a in attempts if a.completion_tokens is not None]
    return AssessmentRun(json.dumps(final, ensure_ascii=False), model or 'unknown', path,
                         _ms(config.clock() - start), rate, sum(prompt) if prompt else None,
                         sum(completion) if completion else None, tuple(attempts), final_errors, template_errors)
