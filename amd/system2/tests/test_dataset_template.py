"""Controlled saved packets exercise the actual loader, normalization and template."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'amd/system2'))
DATA = ROOT / 'amd/system2/data/dev_packets.json'


def api():
    assert importlib.util.find_spec('analyst.dataset'), 'controlled dataset loader must exist'
    assert importlib.util.find_spec('analyst.template'), 'grounded template must exist'
    from analyst.dataset import load_dataset
    from analyst.template import template_assessment
    return load_dataset, template_assessment


def test_equipment_saved_request_to_grounded_template():
    load, template = api()
    from analyst.backend_contract import BackendAssessRequest, BackendAssessResponse
    from analyst.packet import normalize_packet
    cases = load(DATA)
    assert any(c.category == 'equipment' for c in cases), 'saved equipment request must be available'
    case = next(c for c in cases if c.category == 'equipment')
    prepared = normalize_packet(BackendAssessRequest.model_validate(case.request.model_dump()))
    result = template(prepared)
    assert list(result) == ['evidence', 'answer', 'question', 'recommended_action', 'confidence', 'insufficient_context']
    BackendAssessResponse.model_validate({**result, 'flag_id': prepared.flag_id, 'path': 'stub'})
    assert result['question'] == prepared.question
    for evidence in result['evidence']:
        assert evidence['claim'] == prepared.content[evidence['ids'][0]]
        assert evidence['claim'] in result['answer']


def test_categories_safe_insufficiency_and_identity():
    load, template = api()
    cases = load(DATA)
    assert {c.category for c in cases} == {'equipment', 'robot_health', 'navigation', 'data_quality', 'mission', 'insufficient_context'}
    assert len(cases) == 6
    for c in cases:
        assert c.split == 'train'
        result = template(c.prepared)
        assert result['recommended_action'] in c.prepared.allowed_actions
        assert 'expected_action' not in json.dumps(c.request.model_dump())
    c = next(c for c in cases if c.category == 'insufficient_context')
    assert template(c.prepared)['evidence'] == []
    assert template(c.prepared)['confidence'] == 'low'
    assert template(c.prepared)['recommended_action'] == 'MANUAL_REVIEW'
    with pytest.raises((AttributeError, TypeError)):
        c.case_id = 'changed'
    req = cases[0].request
    req.context.clear()
    assert cases[0].request.context


def raw():
    api()
    return json.loads(DATA.read_text(encoding='utf-8'))


def save(tmp_path, obj):
    path = tmp_path / 'captures.json'
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
    return path


@pytest.mark.parametrize('field', ['labels', 'expected_action', 'explanation', 'answer', 'previous_output', 'target'])
@pytest.mark.parametrize('section', ['facts', 'manual', 'policy', 'similar_incidents', 'asset_history', 'system1'])
def test_recursive_leakage_rejected(tmp_path, field, section):
    load, _ = api()
    obj = raw()
    obj['cases'][0]['request']['context'].setdefault(section, []).append({'id': 'bad', 'nested': {field: 'hidden'}})
    with pytest.raises(ValueError):
        load(save(tmp_path, obj))


@pytest.mark.parametrize('mutation', ['holdout', 'future', 'availability', 'hash', 'unknown', 'fact', 'aggregate', 'mission_outcome'])
def test_bad_provenance_and_future_facts_rejected(tmp_path, mutation):
    load, _ = api()
    obj = raw()
    obj.pop('manifest', None)
    c = obj['cases'][0]
    item = c['request']['context']['facts'][0]
    if mutation == 'holdout': c['mission_id'] = 'M006'
    elif mutation == 'future': c['as_of'] = '2000-01-01T00:00:00'
    elif mutation == 'availability': item['provenance']['source_rows'][0]['available_at'] = '2000-01-01T00:00:00'
    elif mutation == 'hash': item['provenance']['source_rows'][0]['row_hash'] = '0' * 64
    elif mutation == 'unknown': item['provenance']['kind'] = 'unverified'
    elif mutation == 'fact': item['fact'] += ' Future failure predicted.'
    elif mutation == 'aggregate': item['success_rate_pct'] = 100
    elif mutation == 'mission_outcome': item['end_battery_pct'] = 5
    with pytest.raises(ValueError): load(save(tmp_path, obj))


def test_equality_duplicates_order_and_hash(tmp_path):
    load, _ = api()
    from analyst.dataset import dataset_manifest
    obj = raw()
    obj.pop('manifest', None)
    c = obj['cases'][0]
    item = c['request']['context']['facts'][0]
    c['as_of'] = max(r['available_at'] for r in item['provenance']['source_rows'])
    c['request']['context']['facts'] = [item, copy.deepcopy(item)]
    c['source_lineage'] = copy.deepcopy(item['provenance']['source_rows'])
    c['request']['context']['citation_ids'] = [item['id']]
    a = load(save(tmp_path, obj))
    assert len(a[0].request.context['facts']) == 1
    obj['cases'].reverse()
    b = load(save(tmp_path, obj))
    assert dataset_manifest(a) == dataset_manifest(b)
    item['fact'] += ' conflict'
    with pytest.raises(ValueError): load(save(tmp_path, obj))


@pytest.mark.parametrize('obj', [None, [], {}, {'cases': []}, {'cases': None}])
def test_empty_and_null_dataset_fail(tmp_path, obj):
    load, _ = api()
    with pytest.raises(ValueError): load(save(tmp_path, obj))


def test_single_case_and_unicode_identity(tmp_path):
    load, template = api()
    obj = raw()
    obj.pop('manifest', None)
    obj['cases'] = obj['cases'][:1]
    item = obj['cases'][0]['request']['context']['facts'][0]
    item['id'] = 'Fé\u0301–点'
    obj['cases'][0]['request']['context']['citation_ids'] = [item['id']]
    obj['cases'][0]['request']['context']['question'] = 'Que signifie 点 — café ?'
    c, = load(save(tmp_path, obj))
    out = template(c.prepared)
    assert any(e['ids'] == [item['id']] for e in out['evidence'])
    assert out['question'] == 'Que signifie 点 — café ?'


def test_holdouts_match_system1_default_fold():
    api()
    sys.path.insert(0, str(ROOT / 'amd/system1'))
    from scripts.build_data import make_folds
    from triage.kit import load_kit
    from analyst.dataset import HOLDOUT_MISSIONS
    assert set(make_folds(load_kit(), 20261010)[2]) == set(HOLDOUT_MISSIONS)
