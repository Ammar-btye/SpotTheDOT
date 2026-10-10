"""Defendable System 2 report: held-out headline rates with mission-level bootstrap CIs (EVAL-01/02/04/05/06).

build_metrics(records, context) is the one pure function behind both a live run (scripts/report.py) and
`report.py --rebuild DIR`. It reads no clock, environment or network: every timestamp, host, label and command comes
from `context`, so the same cases.jsonl always gives the same metrics.json and report.md bytes.

Honesty rules (04-CONTEXT, locked 2026-10-10):
- The headline is computed only on the controlled held-out packets (System 1 fold-2 kit missions, 38 flags in 8
  missions) and is headline-eligible only for the full set. Training-pool development results sit in their own
  section, without CIs, labelled not headline.
- Each headline rate shows value, k/n flags, the number of missions and a 95% CI from a mission-level bootstrap:
  resample whole missions with replacement (random.Random(seed).choices, sorted mission keys, 1,000 resamples, seed
  20261010), skip resamples whose statistic is undefined, then take the 2.5/97.5 percentiles with linear
  interpolation (numpy's default). This mirrors amd/system1/triage/metrics.py bootstrap(), stdlib only. Fewer than
  2 missions gives no CI. Flags within a mission are correlated, so per-flag resampling would understate the width.
- Point values are evaluation.aggregate() over the same rows, so they equal the harness numbers exactly.
- Served output (after retry/fallback, what the operator sees) is kept apart from the model's own first attempt.
- Grounding is mechanical consistency with the cited packet content, not entailment or correctness. Agreement with
  the validator's suggested_action is agreement, never accuracy. The judge and human-label items are listed in
  LIMITATIONS as not built.

Usage (from amd/system2): python scripts/report.py --runner template; see that script for the model run and rebuild.
"""
from __future__ import annotations

from collections import defaultdict
import math
import random
from typing import Callable, Dict, List, Optional, Sequence

from .evaluation import CHECKS, GROUNDING_LABEL, HELDOUT_SCOPE_NOTE, SCOPE_NOTE, aggregate, latency_summary

REPORT_VERSION = 'system2-report-2026-10-10.1'
CI_SEED = 20261010
CI_RESAMPLES = 1000
CI_LEVEL = 0.95
CI_METHOD = ('mission-level bootstrap: whole missions resampled with replacement, 2.5/97.5 percentiles, '
             'linear interpolation')


def _all(r):
    return True


def _sufficient(r):
    return not r['packet_insufficient']


def _hinted(r):
    return r['action']['validator_suggested'] is not None


def _attempted(r):
    return r['first_attempt'] is not None


BOTH, MODEL = ('template', 'model'), ('model',)
# (name, label, runner kinds, row filter, success). Filters depend only on the packet, so both runners share them.
METRICS = (
    ('public_response_valid', 'public response valid', BOTH, _all, lambda r: r['public_valid']),
    ('final_schema_valid', 'schema valid', BOTH, _sufficient, lambda r: r['final']['schema_valid']),
    ('final_citation_valid', 'citation IDs valid', BOTH, _sufficient, lambda r: r['final']['citation_valid']),
    ('final_numeric_consistent', 'numbers consistent with cited rows', BOTH, _sufficient,
     lambda r: r['final']['numeric_consistent']),
    ('final_name_consistent', 'names consistent with cited rows', BOTH, _sufficient,
     lambda r: r['final']['name_consistent']),
    ('final_all_checks', 'all four mechanical checks (grounding pass)', BOTH, _sufficient,
     lambda r: all(r['final'][k] for k in CHECKS)),
    ('agreement_with_validator', 'agreement with validator suggested_action', BOTH, _hinted,
     lambda r: r['action']['agrees_with_validator']),
    ('first_attempt_schema_valid', 'first attempt schema valid', MODEL, _attempted,
     lambda r: r['first_attempt']['schema_valid']),
    ('first_attempt_citation_valid', 'first attempt citation IDs valid', MODEL, _attempted,
     lambda r: r['first_attempt']['citation_valid']),
    ('first_attempt_numeric_consistent', 'first attempt numbers consistent', MODEL, _attempted,
     lambda r: r['first_attempt']['numeric_consistent']),
    ('first_attempt_name_consistent', 'first attempt names consistent', MODEL, _attempted,
     lambda r: r['first_attempt']['name_consistent']),
    ('first_attempt_accepted', 'accepted on first attempt (path llm)', MODEL, _sufficient,
     lambda r: r['path'] == 'llm'),
    ('model_accepted', 'model output served (llm + retry)', MODEL, _sufficient,
     lambda r: r['path'] in ('llm', 'retry')),
    ('retry', 'needed a retry', MODEL, _sufficient, lambda r: r['retry']),
    ('fallback', 'fell back to the checked template', MODEL, _sufficient, lambda r: r['fallback']),
)
SERVED = ('public_response_valid', 'final_schema_valid', 'final_citation_valid', 'final_numeric_consistent',
          'final_name_consistent', 'final_all_checks', 'agreement_with_validator')
OWN = tuple(m[0] for m in METRICS if m[2] == MODEL)
SPEED_CAVEAT = ('Speed is attributed to the label and endpoint above; only an amd-* labelled run on the gfx1151 box is '
                'an AMD measurement.')
LIVE_BUDGET_MS = 15000
METRIC = {m[0]: m for m in METRICS}

LIMITATIONS = [
    {'requirement': 'EVAL-02', 'item': 'claim support judged by a different model', 'status': 'not built',
     'note': 'Only the mechanical part is reported: schema, citation-ID, numeric and name consistency with the cited '
             'packet content.'},
    {'requirement': 'EVAL-03', 'item': 'LLM-vs-template judge rubric', 'status': 'not built',
     'note': 'No judge model scores usefulness or clarity; model and template are compared on mechanical checks only.'},
    {'requirement': 'EVAL-04', 'item': 'action quality against human labels', 'status': 'not built',
     'note': "Only agreement with the validator's suggested_action is reported. That is agreement, not accuracy."},
    {'requirement': 'EVAL-07', 'item': 'judge-vs-human agreement', 'status': 'not built',
     'note': 'Neither a judge nor human labels exist, so their agreement cannot be measured.'},
    {'requirement': 'grounding', 'item': 'entailment / correctness of claims', 'status': 'not built',
     'note': 'Grounding means %s.' % GROUNDING_LABEL},
    {'requirement': 'comparison', 'item': 'evidence that the model beats the template', 'status': 'not built',
     'note': 'The template passes the mechanical checks by construction (it copies cited rows), so mechanical parity '
             'is expected and is not evidence that the model is better.'},
    {'requirement': 'sample size', 'item': 'tight intervals', 'status': 'not built',
     'note': 'n is small (38 flags in 8 held-out missions), so the mission-level CIs are wide.'},
    {'requirement': 'data', 'item': 'independent real-world observations', 'status': 'not built',
     'note': '"Real" means sponsor kit missions as opposed to simulator output; the kit itself carries '
             'synthetic=True metadata. No synthetic or unrestricted-retrieval results are included.'},
]


# ── statistics ───────────────────────────────────────────────────────────────────────────────

def percentile(values: Sequence[float], q: float) -> float:
    """Linear interpolation between closest ranks (numpy's default); q in [0, 100]."""
    v = sorted(values)
    if not v or not 0 <= q <= 100:
        raise ValueError('percentile needs values and q in [0, 100]')
    pos = (len(v) - 1) * q / 100.0
    lo, hi = math.floor(pos), math.ceil(pos)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def _groups(rows, key=lambda r: r['mission_id']) -> Dict[str, list]:
    groups = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    return {k: groups[k] for k in sorted(groups)}


def bootstrap_ci(rows: Sequence, stat: Callable[[list], Optional[float]], n: int = CI_RESAMPLES,
                 seed: int = CI_SEED, key=lambda r: r['mission_id']) -> Optional[List[float]]:
    """95% CI of stat(rows), resampling whole missions; None with fewer than 2 missions or no defined resample."""
    groups = _groups(rows, key)
    keys = list(groups)
    if len(keys) < 2:
        return None
    rng, vals = random.Random(seed), []
    for _ in range(n):
        value = stat([r for k in rng.choices(keys, k=len(keys)) for r in groups[k]])
        if value is not None:
            vals.append(value)
    if not vals:
        return None
    return [round(percentile(vals, 2.5), 6), round(percentile(vals, 97.5), 6)]


def _mean_of(success):
    return lambda rows: (sum(bool(success(r)) for r in rows) / len(rows)) if rows else None


def rate_with_ci(rows: Sequence[dict], metric: str, n: int = CI_RESAMPLES, seed: int = CI_SEED) -> dict:
    """{value, count, denominator, missions, ci95}; value None with count 0 on an empty denominator."""
    _, _, _, keep, success = METRIC[metric]
    chosen = [r for r in rows if keep(r)]
    count = sum(bool(success(r)) for r in chosen)
    return {'value': count / len(chosen) if chosen else None, 'count': count, 'denominator': len(chosen),
            'missions': len({r['mission_id'] for r in chosen}),
            'ci95': bootstrap_ci(chosen, _mean_of(success), n, seed)}


def paired_diff(model_rows: Sequence[dict], template_rows: Sequence[dict], metric: str, n: int = CI_RESAMPLES,
                seed: int = CI_SEED) -> dict:
    """Model minus template rate on the same flags; the CI resamples missions and applies each to both runners."""
    _, _, _, keep, success = METRIC[metric]
    template = {r['case_id']: r for r in template_rows if keep(r)}
    pairs = [(m, template[m['case_id']]) for m in model_rows if keep(m) and m['case_id'] in template]

    def stat(sample):
        if not sample:
            return None
        return (sum(bool(success(m)) for m, _ in sample) - sum(bool(success(t)) for _, t in sample)) / len(sample)
    return {'value': stat(pairs), 'pairs': len(pairs), 'missions': len({m['mission_id'] for m, _ in pairs}),
            'ci95': bootstrap_ci(pairs, stat, n, seed, key=lambda pair: pair[0]['mission_id'])}


def _nearest(values: Sequence[float]) -> dict:
    v = sorted(values)
    if not v:
        return {'p50': None, 'mean': None, 'min': None, 'max': None, 'n': 0}
    return {'p50': v[max(0, math.ceil(0.5 * len(v)) - 1)], 'mean': round(sum(v) / len(v), 3), 'min': v[0],
            'max': v[-1], 'n': len(v)}


def speed_block(model_rows: Sequence[dict], memory: Optional[dict], measurement: dict) -> dict:
    """Latency, decode speed, token counts and peak memory of the held-out model run, with its attribution."""
    rows = [r for r in model_rows if r['attempt_count'] > 0]
    if not rows:
        return {'measured': False, 'reason': 'no model attempts in the held-out run'}
    attempts = [a for r in rows for a in r['attempts']]
    latency = latency_summary([r['latency_ms'] for r in rows])
    speeds = _nearest([a['tokens_per_sec'] for a in attempts if a['tokens_per_sec'] is not None])
    tokens = {k: {x: _nearest([a[k] for a in attempts if a[k] is not None])[x] for x in ('p50', 'max', 'n')}
              for k in ('prompt_tokens', 'completion_tokens')}
    return {'measured': True, 'label': measurement['label'], 'endpoint': measurement['endpoint'],
            'endpoint_loopback': measurement['endpoint_loopback'], 'host': measurement['host'],
            'flags': len(rows), 'attempts': len(attempts), 'latency_ms': latency,
            'within_15s_p95': latency['p95'] is not None and latency['p95'] <= LIVE_BUDGET_MS,
            'decode_tokens_per_sec': speeds, **tokens,
            'truncated_attempts': sum(a['status'] == 'truncated' for a in attempts),
            'timeout_attempts': sum(a['status'] == 'timeout' for a in attempts),
            'models': sorted({a['model'] for a in attempts if a['model'] and a['model'] != 'template'}),
            'peak_memory': memory, 'caveat': SPEED_CAVEAT}


# ── metrics ──────────────────────────────────────────────────────────────────────────────────

def heldout_scope(eligible: bool) -> dict:
    """The held-out scope block (same keys and order as evaluation.run_evaluation's scope)."""
    return {'split': 'heldout', 'headline_eligible': bool(eligible), 'grounding_label': GROUNDING_LABEL,
            'note': HELDOUT_SCOPE_NOTE}


def _runner_block(rows: List[dict], kind: str, ci: dict) -> dict:
    block = {'kind': kind}
    for name, _, kinds, _, _ in METRICS:
        if kind in kinds:
            block[name] = rate_with_ci(rows, name, ci['resamples'], ci['seed'])
    by_category = {}
    for category, group in _groups(rows, lambda r: r['category']).items():
        entry = {'flags': len(group), 'missions': len({r['mission_id'] for r in group})}
        if kind == 'model':
            entry['model_accepted'] = sum(r['path'] in ('llm', 'retry') for r in group if _sufficient(r))
            entry['fallback'] = sum(bool(r['fallback']) for r in group)
        by_category[category] = entry
    block['by_category'] = by_category
    block['aggregates'] = aggregate(rows, kind)
    return block


def _by_runner(records: List[dict], names: Sequence[str]) -> Dict[str, List[dict]]:
    return {name: [r for r in records if r['runner'] == name] for name in names}


def build_metrics(records: List[dict], context: dict) -> dict:
    """Pure: the held-out headline, development section, speed and limitations from records + context."""
    ci = {'method': CI_METHOD, 'level': CI_LEVEL, 'resamples': context['ci']['resamples'],
          'seed': context['ci']['seed']}
    names = list(context['identity']['heldout']['runners'])
    heldout = _by_runner([r for r in records if r['section'] == 'heldout'], names)
    kinds = {name: rows[0]['kind'] for name, rows in heldout.items() if rows}
    cases = {r['case_id']: r['mission_id'] for rows in heldout.values() for r in rows}
    missions = sorted(set(cases.values()))
    scope = dict(context['heldout_scope'], n_flags=len(cases), n_missions=len(missions), missions=missions)
    runners = {name: _runner_block(rows, kinds[name], ci) for name, rows in heldout.items()}
    models = [n for n in names if kinds.get(n) == 'model']
    comparison = None
    if models and 'template' in kinds.values():
        model, template = models[0], next(n for n in names if kinds.get(n) == 'template')
        comparison = {'model': model, 'template': template, 'note': 'model minus template on the same flags',
                      'metrics': {m: paired_diff(heldout[model], heldout[template], m, ci['resamples'], ci['seed'])
                                  for m in SERVED}}
    speed = ({'measured': False, 'reason': 'no model runner in this run'} if not models
             else speed_block(heldout[models[0]], context['memory'], context['measurement']))
    development = None
    if context['identity'].get('development'):
        dev = _by_runner([r for r in records if r['section'] == 'development'], names)
        development = {'split': 'train', 'headline_eligible': False, 'note': SCOPE_NOTE,
                       'n_flags': len({r['case_id'] for rows in dev.values() for r in rows}),
                       'runners': {name: aggregate(rows, kinds[name]) for name, rows in dev.items()}}
    return {
        'report_version': REPORT_VERSION,
        'scope': scope,
        'command': context['command'],
        'identity': context['identity'],
        'measurement': context['measurement'],
        'ci': ci,
        'headline': {'runners': runners, 'comparison': comparison},
        'speed': speed,
        'development': development,
        'limitations': LIMITATIONS,
    }


# ── render ───────────────────────────────────────────────────────────────────────────────────

def _pct(v) -> str:
    return '%.1f%%' % (100 * v)


def _cell(r: Optional[dict]) -> str:
    if r is None:
        return '-'
    if r['value'] is None:
        return 'n/a (0 flags)'
    ci = 'CI n/a' if r['ci95'] is None else '[%s, %s]' % (_pct(r['ci95'][0]), _pct(r['ci95'][1]))
    return '%s %s (%d/%d flags, %d missions)' % (_pct(r['value']), ci, r['count'], r['denominator'], r['missions'])


def _diff(d: Optional[dict]) -> str:
    if d is None or d['value'] is None:
        return '-'
    ci = 'CI n/a' if d['ci95'] is None else '[%+.1f, %+.1f]' % (100 * d['ci95'][0], 100 * d['ci95'][1])
    return '%+.1f pp %s (%d pairs, %d missions)' % (100 * d['value'], ci, d['pairs'], d['missions'])


def _table(L, metrics, names, wanted):
    runners, comparison = metrics['headline']['runners'], metrics['headline']['comparison']
    extra = comparison is not None and any(w in comparison['metrics'] for w in wanted)
    head = list(names) + (['model − template'] if extra else [])
    L += ['| metric | %s |' % ' | '.join(head), '|---|%s' % ('---|' * len(head))]
    for name in wanted:
        if any(name in runners[n] for n in names):
            cells = [_cell(runners[n].get(name)) for n in names]
            if extra:
                cells.append(_diff(comparison['metrics'].get(name)))
            L.append('| %s | %s |' % (METRIC[name][1], ' | '.join(cells)))


def _mem(m: Optional[dict]) -> str:
    if m is None:
        return 'not measured: no memory sampler in this run'
    if not m['available']:
        return 'not measured: %s' % m['reason']
    gpus = ', '.join('%s %s:%s' % (c['card'], c['vendor'], c['device']) for c in m['cards']) or 'unknown GPU'
    return '%.1f MiB peak (VRAM %.1f + GTT %.1f; baseline %.1f MiB; %d samples) on %s' % (
        m['peak']['total_mib'], m['peak']['vram_mib'], m['peak']['gtt_mib'], m['baseline']['total_mib'],
        m['samples'], gpus)


def _speed(L, speed):
    if not speed['measured']:
        L.append('Not measured: %s.' % speed['reason'])
        return
    lat, tps = speed['latency_ms'], speed['decode_tokens_per_sec']
    L += ['Label `%s`, endpoint `%s` (loopback %s), host `%s`. %s' % (
              speed['label'], speed['endpoint'], speed['endpoint_loopback'], speed['host'], speed['caveat']), '',
          '| | |', '|---|---|',
          '| latency p50 / p95 per flag (nearest-rank, incl. retry/fallback) | %s / %s ms (%d flags) |' % (
              lat['p50'], lat['p95'], lat['n']),
          '| p95 within the 15 s live budget | %s |' % ('yes' if speed['within_15s_p95'] else 'no'),
          '| decode tokens/s p50 / mean (min-max, n attempts) | %s / %s (%s-%s, %d) |' % (
              tps['p50'], tps['mean'], tps['min'], tps['max'], tps['n']),
          '| prompt tokens p50 / max | %s / %s |' % (speed['prompt_tokens']['p50'], speed['prompt_tokens']['max']),
          '| completion tokens p50 / max | %s / %s |' % (
              speed['completion_tokens']['p50'], speed['completion_tokens']['max']),
          '| truncated / timed-out attempts | %d / %d of %d |' % (
              speed['truncated_attempts'], speed['timeout_attempts'], speed['attempts']),
          '| peak device memory | %s |' % _mem(speed['peak_memory']),
          '| models observed | %s |' % (', '.join(speed['models']) or '-')]


def render(metrics: dict) -> str:
    scope, ident, meas = metrics['scope'], metrics['identity'], metrics['measurement']
    names = list(metrics['headline']['runners'])
    data = ident['heldout']['dataset']
    L = ['# System 2 evaluation report', '',
         'Held-out dataset content %s, %d of %d flags, runners %s. Label `%s`, %s to %s. Report %s.' % (
             data['content_hash'][:12], len(data['selected_case_ids']), data['case_count'], ', '.join(names),
             meas['label'], meas['started_at'], meas['finished_at'], metrics['report_version']), '',
         '**Headline-eligible (held-out fold 2, full set).**' if scope['headline_eligible']
         else '**Not headline (smoke subset or non-held-out data).**', '',
         '## Reproduce', '', '```', metrics['command']['run'], metrics['command']['rebuild'], '```', '',
         '`--rebuild` recomputes every number below from cases.jsonl and the checked-in held-out dataset, and exits 4 '
         'on any difference.', '',
         '## Headline: held-out fold-2 missions', '',
         '%d flags in %d missions (%s). %s Grounding = %s.' % (
             scope['n_flags'], scope['n_missions'], ', '.join(scope['missions']), scope['note'],
             GROUNDING_LABEL), '',
         'Each cell: value [95%% CI] (k/n flags, missions). CI = %s, %d resamples, seed %d.' % (
             metrics['ci']['method'], metrics['ci']['resamples'], metrics['ci']['seed']), '',
         '### Served output (what the operator sees, after retry/fallback)', '']
    _table(L, metrics, names, SERVED)
    L += ['', "### Model's own output", '']
    if any(r['kind'] == 'model' for r in metrics['headline']['runners'].values()):
        _table(L, metrics, names, OWN)
    else:
        L.append('No model runner in this run.')
    model_names = [n for n in names if metrics['headline']['runners'][n]['kind'] == 'model']
    if model_names:
        L += ['', '### Fallback and paths', '']
        for n in model_names:
            r = metrics['headline']['runners'][n]
            L += ['- `%s` fallback to the checked template: %s' % (n, _cell(r['fallback'])),
                  '- `%s` retry: %s' % (n, _cell(r['retry']))]
        for n in names:
            paths = metrics['headline']['runners'][n]['aggregates']['paths']
            L.append('- `%s` paths: %s' % (n, ', '.join('%s %d' % kv for kv in paths.items())))
    L += ['', '### By category', '', '| category | %s |' % ' | '.join(names), '|---|%s' % ('---|' * len(names))]
    categories = sorted({c for r in metrics['headline']['runners'].values() for c in r['by_category']})
    for c in categories:
        cells = []
        for n in names:
            e = metrics['headline']['runners'][n]['by_category'].get(c)
            cells.append('-' if e is None else '%d flags, %d missions%s' % (
                e['flags'], e['missions'], '' if 'fallback' not in e else
                ', model served %d, fallback %d' % (e['model_accepted'], e['fallback'])))
        L.append('| %s | %s |' % (c, ' | '.join(cells)))
    L += ['', '## Speed', '']
    _speed(L, metrics['speed'])
    L += ['', '## Development set (training missions; not headline)', '']
    dev = metrics['development']
    if dev is None:
        L.append('Not run (--no-dev).')
    else:
        L += ['%d flags. %s' % (dev['n_flags'], dev['note']), '',
              '| metric | %s |' % ' | '.join(dev['runners']), '|---|%s' % ('---|' * len(dev['runners']))]
        rows = [('public response valid', lambda a: a['public_response_valid'])]
        rows += [('final %s' % k, (lambda k: lambda a: a['final'][k])(k)) for k in CHECKS]
        rows += [('agreement with validator suggested_action', lambda a: a['action']['agreement_with_validator']),
                 ('model output served (llm + retry)', lambda a: a['generation']['model_accepted']),
                 ('fell back to the checked template', lambda a: a['generation']['fallback'])]
        for label, get in rows:
            L.append('| %s | %s |' % (label, ' | '.join(_dev_cell(get(a)) for a in dev['runners'].values())))
    L += ['', '## Limitations and deferred items', '']
    L += ['- **%s** %s: %s. %s' % (x['requirement'], x['item'], x['status'], x['note'])
          for x in metrics['limitations']]
    L += ['', '## Method', '',
          '- Held-out packets: System 1 fold-2 kit missions; dynamic evidence only from the flag\'s own mission at or '
          'before as_of; no labels, targets or prior answers; few-shots from the training pool only.',
          '- Both runners see the identical normalized packet per flag (packet hashes checked) and finish in the same '
          'checker. A fallback is the checked template and never counts as model success.',
          '- Rates: k/n over the stated denominator; failed, timed-out and fallback flags stay in it. Rows for '
          'packets marked insufficient are excluded from the final-check denominators.',
          '- CI: %s; %d resamples; seed %d; fewer than 2 missions gives no CI.' % (
              metrics['ci']['method'], metrics['ci']['resamples'], metrics['ci']['seed']),
          '- Identity hash %s; code revision %s.' % (
              ident['identity_hash'][:12], (ident['heldout']['code']['revision'] or 'unknown')[:12])]
    return '\n'.join(L) + '\n'


def _dev_cell(r: dict) -> str:
    return 'n/a (0)' if r['value'] is None else '%d/%d (%s)' % (r['count'], r['denominator'], _pct(r['value']))
