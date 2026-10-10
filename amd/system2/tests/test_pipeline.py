"""Checked generation pipeline: at most two attempts, then the shared checked template, offline only."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'amd/system2'))
DATA = ROOT / 'amd/system2/data/dev_packets.json'

from analyst.backend_contract import BackendAssessRequest  # noqa: E402
from analyst.dataset import load_dataset  # noqa: E402
from analyst.packet import normalize_packet  # noqa: E402
from analyst.template import template_assessment  # noqa: E402


def api():
    assert importlib.util.find_spec('analyst.pipeline'), 'checked generation pipeline must exist'
    import analyst.pipeline as p
    return p


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class FakeGen:
    """Scripted generator; each outcome is a Generation, an exception, or a callable(packet) -> Generation."""

    def __init__(self, outcomes, clock=None, step=0.25):
        self.outcomes, self.clock, self.step, self.calls = list(outcomes), clock, step, []

    def __call__(self, packet, errors=(), timeout_s=None):
        self.calls.append({'errors': errors, 'timeout_s': timeout_s, 'content': dict(packet.content)})
        if self.clock is not None:
            self.clock.t += self.step
        out = self.outcomes[min(len(self.calls), len(self.outcomes)) - 1]
        if isinstance(out, BaseException):
            raise out
        return out(packet) if callable(out) else out


def equipment():
    case = next(c for c in load_dataset(DATA) if c.category == 'equipment')
    return case.request


def gen(obj, **kw):
    p = api()
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return p.Generation(text=text, model=kw.pop('model', 'fake-model'), **kw)


def valid_candidate(req):
    prepared = normalize_packet(req)
    return {'evidence': [{'claim': 'Visual score was 75 with a HIGH severity defect.', 'ids': ['F2', 'F3']}],
            'answer': 'Visual score was 75.', 'question': prepared.question,
            'recommended_action': 'SCHEDULE_MAINTENANCE', 'confidence': 'medium', 'insufficient_context': False}


def invalid_candidate(req):
    bad = valid_candidate(req)
    bad['evidence'][0]['claim'] = 'Visual score was 76.'
    return bad


def cfg(clock=None, **kw):
    p = api()
    return p.PipelineConfig(clock=clock or Clock(), **kw)


def test_valid_generation_returns_llm():
    p, req = api(), equipment()
    g = FakeGen([gen(valid_candidate(req), prompt_tokens=900, completion_tokens=120, tokens_per_sec=24.5)])
    run = p.run_pipeline(req, g, cfg())
    assert run.path == 'llm' and run.model == 'fake-model'
    assert run.assessment == valid_candidate(req)
    assert list(run.assessment) == ['evidence', 'answer', 'question', 'recommended_action', 'confidence',
                                    'insufficient_context']
    assert len(g.calls) == 1 and g.calls[0]['errors'] == ()
    assert [a.status for a in run.attempts] == ['accepted']
    assert run.tokens_per_sec == 24.5 and run.prompt_tokens == 900 and run.completion_tokens == 120
    assert run.final_errors == ()


def test_invalid_then_valid_returns_retry_with_first_errors():
    p, req = api(), equipment()
    g = FakeGen([gen(invalid_candidate(req)), gen(valid_candidate(req), model='fake-2')])
    run = p.run_pipeline(req, g, cfg())
    assert run.path == 'retry' and run.model == 'fake-2'
    assert run.assessment == valid_candidate(req)
    assert len(g.calls) == 2
    first, second = run.attempts
    assert first.status == 'rejected' and first.errors and first.errors[0].code == 'ungrounded_number'
    assert second.status == 'accepted' and second.errors == ()
    retry_errors = g.calls[1]['errors']
    from analyst.grounding import describe_errors
    assert retry_errors == describe_errors(first.errors)
    assert all(isinstance(e, str) and '\n' not in e and len(e) <= 200 for e in retry_errors)
    assert g.calls[0]['content'] == g.calls[1]['content'], 'retry must reuse the same evidence'


@pytest.mark.parametrize('outcomes, statuses', [
    (['invalid', 'invalid'], ['rejected', 'rejected']),
    (['{"evidence": [', '{"evidence": ['], ['parse_error', 'parse_error']),
    (['[1, 2]', 'null'], ['rejected', 'rejected']),
    (['nan', 'dupe'], ['parse_error', 'parse_error']),
    (['truncated', 'truncated'], ['truncated', 'truncated']),
    (['oversized', 'invalid'], ['oversized', 'rejected']),
    (['transport', 'transport'], ['transport_error', 'transport_error']),
    (['timeout', 'invalid'], ['timeout', 'rejected']),
])
def test_two_failures_return_checked_template_fallback(outcomes, statuses):
    p, req = api(), equipment()
    good = json.dumps(valid_candidate(req))
    made = {
        'invalid': gen(invalid_candidate(req)),
        'nan': gen(good.replace('"medium"', 'NaN')),
        'dupe': gen(good[:-1] + ', "confidence": "high"}'),
        'truncated': gen(valid_candidate(req), finish_reason='length'),
        'oversized': gen(json.dumps(dict(valid_candidate(req), answer='Visual score was 75. ' + 'x' * 70000))),
        'transport': p.GenerationError('http', 'HTTP 502 from model server'),
        'timeout': p.GenerationError('timeout', 'read timed out'),
    }
    g = FakeGen([made.get(o) or gen(o) for o in outcomes])
    run = p.run_pipeline(req, g, cfg())
    prepared = normalize_packet(req)
    assert run.path == 'fallback' and run.model == 'template', 'fallback must never be labelled LLM success'
    assert run.assessment == template_assessment(prepared)
    assert [a.status for a in run.attempts] == statuses
    assert len(g.calls) == 2
    assert run.tokens_per_sec is None
    from analyst.grounding import check_assessment
    assert check_assessment(run.assessment, prepared) == ()


def bloated(req):
    """Grounded and packet-cited, but over the generation model's bounds (6 claims, 1,000-char answer)."""
    ok = valid_candidate(req)
    return dict(ok, evidence=ok['evidence'] * 6, answer=('Visual score was 75. ' * 50).strip())


@pytest.mark.parametrize('mutate', [
    bloated,
    lambda req: dict(valid_candidate(req), answer='Visual score was 75. ' + 'x' * 300),
    lambda req: dict(valid_candidate(req), evidence=[{'claim': 'Visual score was 75. ' + 'y' * 200,
                                                      'ids': ['F2']}]),
])
def test_strict_generation_bounds_hold_without_server_grammar(mutate):
    """A server that ignores response_format must not get over-long or over-many claims accepted as 'llm'."""
    p, req = api(), equipment()
    from analyst.grounding import check_assessment
    prepared = normalize_packet(req)
    candidate = mutate(req)
    assert check_assessment(candidate, prepared) == (), 'precondition: the grounding checker alone accepts it'
    g = FakeGen([gen(candidate), gen(candidate)])
    run = p.run_pipeline(req, g, cfg())
    assert run.path == 'fallback' and run.model == 'template'
    assert [a.status for a in run.attempts] == ['rejected', 'rejected']
    assert [e.code for e in run.attempts[0].errors] == ['schema']
    assert g.calls[1]['errors'] and 'schema' in g.calls[1]['errors'][0]


def test_insufficient_packet_short_circuits_without_generator_calls():
    p = api()
    case = next(c for c in load_dataset(DATA) if c.category == 'insufficient_context')
    g = FakeGen([AssertionError('generator must not be called')])
    run = p.run_pipeline(case.request, g, cfg())
    assert g.calls == [] and run.attempts == ()
    assert run.path == 'insufficient_context' and run.model == 'template'
    assert run.assessment == template_assessment(case.prepared)
    a = run.assessment
    assert a['evidence'] == [] and a['recommended_action'] == 'MANUAL_REVIEW' and a['confidence'] == 'low'


def test_deadline_bounds_total_work():
    p, req = api(), equipment()
    clock = Clock()
    g = FakeGen([gen(valid_candidate(req))], clock=clock, step=16.0)
    run = p.run_pipeline(req, g, cfg(clock, deadline_s=15.0))
    assert len(g.calls) == 1, 'a late first attempt leaves no time for a retry'
    assert [a.status for a in run.attempts] == ['timeout']
    assert run.path == 'fallback' and run.latency_ms == 16000
    assert g.calls[0]['timeout_s'] == 15.0
    clock = Clock()
    g = FakeGen([p.GenerationError('http', 'reset'), gen(valid_candidate(req))], clock=clock, step=4.0)
    run = p.run_pipeline(req, g, cfg(clock, deadline_s=15.0))
    assert run.path == 'retry' and [c['timeout_s'] for c in g.calls] == [15.0, 11.0]
    assert run.latency_ms == 8000 and [a.latency_ms for a in run.attempts] == [4000, 4000]


def test_transport_failures_are_bounded_to_two_calls():
    p, req = api(), equipment()
    g = FakeGen([p.GenerationError('http', 'down')] * 5)
    run = p.run_pipeline(req, g, cfg())
    assert len(g.calls) == 2 and run.path == 'fallback'
    assert g.calls[1]['errors'] and all('transport_error' in e for e in g.calls[1]['errors'])


def test_no_safe_template_content_yields_explicit_manual_review():
    p = api()
    actions = {'MONITOR': 'watch', 'DISPATCH_TECHNICIAN': 'send'}
    ctx = {'question': 'Q?', 'facts': [{'id': 'F1', 'fact': 'value NaN'}], 'allowed_actions': actions,
           'suggested_action': 'DISPATCH_TECHNICIAN'}
    req = BackendAssessRequest(flag_id=3, flag={}, context=ctx)
    g = FakeGen([gen('not json')])
    run = p.run_pipeline(req, g, cfg())
    a = run.assessment
    assert run.path == 'insufficient_context' and run.model == 'template'
    assert a['evidence'] == [] and a['insufficient_context'] is True
    assert a['recommended_action'] == 'MANUAL_REVIEW' and a['confidence'] == 'low'
    assert run.final_errors and run.final_errors[0].code == 'nonfinite_number'
    # One surviving template claim is kept; the unsafe one is dropped.
    ctx['facts'] = [{'id': 'F1', 'fact': 'value NaN'}, {'id': 'F2', 'fact': 'battery_pct=17'}]
    run = p.run_pipeline(BackendAssessRequest(flag_id=3, flag={}, context=ctx), FakeGen([gen('x')]), cfg())
    assert run.path == 'fallback'
    assert run.assessment['evidence'] == [{'claim': 'battery_pct=17', 'ids': ['F2']}]
    assert run.assessment['answer'] == 'battery_pct=17'
    assert run.final_errors == ()


def test_no_mutation_and_generator_cannot_alter_checked_evidence():
    p, req = api(), equipment()
    before = req.model_dump()

    def tamper(packet):
        packet.content['F1'] = 'battery 99'
        return gen({**valid_candidate(req), 'evidence': [{'claim': 'battery 99', 'ids': ['F1']}],
                    'answer': 'battery 99'})

    g = FakeGen([tamper, tamper])
    run = p.run_pipeline(req, g, cfg())
    assert run.path == 'fallback'
    assert req.model_dump() == before
    assert g.calls[0]['content'] == g.calls[1]['content'] == normalize_packet(req).content
    out = run.assessment
    out['evidence'].clear()
    assert run.assessment['evidence'], 'returned assessment must be a fresh copy'


def test_repeat_runs_are_identical_except_timing():
    p, req = api(), equipment()

    def once():
        g = FakeGen([gen(invalid_candidate(req)), gen(json.dumps(invalid_candidate(req)))])
        d = p.run_pipeline(req, g, cfg()).to_dict()
        json.dumps(d, allow_nan=False)
        return d

    a, b = once(), once()
    assert a == b
    assert a['path'] == 'fallback' and [x['status'] for x in a['attempts']] == ['rejected', 'rejected']
    assert a['attempts'][0]['errors'][0] == {'code': 'ungrounded_number', 'field': 'evidence', 'claim': 0,
                                             'value': '76'}


def test_secrets_redacted_and_metrics_sanitized():
    p, req = api(), equipment()
    err = p.GenerationError('http', 'HTTP 401 Authorization: Bearer sk-SECRET123 http://u:pw0rd@host/v1?api_key=XYZ987')
    g = FakeGen([err, gen(valid_candidate(req), tokens_per_sec=float('inf'), prompt_tokens=-1,
                          completion_tokens=True)])
    run = p.run_pipeline(req, g, cfg())
    text = json.dumps(run.to_dict(), allow_nan=False)
    for secret in ('sk-SECRET123', 'pw0rd', 'XYZ987'):
        assert secret not in text
        assert all(secret not in e for e in g.calls[1]['errors'])
    assert run.path == 'retry'
    assert run.tokens_per_sec is None and run.prompt_tokens is None and run.completion_tokens is None
    assert 'reference' not in text
    prepared = normalize_packet(req)
    assert all(i in prepared.content for e in run.assessment['evidence'] for i in e['ids'])


@pytest.mark.parametrize('detail, secret', [
    ('{"api_key": "sk-abc123"}', 'sk-abc123'),
    ("{'password': 'hunter2'}", 'hunter2'),
    ('Authorization: Basic dXNlcjpwYXNz', 'dXNlcjpwYXNz'),
    ('authorization="Digest c2VjcmV0LWRpZ2VzdA"', 'c2VjcmV0LWRpZ2VzdA'),
    ('"token":"tok-9f8e7d"', 'tok-9f8e7d'),
    ('x-api-key: k-5551234', 'k-5551234'),
    ('Bearer sk-SECRET123', 'sk-SECRET123'),
])
def test_redact_covers_quoted_keys_and_auth_schemes(detail, secret):
    p = api()
    out = p.redact('http 401 ' + detail)
    assert secret not in out and '[REDACTED]' in out


def test_raw_first_attempt_recorded_separately_from_final():
    p, req = api(), equipment()
    g = FakeGen([gen(invalid_candidate(req), tokens_per_sec=30.0, completion_tokens=80),
                 gen(invalid_candidate(req), tokens_per_sec=31.0, completion_tokens=81)])
    run = p.run_pipeline(req, g, cfg())
    d = run.to_dict()
    assert d['path'] == 'fallback' and d['model'] == 'template'
    assert [x['tokens_per_sec'] for x in d['attempts']] == [30.0, 31.0]
    assert [x['model'] for x in d['attempts']] == ['fake-model', 'fake-model']
    assert d['attempts'][0]['errors'] and d['final_errors'] == []
    assert d['tokens_per_sec'] is None and d['completion_tokens'] == 161
