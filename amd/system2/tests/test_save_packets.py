"""Real offline CLI subprocesses: reproducibility, safe import, atomic rejection."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / 'amd/system2/scripts/save_packets.py'
DATA = ROOT / 'amd/system2/data/dev_packets.json'


def run(*args):
    assert CLI.is_file(), 'offline saved-packet importer must exist'
    return subprocess.run([sys.executable, str(CLI), *map(str, args)], cwd=ROOT,
                          capture_output=True, text=True, timeout=30)


def test_seed_reproducible_matches_checked_in_packets(tmp_path):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    first = run('--seed', '--output', a)
    assert first.returncode == 0, first.stderr
    assert a.exists(), 'seed mode must publish a validated saved dataset'
    assert run('--seed', '--output', b).returncode == 0
    assert a.read_bytes() == b.read_bytes() == DATA.read_bytes()
    assert json.loads(first.stdout)['content_hash'] == json.loads(a.read_text())['manifest']['content_hash']


def test_import_reproducible_and_preserves_reference_separation(tmp_path):
    capture = json.loads(DATA.read_text())
    capture.pop('manifest')
    capture['cases'][0]['reference'] = {'expected_action': 'REINSPECT_NOW', 'source': 'operator-labelled'}
    source = tmp_path / 'source.json'
    source.write_text(json.dumps(capture))
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    assert run('--input', source, '--output', a).returncode == 0
    assert run('--input', source, '--output', b).returncode == 0
    assert a.read_bytes() == b.read_bytes()
    obj = json.loads(a.read_text())
    assert obj['cases'][0]['reference']['expected_action'] == 'REINSPECT_NOW'
    assert 'expected_action' not in json.dumps(obj['cases'][0]['request'])


@pytest.mark.parametrize('mutation', ['label', 'future', 'unknown', 'holdout', 'ambiguous', 'empty', 'null', 'bad_json'])
@pytest.mark.parametrize('existing', [False, True])
def test_rejection_never_publishes_or_replaces(tmp_path, mutation, existing):
    capture = json.loads(DATA.read_text())
    capture.pop('manifest')
    case = capture['cases'][0]
    fact = case['request']['context']['facts'][0]
    if mutation == 'label': fact['labels'] = {'action': 'SECRET_LABEL'}
    elif mutation == 'future': case['as_of'] = '2000-01-01T00:00:00'
    elif mutation == 'unknown': fact.pop('provenance')
    elif mutation == 'holdout': case['mission_id'] = 'M006'
    elif mutation == 'ambiguous': fact['fact'] = 'A prior generated answer passed.'
    elif mutation == 'empty': capture = {'cases': []}
    elif mutation == 'null': capture = None
    source, output = tmp_path / 'source.json', tmp_path / 'approved.json'
    source.write_text('invalid json' if mutation == 'bad_json' else json.dumps(capture))
    if existing: output.write_bytes(b'previous approved data')
    result = run('--input', source, '--output', output)
    assert result.returncode != 0
    assert 'SECRET_LABEL' not in result.stderr
    assert output.read_bytes() == b'previous approved data' if existing else not output.exists()
    assert not list(tmp_path.glob('*.tmp'))


def test_safe_lineage_allows_stripping_transport_diagnostics(tmp_path):
    capture = json.loads(DATA.read_text())
    capture.pop('manifest')
    case = capture['cases'][0]
    case['request']['context']['explanations'] = [{'answer': 'PRIOR_ANSWER_DO_NOT_PROMPT'}]
    case['request']['context']['system1'] = [{'answer': 'PRIOR_LABEL'}]
    case['request']['flag']['labels'] = {'escalate': 'A'}
    source, output = tmp_path / 'source.json', tmp_path / 'approved.json'
    source.write_text(json.dumps(capture))
    result = run('--input', source, '--output', output)
    assert result.returncode == 0, result.stderr
    text = output.read_text()
    assert 'PRIOR_ANSWER_DO_NOT_PROMPT' not in text and 'PRIOR_LABEL' not in text
    case['request']['context']['facts'][0].pop('provenance')
    source.write_text(json.dumps(capture))
    before = output.read_bytes()
    assert run('--input', source, '--output', output).returncode != 0
    assert output.read_bytes() == before


def test_no_holdout_override_and_seed_import_exclusive(tmp_path):
    assert run('--seed', '--output', tmp_path / 'x', '--holdout-fold', '0').returncode != 0
    assert run('--seed', '--input', DATA, '--output', tmp_path / 'x').returncode != 0
