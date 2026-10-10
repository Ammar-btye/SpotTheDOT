"""One-command defendable report (plan 04-02): held-out headline with mission-level CIs, dev section, rebuild.

Every CLI test runs the real scripts/report.py in a subprocess. Model runs talk to a ThreadingHTTPServer on
127.0.0.1 that imitates llama-server, and memory comes from a fake drm tree. No model, GPU or llama.cpp process is
involved, so every number asserted here is a regression check of the report code, never a measurement.
"""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
SYS2 = ROOT / 'amd/system2'
sys.path.insert(0, str(SYS2))
SCRIPT = SYS2 / 'scripts/report.py'
HELDOUT = SYS2 / 'data/heldout_packets.json'
DEV = SYS2 / 'data/dev_packets.json'

from analyst.dataset import load_dataset  # noqa: E402
from analyst.evaluation import aggregate  # noqa: E402
from analyst.headline import METRICS, bootstrap_ci, percentile  # noqa: E402

HELDOUT_CASES = load_dataset(HELDOUT, split='heldout')
HEADINGS = ('## Reproduce', '## Headline: held-out fold-2 missions', '## Speed',
            '## Development set (training missions; not headline)', '## Limitations and deferred items', '## Method')


def _reject(name):
    raise AssertionError('non-finite JSON constant %s in artifact' % name)


def report(*args, timeout=300):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                          timeout=timeout, cwd=str(SYS2))


def metrics(out: Path) -> dict:
    return json.loads((out / 'metrics.json').read_text(encoding='utf-8'), parse_constant=_reject)


def records(out: Path) -> list:
    return [json.loads(line, parse_constant=_reject)
            for line in (out / 'cases.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]


@pytest.fixture(scope='module')
def template_run(tmp_path_factory):
    out = tmp_path_factory.mktemp('report') / 'template'
    result = report('--runner', 'template', '--out-dir', out, '--quiet')
    assert result.returncode == 0, result.stderr
    return out


# ── statistics ───────────────────────────────────────────────────────────────────────────────

def test_percentile_is_linear_interpolation():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert percentile([4, 1, 3, 2], 0) == 1 and percentile([1, 2, 3, 4], 100) == 4
    with pytest.raises(ValueError):
        percentile([], 50)


def test_bootstrap_ci_edges_and_determinism():
    mean = lambda rows: sum(r['ok'] for r in rows) / len(rows) if rows else None  # noqa: E731
    one = [{'mission_id': 'M1', 'ok': 1}, {'mission_id': 'M1', 'ok': 0}]
    assert bootstrap_ci(one, mean) is None
    two = [{'mission_id': 'A', 'ok': 1}] * 3 + [{'mission_id': 'B', 'ok': 0}] * 3
    assert bootstrap_ci(two, mean) == [0.0, 1.0]
    many = [{'mission_id': 'M%d' % (i % 5), 'ok': i % 3 != 0} for i in range(30)]
    assert bootstrap_ci(many, mean, seed=7) == bootstrap_ci(many, mean, seed=7)


# ── offline template run ─────────────────────────────────────────────────────────────────────

def test_template_report_scope(template_run):
    for name in ('cases.jsonl', 'report.md', 'metrics.json'):
        assert (template_run / name).is_file()
    scope = metrics(template_run)['scope']
    assert scope['headline_eligible'] is True and scope['split'] == 'heldout'
    assert scope['n_flags'] == len(HELDOUT_CASES) == 38
    assert scope['n_missions'] == 8 and scope['missions'] == sorted({c.mission_id for c in HELDOUT_CASES})


def _harness_value(agg, name):
    if name == 'public_response_valid':
        return agg['public_response_valid']
    if name == 'agreement_with_validator':
        return agg['action']['agreement_with_validator']
    if name.startswith('final_') and name != 'final_all_checks':
        return agg['final'][name[len('final_'):]]
    return None


def test_template_rates_equal_harness_aggregates(template_run):
    block = metrics(template_run)['headline']['runners']['template']
    rows = [r for r in records(template_run) if r['section'] == 'heldout' and r['runner'] == 'template']
    agg = aggregate(rows, 'template')
    assert block['aggregates'] == agg
    for name, _, kinds, _, _ in METRICS:
        if 'template' not in kinds:
            assert name not in block
            continue
        r = block[name]
        assert set(r) == {'value', 'count', 'denominator', 'missions', 'ci95'}
        assert r['ci95'] is None or 0 <= r['ci95'][0] <= r['ci95'][1] <= 1
        want = _harness_value(agg, name)
        if want is not None:
            assert {k: r[k] for k in ('value', 'count', 'denominator')} == want, name
    assert block['final_citation_valid']['denominator'] == 38 and block['final_citation_valid']['missions'] == 8


def _untimed(value):
    """Drop measured wall-clock latency, which legitimately varies between runs; every count and CI must not."""
    if isinstance(value, dict):
        return {k: _untimed(v) for k, v in value.items() if k != 'latency_ms'}
    if isinstance(value, list):
        return [_untimed(v) for v in value]
    return value


def test_template_report_is_deterministic(template_run, tmp_path):
    again = tmp_path / 'again'
    assert report('--runner', 'template', '--out-dir', again, '--quiet').returncode == 0
    a, b = metrics(template_run), metrics(again)
    assert _untimed(a['headline']) == _untimed(b['headline'])
    assert _untimed(a['development']) == _untimed(b['development'])
    assert all(a['headline']['runners']['template'][m]['ci95'] == b['headline']['runners']['template'][m]['ci95']
               for m in ('public_response_valid', 'final_all_checks', 'agreement_with_validator'))


def test_development_section_and_record_sections(template_run):
    m = metrics(template_run)
    dev = m['development']
    assert dev['split'] == 'train' and dev['headline_eligible'] is False
    assert 'training missions only' in dev['note'] and dev['n_flags'] == 6
    rows = records(template_run)
    assert {r['section'] for r in rows} == {'heldout', 'development'}
    assert sum(r['section'] == 'heldout' for r in rows) == 38


def test_limitations_listed_as_not_built(template_run):
    items = {x['requirement']: x for x in metrics(template_run)['limitations']}
    for req in ('EVAL-02', 'EVAL-03', 'EVAL-04', 'EVAL-07'):
        assert items[req]['status'] == 'not built'
    assert 'different model' in items['EVAL-02']['item'] and 'human labels' in items['EVAL-04']['item']
    assert 'agreement, not accuracy' in items['EVAL-04']['note']


def test_report_markdown_sections(template_run):
    text = (template_run / 'report.md').read_text(encoding='utf-8')
    for heading in HEADINGS:
        assert heading in text, heading
    speed = text.split('## Speed', 1)[1].split('\n## ', 1)[0]
    assert 'Not measured' in speed
    assert 'agreement with validator suggested_action' in text
    assert '**Headline-eligible (held-out fold 2, full set).**' in text


def test_limit_subset_is_not_headline(tmp_path):
    out = tmp_path / 'smoke'
    result = report('--runner', 'template', '--limit', '5', '--no-dev', '--out-dir', out, '--quiet')
    assert result.returncode == 0, result.stderr
    m = metrics(out)
    assert m['scope']['headline_eligible'] is False and m['scope']['n_flags'] == 5
    assert m['development'] is None
    assert '**Not headline' in (out / 'report.md').read_text(encoding='utf-8')


def test_wrong_split_rejected_and_usage_errors(tmp_path):
    out = tmp_path / 'x'
    result = report('--heldout', DEV, '--out-dir', out)
    assert result.returncode == 1 and not out.exists()
    result = report('--dev', HELDOUT, '--out-dir', out)
    assert result.returncode == 1 and not out.exists()
    assert report('--runner', 'both', '--out-dir', out).returncode == 2
    assert not out.exists()
