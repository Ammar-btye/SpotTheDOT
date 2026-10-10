"""One reproducible evaluation harness: the template baseline and any served model on the same approved packets.

Both runners take the identical approved saved case (analyst.dataset) as a fresh BackendAssessRequest, normalize it
with the shared normalize_packet, and finish in the same checker. TemplateRunner calls the pipeline's checked
template (the exact function run_pipeline uses for fallback) without generation; ModelRunner calls run_pipeline with
a generator such as LlamaGenerator. evaluate_cases() hashes the normalized packet each runner saw (and every packet
actually handed to the generator) and raises ValueError unless all runners saw the same packet, so no baseline-only
data path can exist.

Per case it keeps the raw first model attempt apart from the final output: first-attempt parse/schema/citation/
numeric/name checks come from that attempt's own checker errors; final checks re-run check_assessment on the final
assessment, and the flat public response is validated with BackendAssessResponse. A fallback is the checked
template, labelled model 'template', and never counts as model success.

Metrics are mechanical consistency with the cited packet content, never entailment or correctness. Rates are
{value, count, denominator}; an empty denominator gives value null with count 0 (never NaN). Failed, timed-out and
fallback cases stay in their denominators. Action agreement with the validator's suggested_action (preserved from
the request before any run) is reported as agreement, not action quality. Action quality is scored only against an
independent case reference {expected_action, source}, which lives outside the request and never reaches a prompt.
Latency quantiles use the nearest-rank method on per-case latency in milliseconds, including retry and fallback.

The approved dataset holds development kit packets from training missions only (synthetic kit data, few-shots from
the same pool with the current case excluded), so scope.headline_eligible is always false. Measured timings vary
between runs; identity (dataset, selection, config, prompt, entity catalog source and hash, code revision) and
outcomes from a deterministic runner do not. No model or GPU is touched here; measurements are whatever endpoint
the caller points the model runner at.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import random
import subprocess
import tempfile
import time
from typing import Dict, List, Optional, Sequence, Tuple
import urllib.parse

from pydantic import ValidationError

from .backend_contract import BackendAction, BackendAssessRequest, BackendAssessResponse
from .dataset import SPLITS, SavedCase, content_hash, validate_dataset
from .grounding import EntityCatalog, check_assessment, default_catalog
from .packet import PreparedPacket, normalize_packet
from .paths import repo_root
from .pipeline import AssessmentRun, PipelineConfig, _template, run_pipeline

HARNESS_VERSION = 'system2-eval-2026-10-10.1'
ROOT = Path(__file__).resolve().parents[1]       # amd/system2 (/app in the image)
REPO = repo_root()                               # None outside a checkout: code revision is then null
DEFAULT_DATASET = ROOT / 'data' / 'dev_packets.json'
DEFAULT_SEED = 20261010
GROUNDING_LABEL = 'mechanical consistency with cited packet content (not entailment, not correctness)'
SCOPE_NOTE = ('Approved development kit packets from training missions only (synthetic kit data, few-shots drawn from '
              'the same pool with the current case excluded). Not held-out and not independent real-world '
              'observations; never a headline number.')
PATHS = ('llm', 'retry', 'fallback', 'insufficient_context')
CHECKS = ('schema_valid', 'citation_valid', 'numeric_consistent', 'name_consistent')
# Checker error codes by metric; an unknown code fails the schema check (fail closed).
SCHEMA_CODES = frozenset({'schema', 'empty_evidence', 'empty_claim', 'empty_ids', 'empty_answer', 'question_mismatch',
                          'unauthorized_action', 'insufficient_mismatch', 'insufficient_inconsistent'})
CITATION_CODES = frozenset({'unknown_id', 'duplicate_id'})
NUMERIC_CODES = frozenset({'nonfinite_number', 'ungrounded_number', 'unit_mismatch', 'unsupported_number',
                           'ungrounded_time'})
NAME_CODES = frozenset({'ungrounded_entity', 'ungrounded_identifier'})
KNOWN_CODES = SCHEMA_CODES | CITATION_CODES | NUMERIC_CODES | NAME_CODES
# A reference from any of these is the validator's own view, so it can only ever measure agreement.
VALIDATOR_SOURCES = frozenset({'validator', 'policy', 'system1', 'suggested_action', 'template', 'model'})


@dataclass(frozen=True)
class EvalConfig:
    seed: int = DEFAULT_SEED
    limit: Optional[int] = None
    deadline_s: float = 15.0      # run_pipeline budget per case (15 s p95 live-explain target)
    timeout_s: float = 15.0       # per HTTP call; the smaller of this and the remaining deadline wins
    max_tokens: int = 350
    model_url: Optional[str] = None
    model: Optional[str] = None
    label: str = 'unlabelled'

    def identity(self) -> dict:
        return {'seed': self.seed, 'limit': self.limit, 'deadline_s': self.deadline_s, 'timeout_s': self.timeout_s,
                'max_tokens': self.max_tokens, 'model_url': endpoint(self.model_url), 'model': self.model}


@dataclass(frozen=True)
class EvalDataset:
    cases: Tuple[SavedCase, ...]
    manifest: dict
    file_sha256: str
    path: str
    split: str = 'train'


@dataclass(frozen=True)
class RunOutcome:
    run: AssessmentRun
    packet_hash: str
    sent_packet_hashes: Tuple[str, ...] = ()


# ── dataset, references, identity ────────────────────────────────────────────────────────────

def load_eval_dataset(path) -> EvalDataset:
    """Approved dataset only: manifest required, full provenance validation, valid references; ValueError otherwise."""
    try:
        raw = Path(path).read_bytes()
        value = json.loads(raw.decode('utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError('cannot read saved dataset') from exc
    if not isinstance(value, dict) or not isinstance(value.get('manifest'), dict):
        raise ValueError('evaluation requires an approved dataset with its manifest')
    split = value['manifest'].get('split', 'train')    # absent = the Phase 2 training manifest
    if split not in SPLITS:
        raise ValueError('unknown dataset split')
    cases = validate_dataset(value, split)   # empty, leakage, future evidence, split and manifest mismatch fail here
    for c in cases:
        reference_action(c.reference)
    return EvalDataset(cases, value['manifest'], hashlib.sha256(raw).hexdigest(), str(path), split)


def reference_action(reference) -> Optional[str]:
    """Independent expected action or None; ValueError for malformed or validator-derived references."""
    if reference is None:
        return None
    if not isinstance(reference, dict) or set(reference) != {'expected_action', 'source'}:
        raise ValueError('reference must be {expected_action, source}')
    action, source = reference['expected_action'], reference['source']
    if not isinstance(action, str) or action not in BackendAction._value2member_map_:
        raise ValueError('reference expected_action is not a known action')
    if not isinstance(source, str) or not source.strip() or source.strip().lower() in VALIDATOR_SOURCES:
        raise ValueError('reference source must be independent of the validator')
    return action


def select_cases(cases: Sequence[SavedCase], limit: Optional[int], seed: int) -> Tuple[SavedCase, ...]:
    """All cases, or a seeded sample of `limit` cases, always in case_id order."""
    chosen = list(cases) if limit is None or limit >= len(cases) else random.Random(seed).sample(list(cases), limit)
    return tuple(sorted(chosen, key=lambda c: c.case_id))


def request_hash(case: SavedCase) -> str:
    return content_hash(case.to_dict()['request'])


def packet_hash(p: PreparedPacket) -> str:
    """Identity of the normalized evidence map and everything else a runner may use."""
    return content_hash({'flag_id': p.flag_id, 'question': p.question, 'content': p.content,
                         'allowed_actions': list(p.allowed_actions), 'suggested_action': p.suggested_action,
                         'insufficient_context': p.insufficient_context})


def endpoint(url: Optional[str]) -> Optional[str]:
    """scheme://host[:port]/path without credentials or query."""
    if not url:
        return None
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ''
    netloc = ('[%s]' % host if ':' in host else host) + (':%d' % parts.port if parts.port else '')
    return urllib.parse.urlunsplit((parts.scheme, netloc, parts.path.rstrip('/'), '', ''))


def is_loopback(url: Optional[str]) -> Optional[bool]:
    if not url:
        return None
    host = urllib.parse.urlsplit(url).hostname or ''
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def code_revision() -> dict:
    """HEAD commit and whether amd/system2 sources differ from it (results/ excluded); nulls when git is absent."""
    if REPO is None:
        return {'revision': None, 'dirty': None}

    def git(*args):
        return subprocess.run(['git', '-C', str(REPO), *args], capture_output=True, text=True, timeout=10,
                              check=True).stdout
    try:
        revision = git('rev-parse', 'HEAD').strip()
        dirty = bool(git('status', '--porcelain', '--', 'amd/system2', ':!amd/system2/results').strip())
    except (OSError, subprocess.SubprocessError):
        return {'revision': None, 'dirty': None}
    return {'revision': revision or None, 'dirty': dirty}


def catalog_identity(catalog: EntityCatalog) -> dict:
    """Kit source and content hash of the entity catalog the checker grounds names against."""
    entities = [[e.kind, e.key, list(e.aliases)] for e in catalog.entities]
    return {'source': catalog.source, 'entity_count': len(entities), 'content_hash': content_hash(entities)}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


# ── runners ──────────────────────────────────────────────────────────────────────────────────

def _prepare(request) -> PreparedPacket:
    body = request if isinstance(request, BackendAssessRequest) else BackendAssessRequest.model_validate(request)
    return normalize_packet(body)


class TemplateRunner:
    """Checked template baseline: same normalization and checker as run_pipeline's fallback, no generation."""
    name = 'template'
    kind = 'template'

    def run(self, request, config: EvalConfig) -> RunOutcome:
        prepared = _prepare(request)
        t0 = time.monotonic()
        final, path, final_errors, template_errors = _template(prepared, default_catalog())
        latency = max(0, int(round((time.monotonic() - t0) * 1000)))
        run = AssessmentRun(json.dumps(final, ensure_ascii=False), 'template', path, latency, None, None, None, (),
                            final_errors, template_errors)
        return RunOutcome(run, packet_hash(prepared))

    def identity(self, prepared: PreparedPacket) -> Optional[dict]:
        return None


class ModelRunner:
    """run_pipeline with a generator (e.g. LlamaGenerator); records the hash of every packet sent to it."""
    kind = 'model'

    def __init__(self, generator, name: str = 'model'):
        self.generator, self.name = generator, name

    def run(self, request, config: EvalConfig) -> RunOutcome:
        prepared = _prepare(request)
        sent = []

        def recording(packet, errors, timeout_s=None):
            sent.append(packet_hash(packet))
            return self.generator(packet, errors, timeout_s=timeout_s)

        run = run_pipeline(request, recording, PipelineConfig(deadline_s=config.deadline_s))
        return RunOutcome(run, packet_hash(prepared), tuple(sent))

    def identity(self, prepared: PreparedPacket) -> Optional[dict]:
        ident = getattr(self.generator, 'identity', None)
        if ident is None:
            return None
        try:
            return ident(prepared)
        except ValueError as exc:     # too few distinct few-shots: the generator itself fails the same way
            return {'prompt_error': str(exc)[:200]}


# ── per-case scoring ─────────────────────────────────────────────────────────────────────────

def _checks(codes, parsed: bool) -> dict:
    """Cumulative and fail closed: a check passes only for a parsed, schema-valid output without that error class."""
    codes = set(codes)
    schema = parsed and not codes & SCHEMA_CODES and not codes - KNOWN_CODES
    return {'parsed': parsed, 'schema_valid': schema,
            'citation_valid': schema and not codes & CITATION_CODES,
            'numeric_consistent': schema and not codes & NUMERIC_CODES,
            'name_consistent': schema and not codes & NAME_CODES}


def _first_attempt(run: AssessmentRun, kind: str, insufficient: bool) -> Optional[dict]:
    if run.attempts:
        a = run.attempts[0]
        return dict(_checks([e.code for e in a.errors], a.status in ('accepted', 'rejected')),
                    status=a.status, accepted=a.status == 'accepted')
    if kind == 'model' and not insufficient:   # deadline spent before any call: a failed attempt, still counted
        return dict(_checks((), False), status='not_attempted', accepted=False)
    return None


def _public(run: AssessmentRun, flag_id: int) -> Tuple[bool, Optional[str]]:
    public = dict(run.assessment, flag_id=flag_id, model=run.model, latency_ms=run.latency_ms,
                  tokens_per_sec=run.tokens_per_sec, path=run.path)
    try:
        BackendAssessResponse.model_validate(public)
    except ValidationError as exc:
        where = ['.'.join(str(p) for p in e['loc']) or 'response' for e in exc.errors()][:4]
        return False, '%d validation error(s): %s' % (exc.error_count(), ', '.join(where))
    return True, None


def score_case(case: SavedCase, runner, outcome: RunOutcome) -> dict:
    prepared, run = case.prepared, outcome.run
    assessment = run.assessment
    final_errors = check_assessment(assessment, prepared, default_catalog())
    public_valid, public_error = _public(run, prepared.flag_id)
    insufficient = prepared.insufficient_context
    recommended, suggested = assessment['recommended_action'], prepared.suggested_action
    reference = reference_action(case.reference)
    return {
        'runner': runner.name, 'kind': runner.kind, 'case_id': case.case_id, 'category': case.category,
        'mission_id': case.mission_id, 'split': case.split, 'request_hash': request_hash(case),
        'packet_hash': outcome.packet_hash, 'packet_insufficient': insufficient,
        'path': run.path, 'model': run.model, 'latency_ms': run.latency_ms, 'tokens_per_sec': run.tokens_per_sec,
        'prompt_tokens': run.prompt_tokens, 'completion_tokens': run.completion_tokens,
        'attempt_count': len(run.attempts), 'retry': len(run.attempts) >= 2,
        'fallback': runner.kind == 'model' and not insufficient and run.model == 'template',
        'attempts': [a.to_dict() for a in run.attempts],
        'first_attempt': _first_attempt(run, runner.kind, insufficient),
        'final': dict(_checks([e.code for e in final_errors], True), errors=[e.to_dict() for e in final_errors]),
        'public_valid': public_valid, 'public_error': public_error, 'assessment': assessment,
        'action': {'recommended': recommended, 'validator_suggested': suggested,
                   'agrees_with_validator': None if suggested is None else recommended == suggested,
                   'reference_action': reference,
                   'matches_reference': None if reference is None else recommended == reference},
        'prompt': runner.identity(prepared),
    }


# ── aggregation ──────────────────────────────────────────────────────────────────────────────

def rate(count: int, denominator: int) -> dict:
    return {'value': count / denominator if denominator else None, 'count': count, 'denominator': denominator}


def latency_summary(values: Sequence[int]) -> dict:
    """Nearest-rank quantiles (rank = ceil(q * n)) in milliseconds; nulls when there are no cases."""
    v = sorted(values)
    q = (lambda p: v[max(0, math.ceil(p * len(v)) - 1)]) if v else (lambda p: None)
    return {'n': len(v), 'p50': q(0.5), 'p95': q(0.95), 'max': v[-1] if v else None,
            'mean': round(sum(v) / len(v), 3) if v else None, 'method': 'nearest-rank', 'unit': 'ms'}


def _safe_manual_review(r: dict) -> bool:
    a = r['assessment']
    return (r['public_valid'] and r['path'] == 'insufficient_context' and not a['evidence']
            and a['confidence'] == 'low' and a['recommended_action'] == 'MANUAL_REVIEW')


def aggregate(rows: List[dict], kind: str) -> dict:
    suff = [r for r in rows if not r['packet_insufficient']]
    guarded = [r for r in rows if r['packet_insufficient']]
    gen = suff if kind == 'model' else []
    attempts = [a for r in rows for a in r['attempts']]
    prompt = [a['prompt_tokens'] for a in attempts if a['prompt_tokens'] is not None]
    completion = [a['completion_tokens'] for a in attempts if a['completion_tokens'] is not None]
    speeds = [a['tokens_per_sec'] for a in attempts if a['tokens_per_sec'] is not None]
    refs = [r for r in rows if r['action']['reference_action'] is not None]
    hinted = [r for r in rows if r['action']['validator_suggested'] is not None]
    n = len(rows)
    return {
        'kind': kind, 'cases': n, 'sufficient_cases': len(suff),
        'public_response_valid': rate(sum(r['public_valid'] for r in rows), n),
        'guarded_insufficient': {'cases': len(guarded), 'safe_manual_review': rate(
            sum(_safe_manual_review(r) for r in guarded), len(guarded))},
        'first_attempt': {k: rate(sum(r['first_attempt'][k] for r in gen), len(gen))
                          for k in ('parsed',) + CHECKS + ('accepted',)},
        'final': {k: rate(sum(r['final'][k] for r in suff), len(suff)) for k in CHECKS},
        'final_insufficient_among_sufficient': rate(sum(r['path'] == 'insufficient_context' for r in suff), len(suff)),
        'generation': {
            'cases': len(gen), 'attempted_outputs': len(attempts),
            'model_accepted': rate(sum(r['path'] in ('llm', 'retry') for r in gen), len(gen)),
            'first_attempt_accepted': rate(sum(r['path'] == 'llm' for r in gen), len(gen)),
            'retry': rate(sum(r['retry'] for r in gen), len(gen)),
            'fallback': rate(sum(r['fallback'] for r in gen), len(gen)),
            'attempt_statuses': dict(sorted(Counter(a['status'] for a in attempts).items()))},
        'paths': {p: sum(r['path'] == p for r in rows) for p in PATHS},
        'models': dict(sorted(Counter(r['model'] for r in rows).items())),
        'action': {
            'metric_kind': ('agreement_with_validator' if not refs else
                            'action_quality' if len(refs) == n else 'mixed'),
            'reference_origin': 'independent' if refs else 'none',
            'agreement_with_validator': rate(sum(r['action']['agrees_with_validator'] for r in hinted), len(hinted)),
            'action_quality': rate(sum(r['action']['matches_reference'] for r in refs), len(refs))},
        'latency_ms': latency_summary([r['latency_ms'] for r in rows]),
        'tokens': {'attempts_with_usage': sum(a['prompt_tokens'] is not None or a['completion_tokens'] is not None
                                              for a in attempts),
                   'prompt_tokens': sum(prompt) if prompt else None,
                   'completion_tokens': sum(completion) if completion else None,
                   'tokens_per_sec_mean': {'value': round(sum(speeds) / len(speeds), 3) if speeds else None,
                                           'n': len(speeds)}},
    }


def evaluate_cases(cases: Sequence[SavedCase], runners: Sequence, config: EvalConfig) -> dict:
    """Run every runner on every case; ValueError unless all runners saw the identical normalized packet."""
    if not cases:
        raise ValueError('no cases to evaluate')
    names = [r.name for r in runners]
    if not runners or len(set(names)) != len(names):
        raise ValueError('runner names must be unique and nonempty')
    expected = {c.case_id: (request_hash(c), packet_hash(c.prepared)) for c in cases}
    rows: Dict[str, List[dict]] = {}
    for runner in runners:
        rows[runner.name] = []
        for case in cases:
            outcome = runner.run(case.to_dict()['request'], config)   # a fresh copy; the reference never goes in
            want_request, want_packet = expected[case.case_id]
            if request_hash(case) != want_request:
                raise ValueError('saved request changed during evaluation of %s' % case.case_id)
            if outcome.packet_hash != want_packet or any(h != want_packet for h in outcome.sent_packet_hashes):
                raise ValueError('runner %s saw a different packet for %s' % (runner.name, case.case_id))
            rows[runner.name].append(score_case(case, runner, outcome))
    ids = [c.case_id for c in cases]
    return {'records': [r for name in names for r in rows[name]],
            'runners': {r.name: aggregate(rows[r.name], r.kind) for r in runners},
            'comparison': {'runners': names, 'case_ids': ids, 'packet_hashes_match': True,
                           'packet_set_hash': content_hash([[i, expected[i][1]] for i in ids])}}


# ── run + artifacts ──────────────────────────────────────────────────────────────────────────

def _prompt_identity(records: List[dict]) -> Optional[dict]:
    prompts = [r['prompt'] for r in records if r['prompt']]
    if not prompts:
        return None
    first = prompts[0]
    return {'prompt_version': first.get('prompt_version'),
            'prompt_sha256s': sorted({p['prompt_sha256'] for p in prompts if p.get('prompt_sha256')}),
            'max_tokens': first.get('max_tokens'), 'temperature': first.get('temperature'),
            'thinking': first.get('thinking'),
            'example_case_ids': {r['case_id']: r['prompt'].get('example_case_ids') for r in records if r['prompt']}}


def run_evaluation(dataset: EvalDataset, runners: Sequence, config: EvalConfig) -> dict:
    """Select, evaluate and assemble metrics.json content (records stay under 'records')."""
    selected = select_cases(dataset.cases, config.limit, config.seed)
    started = utc_now()
    result = evaluate_cases(selected, runners, config)
    finished = utc_now()
    identity = {
        'harness_version': HARNESS_VERSION,
        'dataset': {'content_hash': dataset.manifest['content_hash'], 'file_sha256': dataset.file_sha256,
                    'policy_version': dataset.manifest['policy_version'],
                    'holdout_fold': dataset.manifest['holdout_fold'],
                    'holdout_missions': dataset.manifest['holdout_missions'], 'case_count': len(dataset.cases),
                    'selected_case_ids': [c.case_id for c in selected],
                    'splits': sorted({c.split for c in selected}),
                    'packet_set_hash': result['comparison']['packet_set_hash']},
        'runners': [r.name for r in runners],
        'config': config.identity(),
        'prompt': _prompt_identity(result['records']),
        'catalog': catalog_identity(default_catalog()),   # kit edits change name checks; code_revision misses them
        'code': code_revision(),
    }
    identity['identity_hash'] = content_hash(identity)
    model_url = config.model_url if any(r.kind == 'model' for r in runners) else None
    return {
        'identity': identity,
        'scope': {'split': '+'.join(identity['dataset']['splits']), 'headline_eligible': False,
                  'grounding_label': GROUNDING_LABEL, 'note': SCOPE_NOTE},
        'measurement': {'label': config.label,
                        'source': 'http model endpoint + in-process template' if model_url else 'in-process template',
                        'endpoint_loopback': is_loopback(model_url), 'dataset_path': dataset.path,
                        'started_at': started, 'finished_at': finished,
                        'latency_quantile_method': 'nearest-rank', 'latency_unit': 'ms'},
        'runners': result['runners'],
        'comparison': result['comparison'],
        'records': result['records'],
    }


def _fmt(r: dict) -> str:
    return 'n/a (0)' if r['value'] is None else '%d/%d (%.1f%%)' % (r['count'], r['denominator'], 100 * r['value'])


def report(metrics: dict) -> str:
    ident, meas = metrics['identity'], metrics['measurement']
    L = ['# System 2 evaluation: %s' % ', '.join(ident['runners']), '',
         'Dataset `%s` content %s, %d of %d cases, split %s. Label `%s`, %s to %s.' % (
             meas['dataset_path'], ident['dataset']['content_hash'][:12], len(ident['dataset']['selected_case_ids']),
             ident['dataset']['case_count'], metrics['scope']['split'], meas['label'], meas['started_at'],
             meas['finished_at']),
         '', '**Not headline numbers.** %s Grounding = %s.' % (metrics['scope']['note'], GROUNDING_LABEL), '',
         '| metric | %s |' % ' | '.join(metrics['runners']), '|---|%s' % ('---|' * len(metrics['runners']))]
    rows = [('public response valid', lambda a: _fmt(a['public_response_valid'])),
            ('model accepted (llm+retry)', lambda a: _fmt(a['generation']['model_accepted'])),
            ('retry', lambda a: _fmt(a['generation']['retry'])),
            ('fallback to template', lambda a: _fmt(a['generation']['fallback'])),
            ('guarded insufficient: safe manual review',
             lambda a: _fmt(a['guarded_insufficient']['safe_manual_review']))]
    rows += [('first attempt %s' % k, (lambda k: lambda a: _fmt(a['first_attempt'][k]))(k)) for k in CHECKS]
    rows += [('final %s' % k, (lambda k: lambda a: _fmt(a['final'][k]))(k)) for k in CHECKS]
    rows += [('action agreement with validator', lambda a: _fmt(a['action']['agreement_with_validator'])),
             ('action quality (independent refs)', lambda a: _fmt(a['action']['action_quality'])),
             ('latency p50 / p95 ms (nearest-rank)',
              lambda a: '%s / %s' % (a['latency_ms']['p50'], a['latency_ms']['p95']))]
    for label, get in rows:
        L.append('| %s | %s |' % (label, ' | '.join(get(a) for a in metrics['runners'].values())))
    return '\n'.join(L) + '\n'


def write_artifacts(out_dir: Path, metrics: dict) -> None:
    """Serialize everything first, then atomically replace cases.jsonl, report.md and (last) metrics.json.

    Any previous metrics.json is removed before the first replacement, so its presence always means all three files
    come from the same completed run, even when a later write fails (disk full, permissions).
    """
    records = metrics['records']
    summary = {k: v for k, v in metrics.items() if k != 'records'}
    payloads = [
        ('cases.jsonl', ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n'
                                for r in records).encode('utf-8')),
        ('report.md', report(summary).encode('utf-8')),
        ('metrics.json', (json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')),
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'metrics.json').unlink(missing_ok=True)
    for name, data in payloads:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=out_dir, prefix='.' + name + '-', suffix='.tmp', delete=False) as f:
                temporary = Path(f.name)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(temporary, 0o644)    # NamedTemporaryFile creates 0600; artifacts are ordinary readable files
            os.replace(temporary, out_dir / name)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
