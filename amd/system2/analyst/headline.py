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

from .evaluation import CHECKS, GROUNDING_LABEL, HELDOUT_SCOPE_NOTE, SCOPE_NOTE, aggregate

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
        'headline': {'runners': runners, 'comparison': None},
        'speed': {'measured': False, 'reason': 'no model runner in this run'},
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


def _table(L, metrics, names, wanted):
    runners = metrics['headline']['runners']
    L += ['| metric | %s |' % ' | '.join(names), '|---|%s' % ('---|' * len(names))]
    for name in wanted:
        if any(name in runners[n] for n in names):
            L.append('| %s | %s |' % (METRIC[name][1], ' | '.join(_cell(runners[n].get(name)) for n in names)))


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
    speed = metrics['speed']
    L.append('Not measured: %s.' % speed['reason'] if not speed['measured'] else '')
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
