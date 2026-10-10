"""One-command defendable report (plan 04-02): held-out headline with mission-level CIs, dev section, rebuild.

Every CLI test runs the real scripts/report.py in a subprocess. Model runs talk to a ThreadingHTTPServer on
127.0.0.1 that imitates llama-server, and memory comes from a fake drm tree. No model, GPU or llama.cpp process is
involved, so every number asserted here is a regression check of the report code, never a measurement.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import shutil
from pathlib import Path
import subprocess
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[3]
SYS2 = ROOT / 'amd/system2'
sys.path.insert(0, str(SYS2))
SCRIPT = SYS2 / 'scripts/report.py'
HELDOUT = SYS2 / 'data/heldout_packets.json'
DEV = SYS2 / 'data/dev_packets.json'

from analyst.dataset import dataset_manifest, load_dataset, validate_dataset  # noqa: E402
from analyst.evaluation import aggregate  # noqa: E402
from analyst.headline import METRICS, SERVED, bootstrap_ci, percentile  # noqa: E402
from analyst.prompts import example_output, packet_view  # noqa: E402

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


# ── fake-model run: paired comparison, fallback, speed and memory plumbing ───────────────────

DEV_CASES = load_dataset(DEV)
BY_EVIDENCE = {json.dumps(packet_view(c.prepared)['evidence'], sort_keys=True): c
               for c in HELDOUT_CASES + DEV_CASES if not c.prepared.insufficient_context}
BROKEN = tuple(sorted(c.case_id for c in HELDOUT_CASES if c.category != 'mission')[:3])
TPS = 41.5


def envelope(content, completion=120, prompt=900):
    return {'model': 'qwen-fake', 'choices': [{'index': 0, 'finish_reason': 'stop',
                                               'message': {'role': 'assistant', 'content': content}}],
            'usage': {'prompt_tokens': prompt, 'completion_tokens': completion},
            'timings': {'predicted_per_second': TPS, 'prompt_n': prompt, 'predicted_n': completion}}


@pytest.fixture(scope='module')
def server():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            current = json.loads(body['messages'][-1]['content'].split('\n')[1])
            case = BY_EVIDENCE[json.dumps(current['evidence'], sort_keys=True)]
            content = ('{"evidence": [' if case.case_id in BROKEN
                       else json.dumps(example_output(case.prepared)))
            data = json.dumps(envelope(content)).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    http.daemon_threads = True
    worker = threading.Thread(target=http.serve_forever, kwargs={'poll_interval': 0.02}, daemon=True)
    worker.start()
    yield 'http://127.0.0.1:%d' % http.server_port
    http.shutdown()
    http.server_close()
    worker.join()


@pytest.fixture(scope='module')
def drm(tmp_path_factory):
    d = tmp_path_factory.mktemp('drm') / 'card0' / 'device'
    d.mkdir(parents=True)
    for name, value in (('mem_info_vram_used', '536870912'), ('mem_info_gtt_used', '6442450944'),
                        ('vendor', '0x1002'), ('device', '0x1586')):
        (d / name).write_text(value + '\n')
    return d.parents[1]


@pytest.fixture(scope='module')
def model_run(server, drm, tmp_path_factory):
    out = tmp_path_factory.mktemp('report') / 'both'
    result = report('--runner', 'both', '--model-url', server + '/', '--model', 'qwen-fake',
                    '--label', 'fake-loopback-test', '--drm-root', drm, '--mem-interval-s', '0.05',
                    '--out-dir', out, '--quiet')
    assert result.returncode == 0, result.stderr
    return out


def test_model_run_reports_own_output_and_fallback(model_run):
    runners = metrics(model_run)['headline']['runners']
    model = runners['model']
    for name in ('first_attempt_accepted', 'model_accepted', 'fallback', 'first_attempt_citation_valid'):
        assert set(model[name]) == {'value', 'count', 'denominator', 'missions', 'ci95'}
    assert model['fallback']['count'] == 3 and model['fallback']['denominator'] == 38
    assert model['model_accepted']['count'] == 35 and model['retry']['count'] == 3
    rows = [r for r in records(model_run) if r['section'] == 'heldout' and r['runner'] == 'model']
    assert model['aggregates'] == aggregate(rows, 'model')
    assert model['aggregates']['generation']['fallback'] == {k: model['fallback'][k]
                                                             for k in ('value', 'count', 'denominator')}
    assert 'first_attempt_accepted' not in runners['template']


def test_model_run_paired_comparison(model_run):
    comparison = metrics(model_run)['headline']['comparison']
    assert comparison['model'] == 'model' and comparison['template'] == 'template'
    assert set(comparison['metrics']) == set(SERVED)
    for d in comparison['metrics'].values():
        assert d['pairs'] == 38 and d['missions'] == 8
        assert d['ci95'] is None or -1 <= d['ci95'][0] <= d['ci95'][1] <= 1
    # served output is the model's own answer or the checked template, so mechanical checks stay level here
    assert comparison['metrics']['final_citation_valid']['value'] == 0.0


def test_model_run_speed_block(model_run):
    m = metrics(model_run)
    speed = m['speed']
    assert speed['measured'] is True and speed['label'] == 'fake-loopback-test'
    assert speed['endpoint'].startswith('http://127.0.0.1:') and '@' not in speed['endpoint']
    assert speed['endpoint_loopback'] is True
    assert isinstance(speed['latency_ms']['p50'], int) and isinstance(speed['latency_ms']['p95'], int)
    assert speed['decode_tokens_per_sec']['p50'] == TPS and speed['decode_tokens_per_sec']['n'] == speed['attempts']
    assert speed['completion_tokens']['max'] == 120 and speed['prompt_tokens']['p50'] == 900
    assert speed['models'] == ['qwen-fake'] and 'amd-*' in speed['caveat']
    mem = speed['peak_memory']
    assert mem['available'] is True and mem['peak']['total_bytes'] >= mem['baseline']['total_bytes']
    assert mem['cards'] == [{'card': 'card0', 'vendor': '0x1002', 'device': '0x1586'}]
    assert m['measurement']['label'] == 'fake-loopback-test'
    text = (model_run / 'report.md').read_text(encoding='utf-8')
    section = text.split('## Speed', 1)[1].split('\n## ', 1)[0]
    assert 'fake-loopback-test' in section and '0x1002:0x1586' in section
    assert 'model − template' in text and '### Fallback and paths' in text


def test_model_run_without_memory_sampling(server, tmp_path):
    out = tmp_path / 'nomem'
    result = report('--runner', 'both', '--model-url', server, '--model', 'qwen-fake', '--label', 'fake-loopback-test',
                    '--mem-source', 'none', '--no-dev', '--limit', '4', '--out-dir', out, '--quiet')
    assert result.returncode == 0, result.stderr
    mem = metrics(out)['speed']['peak_memory']
    assert mem['available'] is False and mem['reason'] == 'memory sampling disabled (--mem-source none)'


@pytest.mark.parametrize('extra', [
    ('--model-url', 'http://127.0.0.1:9', '--model', 'x'),                                # no --label
    ('--model-url', 'http://user:secret@127.0.0.1:9', '--label', 'x'),                    # credentials
    ('--model-url', 'ftp://127.0.0.1:9', '--label', 'x'),                                 # scheme
])
def test_model_usage_errors(tmp_path, extra):
    out = tmp_path / 'x'
    result = report('--runner', 'both', '--out-dir', out, *extra)
    assert result.returncode == 2 and not out.exists()
    assert 'secret' not in result.stderr


# ── --rebuild ────────────────────────────────────────────────────────────────────────────────

def _copy(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst


def _rewrite_records(path: Path, edit):
    rows = records(path)
    rows = edit(rows)
    (path / 'cases.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows), encoding='utf-8')


@pytest.mark.parametrize('which', ['template_run', 'model_run'])
def test_rebuild_is_byte_identical(request, which, tmp_path):
    src = request.getfixturevalue(which)
    out = tmp_path / 'rebuilt'
    result = report('--rebuild', src, '--out-dir', out)
    assert result.returncode == 0, result.stderr
    assert 'rebuild: identical' in result.stdout
    for name in ('metrics.json', 'report.md', 'cases.jsonl'):
        assert (out / name).read_bytes() == (src / name).read_bytes(), name


def test_rebuild_in_place_keeps_bytes(template_run, tmp_path):
    a = _copy(template_run, tmp_path / 'a')
    before = {n: (a / n).read_bytes() for n in ('metrics.json', 'report.md', 'cases.jsonl')}
    assert report('--rebuild', a).returncode == 0
    assert {n: (a / n).read_bytes() for n in before} == before


def _flip(rows):
    r = next(r for r in rows if r['section'] == 'heldout' and r['runner'] == 'template')
    r['final']['citation_valid'] = not r['final']['citation_valid']
    return rows


def _drop(rows):
    i = next(i for i, r in enumerate(rows) if r['section'] == 'heldout')
    return rows[:i] + rows[i + 1:]


def _repacket(rows):
    next(r for r in rows if r['section'] == 'heldout')['packet_hash'] = '0' * 64
    return rows


@pytest.mark.parametrize('tamper, message', [
    ('flip', 'differs at headline.runners.template'),
    ('headline', 'differs at headline.runners.template.final_citation_valid.value'),
    ('drop', 'differs at '),
    ('packet', 'held-out dataset changed since the run'),
    ('identity', 'differs at identity.identity_hash'),
])
def test_rebuild_refuses_tampering(template_run, tmp_path, tamper, message):
    a, out = _copy(template_run, tmp_path / 'a'), tmp_path / 'out'
    if tamper == 'flip':
        _rewrite_records(a, _flip)
    elif tamper == 'drop':
        _rewrite_records(a, _drop)
    elif tamper == 'packet':
        _rewrite_records(a, _repacket)
    else:
        m = metrics(a)
        if tamper == 'headline':
            m['headline']['runners']['template']['final_citation_valid']['value'] = 0.5
        else:
            m['identity']['heldout']['code']['revision'] = 'f' * 40
        (a / 'metrics.json').write_text(json.dumps(m, indent=2), encoding='utf-8')
    result = report('--rebuild', a, '--out-dir', out)
    assert result.returncode == 4, (result.stdout, result.stderr)
    assert message in result.stderr
    assert not out.exists()


def test_rebuild_refuses_changed_heldout_dataset(template_run, tmp_path):
    raw = json.loads(HELDOUT.read_text(encoding='utf-8'))
    subset = validate_dataset({'cases': raw['cases'][:-1]}, split='heldout')
    changed = tmp_path / 'heldout.json'
    changed.write_text(json.dumps({'cases': [c.to_dict() for c in subset], 'manifest': dataset_manifest(subset)}),
                       encoding='utf-8')
    out = tmp_path / 'out'
    result = report('--rebuild', template_run, '--heldout', changed, '--out-dir', out)
    assert result.returncode == 4 and 'held-out dataset changed since the run' in result.stderr
    assert not out.exists()


@pytest.mark.parametrize('missing', ['cases.jsonl', 'metrics.json'])
def test_rebuild_missing_inputs(template_run, tmp_path, missing):
    a = _copy(template_run, tmp_path / 'a')
    (a / missing).unlink()
    result = report('--rebuild', a, '--out-dir', tmp_path / 'out')
    assert result.returncode == 1 and not (tmp_path / 'out').exists()


def test_rebuild_never_runs_a_model(template_run, tmp_path):
    result = report('--rebuild', template_run, '--runner', 'both', '--model-url', 'http://127.0.0.1:9', '--label', 'x')
    assert result.returncode == 2
