"""Flat public response accepts checked-pipeline metadata (llm/retry/fallback) without loosening safety rules.

Public responses are built from real run_pipeline results (fake generators, no model). The committed JSON Schema's
conditional rules are evaluated independently by a focused keyword evaluator, so a schema/model drift fails here.
"""
import copy
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'amd/system2'))
SYSTEM2 = ROOT / 'amd/system2'
DATA = SYSTEM2 / 'data/dev_packets.json'
SCHEMA = SYSTEM2 / 'schema/assess_response.schema.json'
EXAMPLES = ('equipment', 'robot_health', 'navigation', 'data_quality', 'mission', 'insufficient_context')

from analyst.backend_contract import BACKEND_CONTRACT_VERSION, BackendAssessResponse  # noqa: E402
from analyst.dataset import load_dataset  # noqa: E402
from analyst.pipeline import Generation, GenerationError, run_pipeline  # noqa: E402
from analyst.prompts import example_output  # noqa: E402


def case(case_id):
    return next(c for c in load_dataset(DATA) if c.case_id == case_id)


def public(run, flag_id):
    """Internal AssessmentRun -> flat public response fields (no nested metadata)."""
    return dict(run.assessment, flag_id=flag_id, model=run.model, latency_ms=run.latency_ms,
                tokens_per_sec=run.tokens_per_sec, path=run.path)


def scripted(*outcomes):
    queue = list(outcomes)

    def generator(packet, errors=(), timeout_s=None):
        o = queue.pop(0)
        if isinstance(o, Exception):
            raise o
        return o(packet) if callable(o) else o
    return generator


def ok(packet):
    return Generation(json.dumps(example_output(packet)), 'qwen3.5-9b-q4', 'stop', 900, 180, 35.6)


def bad(packet):
    return Generation('{"evidence":', 'qwen3.5-9b-q4', 'stop', 900, 3, 35.6)


def run_for(path):
    c = case('kit-equipment' if path != 'insufficient_context' else 'kit-insufficient_context')
    gen = {'llm': scripted(ok), 'retry': scripted(bad, ok),
           'fallback': scripted(GenerationError('http', 'status 500'), bad),
           'insufficient_context': scripted()}[path]
    run = run_pipeline(c.request, gen)
    assert run.path == path
    return c, run


def fixture_response(name):
    return json.loads((SYSTEM2 / 'fixtures/backend' / (name + '.json')).read_text(encoding='utf-8'))['response']


# ── every path from real pipeline results ────────────────────────────────────────────────────

@pytest.mark.parametrize('path', ['llm', 'retry', 'fallback', 'insufficient_context'])
def test_pipeline_result_builds_valid_public_response(path):
    c, run = run_for(path)
    r = BackendAssessResponse.model_validate(public(run, c.request.flag_id))
    assert r.path == path and r.model == run.model
    assert list(r.model_dump())[:6] == ['evidence', 'answer', 'question', 'recommended_action', 'confidence',
                                        'insufficient_context']
    assert published_accepts(public(run, c.request.flag_id))
    if path == 'fallback':
        assert r.model == 'template' and r.tokens_per_sec is None
    if path in ('llm', 'retry'):
        assert r.model == 'qwen3.5-9b-q4' and r.tokens_per_sec == 35.6 and r.evidence
    if path == 'insufficient_context':
        assert (r.evidence, r.confidence, r.recommended_action.value) == ([], 'low', 'MANUAL_REVIEW')


@pytest.mark.parametrize('name', EXAMPLES)
def test_existing_stub_and_insufficient_examples_still_validate(name):
    response = fixture_response(name)
    r = BackendAssessResponse.model_validate(response)
    assert r.path in ('stub', 'insufficient_context')
    assert published_accepts(response)


def test_stub_defaults_and_version_marker_retained():
    response = fixture_response('equipment')
    for key in ('model', 'latency_ms', 'tokens_per_sec'):
        response.pop(key, None)
    r = BackendAssessResponse.model_validate(response)
    assert (r.model, r.latency_ms, r.tokens_per_sec) == ('stub', 0, None)
    assert BACKEND_CONTRACT_VERSION == '2026-10-10.backend.2'   # backend.2: additive multimodal inputs


# ── safety rules stay strict ─────────────────────────────────────────────────────────────────

def complete(**changes):
    c, run = run_for('llm')
    return dict(public(run, c.request.flag_id), **changes)


def insufficient(**changes):
    c, run = run_for('insufficient_context')
    return dict(public(run, c.request.flag_id), **changes)


@pytest.mark.parametrize('build', [
    lambda: complete(evidence=[]),
    lambda: complete(path='insufficient_context'),
    lambda: complete(insufficient_context=True),
    lambda: complete(path='fallback'),                       # fallback must be labelled template
    lambda: complete(path='stub'),                           # stub path keeps model stub
    lambda: complete(model='template'),                      # llm success never claims the template
    lambda: complete(model='stub', path='retry'),
    lambda: complete(path='LLM'),
    lambda: complete(path='template'),
    lambda: insufficient(confidence='high'),
    lambda: insufficient(recommended_action='MONITOR'),
    lambda: insufficient(evidence=[{'claim': 'x', 'ids': ['F1']}]),
    lambda: insufficient(path='llm'),
    lambda: insufficient(path='fallback'),
])
def test_inconsistent_path_or_insufficiency_rejected_by_model_and_schema(build):
    response = build()
    with pytest.raises(ValidationError):
        BackendAssessResponse.model_validate(response)
    assert not published_accepts(response)


@pytest.mark.parametrize('changes', [
    {'model': ''}, {'model': '   '}, {'model': 5}, {'model': None},
    {'latency_ms': True}, {'latency_ms': -1}, {'latency_ms': 1.5}, {'latency_ms': '3'},
    {'tokens_per_sec': True}, {'tokens_per_sec': -0.5}, {'tokens_per_sec': float('inf')},
    {'tokens_per_sec': float('nan')}, {'tokens_per_sec': '35.6'},
    {'attempts': [{'index': 1}]}, {'metadata': {'path': 'llm'}}, {'flag_id': True},
])
def test_wrong_or_nested_metadata_rejected(changes):
    with pytest.raises(ValidationError):
        BackendAssessResponse.model_validate(complete(**changes))


@pytest.mark.parametrize('text', ['NaN', 'Infinity', '-Infinity'])
def test_nonfinite_speed_rejected_from_json(text):
    body = json.dumps(complete()).replace('"tokens_per_sec": 35.6', '"tokens_per_sec": %s' % text)
    assert text in body
    with pytest.raises(ValidationError):
        BackendAssessResponse.model_validate_json(body)


def test_integer_speed_and_zero_metadata_accepted():
    r = BackendAssessResponse.model_validate(complete(tokens_per_sec=0, latency_ms=0))
    assert r.tokens_per_sec == 0 and r.latency_ms == 0


def test_request_shape_and_vocabulary_unchanged():
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    assert schema['properties']['path']['enum'] == ['stub', 'llm', 'retry', 'fallback', 'insufficient_context']
    assert schema['properties']['model']['type'] == 'string' and 'const' not in schema['properties']['model']
    assert schema['properties']['model']['default'] == 'stub'
    assert schema['$defs']['BackendAction']['enum'][-1] == 'MANUAL_REVIEW'
    assert schema['properties']['confidence']['enum'] == ['high', 'medium', 'low']
    assert schema['$defs']['BackendEvidence']['additionalProperties'] is False
    assert set(schema['properties']) == {'evidence', 'answer', 'question', 'recommended_action', 'confidence',
                                         'insufficient_context', 'flag_id', 'model', 'latency_ms',
                                         'tokens_per_sec', 'path'}


def test_live_api_stays_stub():
    from fastapi.testclient import TestClient
    from analyst.api import KEY_HEADER, create_app
    key = 'contract-test-key-0123456789'
    pair = json.loads((SYSTEM2 / 'fixtures/backend/equipment.json').read_text(encoding='utf-8'))
    with TestClient(create_app(api_key=key)) as client:
        r = client.post('/v1/assess', json=pair['request'], headers={KEY_HEADER: key})
    assert r.status_code == 200 and (r.json()['model'], r.json()['path']) == ('stub', 'stub')


# ── independent evaluator for the published conditional rules ───────────────────────────────

def _matches(instance, rule):
    known = {'properties', 'required', 'const', 'enum', 'not', 'minItems', 'maxItems', 'allOf', 'if', 'then', 'else'}
    assert set(rule) <= known, set(rule) - known
    if 'const' in rule and (type(instance) is not type(rule['const']) or instance != rule['const']):
        return False
    if 'enum' in rule and not any(type(instance) is type(v) and instance == v for v in rule['enum']):
        return False
    if 'not' in rule and _matches(instance, rule['not']):
        return False
    if 'minItems' in rule and len(instance) < rule['minItems']:
        return False
    if 'maxItems' in rule and len(instance) > rule['maxItems']:
        return False
    if any(k not in instance for k in rule.get('required', [])):
        return False
    if not all(_matches(instance[k], r) for k, r in rule.get('properties', {}).items() if k in instance):
        return False
    if 'if' in rule:
        branch = rule.get('then' if _matches(instance, rule['if']) else 'else')
        if branch is not None and not _matches(instance, branch):
            return False
    return all(_matches(instance, r) for r in rule.get('allOf', []))


def published_accepts(response):
    """Committed schema's enum/const/conditional rules (types are covered by the Pydantic parity test)."""
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    if set(response) - set(schema['properties']) or any(k not in response for k in schema['required']):
        return False
    top = {k: schema[k] for k in ('if', 'then', 'else', 'allOf') if k in schema}
    props = {k: {kk: vv for kk, vv in v.items() if kk in ('const', 'enum')}
             for k, v in schema['properties'].items() if k in ('path', 'confidence')}
    return _matches(response, dict(top, properties=props))


def test_schema_drift_check_passes():
    import subprocess
    r = subprocess.run([sys.executable, str(SYSTEM2 / 'scripts/export_schema.py'), '--check'],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    sub = copy.deepcopy(json.loads(SCHEMA.read_text(encoding='utf-8')))
    sub.pop('$comment')
    assert sub == BackendAssessResponse.model_json_schema(mode='serialization')
