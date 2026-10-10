"""Controlled fold-2 held-out packets for the Phase 4 headline (plan 04-01).

The population is recomputed here independently from system1's kit and policy, the real save_packets.py and
evaluate.py CLIs run in subprocesses, and every tamper must make the held-out validator fail closed. The train
validator (and through it the few-shot loader) must reject the held-out file, and vice versa.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
SYS2 = ROOT / 'amd/system2'
sys.path.insert(0, str(SYS2))
sys.path.insert(0, str(ROOT / 'amd/system1'))
DEV = SYS2 / 'data/dev_packets.json'
HELDOUT = SYS2 / 'data/heldout_packets.json'
SAVE = SYS2 / 'scripts/save_packets.py'
EVALUATE = SYS2 / 'scripts/evaluate.py'

from analyst.dataset import (HOLDOUT_MISSIONS, evidence_item, load_dataset, source_tables,  # noqa: E402
                             validate_dataset)
from analyst.prompts import load_examples  # noqa: E402
from triage.events import action_event, mission_events  # noqa: E402
from triage.kit import load_kit  # noqa: E402
from triage.policy import label_action, label_mission  # noqa: E402

DYNAMIC = ('actions', 'readings', 'anomalies', 'missions')


def run(script, *args, timeout=120):
    return subprocess.run([sys.executable, str(script), *map(str, args)], cwd=ROOT, capture_output=True, text=True,
                          timeout=timeout)


def raw(path=HELDOUT) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def expected_population():
    """Independent recomputation: flagged fold-2 actions plus non-P4 fold-2 missions -> {case_id: category}."""
    kit, out = load_kit(), {}
    for a in kit.actions:
        if a['mission_id'] not in HOLDOUT_MISSIONS:
            continue
        ev = action_event(a, kit.missions[a['mission_id']], kit.locations[a['location_id']], kit.assets[a['asset_id']],
                          kit.readings.get(a['action_id']), kit.anomalies.get(a['action_id']), 'kit')
        category = label_action(ev)['category']
        if category != 'none':
            out['heldout-' + a['action_id']] = category
    for m in sorted(HOLDOUT_MISSIONS):
        actions = sorted(kit.actions_of(m), key=lambda a: (a['timestamp'], a['sequence']))
        ev = mission_events(kit.missions[m], actions, kit.locations, kit.assets, kit.readings, kit.anomalies, 'kit')[-1]
        if label_mission(ev)['priority'] != 'P4':
            out['heldout-mission-' + m] = 'mission'
    return out


# ── reproducibility and population ───────────────────────────────────────────────────────────

def test_heldout_cli_reproduces_checked_in_file(tmp_path):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    first = run(SAVE, '--heldout', '--output', a)
    assert first.returncode == 0, first.stderr
    assert run(SAVE, '--heldout', '--output', b).returncode == 0
    assert a.read_bytes() == b.read_bytes() == HELDOUT.read_bytes()
    manifest = json.loads(first.stdout)
    assert manifest['split'] == 'heldout' and manifest['case_count'] == 38
    assert manifest == raw()['manifest']


def test_dev_seed_still_byte_identical(tmp_path):
    out = tmp_path / 'd.json'
    result = run(SAVE, '--seed', '--output', out)
    assert result.returncode == 0, result.stderr
    assert out.read_bytes() == DEV.read_bytes()
    assert 'split' not in json.loads(result.stdout)


def test_heldout_and_seed_are_exclusive(tmp_path):
    assert run(SAVE, '--heldout', '--seed', '--output', tmp_path / 'x').returncode != 0
    assert not (tmp_path / 'x').exists()


def test_population_matches_independent_policy_recomputation():
    cases = load_dataset(HELDOUT, split='heldout')
    assert {c.case_id: c.category for c in cases} == expected_population()
    assert len(cases) == 38
    missions = {c.mission_id for c in cases}
    assert len(missions) == 8 and missions == HOLDOUT_MISSIONS - {'M019'}


def test_every_case_is_own_mission_and_as_of_bounded():
    tables = source_tables()
    for c in load_dataset(HELDOUT, split='heldout'):
        d = c.to_dict()
        assert c.split == 'heldout' and c.mission_id in HOLDOUT_MISSIONS
        assert c.reference is None
        assert d['request']['flag'] == {'category': c.category}
        for ref in c.source_lineage:
            if ref['table'] in DYNAMIC:
                assert tables[ref['table']][ref['row_id']]['mission_id'] == c.mission_id
                assert ref['available_at'] <= c.as_of
        facts = {f['id']: f for f in d['request']['context']['facts']}
        if c.category != 'mission':
            f1 = facts['F1']['provenance']['source_rows']
            assert f1 == [{**f1[0], 'table': 'actions', 'row_id': c.case_id[len('heldout-'):]}]
        else:
            assert facts['F1']['provenance']['source_rows'][0]['table'] == 'missions'
            assert c.as_of == tables['missions'][c.mission_id]['end_time']
        assert not c.prepared.insufficient_context


# ── cross-split rejection ────────────────────────────────────────────────────────────────────

def test_train_validator_and_few_shot_loader_reject_heldout():
    with pytest.raises(ValueError):
        load_dataset(HELDOUT)
    with pytest.raises(ValueError):
        validate_dataset(raw(HELDOUT))
    with pytest.raises(ValueError):
        load_examples(HELDOUT)


def test_heldout_validator_rejects_dev():
    with pytest.raises(ValueError):
        validate_dataset(raw(DEV), split='heldout')
    with pytest.raises(ValueError):
        validate_dataset(raw(HELDOUT), split='validation')


def test_mixed_splits_fail():
    value = raw(HELDOUT)
    value.pop('manifest')
    value['cases'].append(raw(DEV)['cases'][0])
    for split in ('train', 'heldout'):
        with pytest.raises(ValueError):
            validate_dataset(value, split=split)


# ── tampering ────────────────────────────────────────────────────────────────────────────────

def _inject(case, table, row):
    """Add one correctly hashed, correctly projected evidence row from `row` to the case."""
    context = case['request']['context']
    item = evidence_item('F%d' % (len(context['facts']) + 1), table, row)
    context['facts'].append(item)
    context['citation_ids'].append(item['id'])
    case['source_lineage'] = case['source_lineage'] + item['provenance']['source_rows']


def _early_row(tables, missions, as_of):
    rows = [r for r in tables['actions'].values() if r['mission_id'] in missions and r['timestamp'] <= as_of]
    assert rows, 'fixture needs an earlier row from another mission'
    return min(rows, key=lambda r: r['timestamp'])


def _tamper(how):
    value, tables = raw(HELDOUT), source_tables()
    case = max(value['cases'], key=lambda c: c['as_of'])
    others = {m['mission_id'] for m in tables['missions'].values()} - HOLDOUT_MISSIONS
    if how == 'training_row':
        _inject(case, 'actions', _early_row(tables, others, case['as_of']))
    elif how == 'other_heldout_row':
        _inject(case, 'actions', _early_row(tables, HOLDOUT_MISSIONS - {case['mission_id']}, case['as_of']))
    elif how == 'future':
        case['as_of'] = tables['missions'][case['mission_id']]['start_time']
    elif how == 'expected_action':
        case['request']['context']['expected_action'] = 'REINSPECT_NOW'
    elif how == 'fact':
        case['request']['context']['facts'][0]['fact'] += '; status=COMPLETED'
    elif how == 'manifest':
        value['manifest']['content_hash'] = '0' * 64
        return value
    value.pop('manifest')
    return value


@pytest.mark.parametrize('how', ['training_row', 'other_heldout_row', 'future', 'expected_action', 'fact',
                                 'manifest'])
def test_tampered_heldout_rejected(how):
    with pytest.raises(ValueError):
        validate_dataset(_tamper(how), split='heldout')


def test_untampered_copy_still_validates():
    value = raw(HELDOUT)
    assert len(validate_dataset(copy.deepcopy(value), split='heldout')) == 38


# ── tracer: template evaluation end to end ───────────────────────────────────────────────────

def test_template_evaluation_on_heldout(tmp_path):
    out = tmp_path / 'eval'
    result = run(EVALUATE, '--dataset', HELDOUT, '--runner', 'template', '--out-dir', out, '--quiet', timeout=180)
    assert result.returncode == 0, result.stderr
    metrics = json.loads((out / 'metrics.json').read_text(encoding='utf-8'))
    assert metrics['identity']['dataset']['case_count'] == 38
    assert metrics['scope']['split'] == 'heldout'
    rows = [json.loads(line) for line in (out / 'cases.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 38 and {r['runner'] for r in rows} == {'template'}
    assert {r['split'] for r in rows} == {'heldout'}
