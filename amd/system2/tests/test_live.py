"""Live /v1/assess wiring (analyst.live): the checked pipeline behind the HTTP API.

These are REGRESSION tests only. Every generator here is a scripted fake or a local ThreadingHTTPServer pretending
to be llama-server; no model, GPU or AMD box is involved, so nothing here is live AMD evidence. Apps are built with
create_app(api_key=KEY, assessor=LiveAssessor(...)), never from the environment, so a developer shell with live
SYSTEM2_* variables cannot leak in.
"""
import copy
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / 'data' / 'dev_packets.json'
SERVE = ROOT / 'scripts' / 'serve.py'
INSUFFICIENT = ROOT / 'fixtures' / 'backend' / 'insufficient_context.json'
KEY = 'live-test-key-0123456789abcdef'
URL = 'http://127.0.0.1:18080'
LIVE_ENV = ('SYSTEM2_LLAMA_URL', 'SYSTEM2_MODEL', 'SYSTEM2_CACHE_DIR')

from analyst.api import create_app  # noqa: E402
from analyst.backend_contract import BackendAssessResponse  # noqa: E402
from analyst.dataset import load_dataset  # noqa: E402
from analyst.generation import LlamaGenerator  # noqa: E402
from analyst.live import LiveAssessor, assessor_from_env, to_response  # noqa: E402
from analyst.packet import normalize_packet  # noqa: E402
from analyst.pipeline import Generation, GenerationError, PipelineConfig  # noqa: E402
from analyst.prompts import example_output  # noqa: E402


# ── helpers (copied from test_pipeline.py / test_generation.py, not imported) ─────────────────

class FakeGen:
    """Scripted generator; each outcome is a Generation, an exception, or a callable(packet) -> Generation."""

    def __init__(self, outcomes):
        self.outcomes, self.calls = list(outcomes), []

    def __call__(self, packet, errors=(), timeout_s=None):
        self.calls.append({'errors': errors, 'timeout_s': timeout_s, 'content': dict(packet.content)})
        out = self.outcomes[min(len(self.calls), len(self.outcomes)) - 1]
        if isinstance(out, BaseException):
            raise out
        return out(packet) if callable(out) else out


def case(category='equipment'):
    return next(c for c in load_dataset(DATA) if c.category == category)


def equipment_json():
    return case().to_dict()['request']


def gen(obj, **kw):
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return Generation(text=text, model=kw.pop('model', 'fake-model'), **kw)


def valid_candidate(req):
    prepared = normalize_packet(req)
    return {'evidence': [{'claim': 'Visual score was 75 with a HIGH severity defect.', 'ids': ['F2', 'F3']}],
            'answer': 'Visual score was 75.', 'question': prepared.question,
            'recommended_action': 'SCHEDULE_MAINTENANCE', 'confidence': 'medium', 'insufficient_context': False}


def invalid_candidate(req):
    bad = valid_candidate(req)
    bad['evidence'][0]['claim'] = 'Visual score was 76.'
    return bad


def good(**kw):
    return gen(valid_candidate(case().request), **kw)


def bad():
    return gen(invalid_candidate(case().request))


def live_client(fake, cache=None):
    assessor = LiveAssessor(fake, 'fake-model', PipelineConfig(deadline_s=15.0), cache=cache)
    return TestClient(create_app(api_key=KEY, assessor=assessor))


def post(client, body, key=KEY):
    headers = {'X-API-Key': key} if key is not None else {}
    return client.post('/v1/assess', json=body, headers=headers)


# ── tracer: live /v1/assess through the checked pipeline ─────────────────────────────────────

def test_live_assess_returns_llm_with_metadata():
    fake = FakeGen([good(model='qwen-served', tokens_per_sec=41.5)])
    r = post(live_client(fake), equipment_json())
    assert r.status_code == 200, r.text
    out = BackendAssessResponse.model_validate(r.json())
    assert out.path == 'llm' and out.model == 'qwen-served'
    assert out.tokens_per_sec == 41.5
    assert type(r.json()['latency_ms']) is int and out.latency_ms >= 0
    assert r.headers['X-System2-Cache'] == 'off'
    assert len(fake.calls) == 1


def test_invalid_then_valid_is_retry():
    fake = FakeGen([bad(), good()])
    r = post(live_client(fake), equipment_json())
    assert r.status_code == 200 and r.json()['path'] == 'retry'
    assert len(fake.calls) == 2 and fake.calls[1]['errors']


@pytest.mark.parametrize('outcomes', [
    lambda: [bad(), bad()],
    lambda: [GenerationError('timeout', 'slow'), GenerationError('timeout', 'slow')],
], ids=['two_invalid', 'two_timeouts'])
def test_two_failures_fall_back_to_template(outcomes):
    fake = FakeGen(outcomes())
    r = post(live_client(fake), equipment_json())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['path'] == 'fallback' and body['model'] == 'template' and body['tokens_per_sec'] is None
    assert len(fake.calls) == 2


def test_insufficient_context_never_generates():
    req = json.loads(INSUFFICIENT.read_text(encoding='utf-8'))['request']
    fake = FakeGen([good()])
    r = post(live_client(fake), req)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['path'] == 'insufficient_context' and body['evidence'] == []
    assert body['recommended_action'] == 'MANUAL_REVIEW'
    assert fake.calls == []


@pytest.mark.parametrize('key', [None, 'wrong-key-0123456789abcdef'], ids=['missing', 'wrong'])
def test_key_checked_before_generation(key):
    fake = FakeGen([good()])
    r = post(live_client(fake), equipment_json(), key=key)
    assert r.status_code == 401
    assert fake.calls == []


def test_malformed_consumed_value_422_before_generation():
    req = copy.deepcopy(equipment_json())
    req['context']['allowed_actions'] = 5
    fake = FakeGen([good()])
    r = post(live_client(fake), req)
    assert r.status_code == 422
    assert fake.calls == []


def test_live_health_reports_model_not_secrets():
    assessor = LiveAssessor(LlamaGenerator(URL, model='qwen-live'), 'qwen-live')
    r = TestClient(create_app(api_key=KEY, assessor=assessor)).get('/health')
    assert r.status_code == 200
    assert r.json()['mode'] == 'live' and r.json()['model'] == 'qwen-live'
    assert KEY not in r.text and '127.0.0.1' not in r.text and '18080' not in r.text


def test_stub_health_and_assess_unchanged():
    c = TestClient(create_app(api_key=KEY))
    h = c.get('/health').json()
    assert set(h) == {'status', 'mode', 'contract_version'} and h['mode'] == 'stub'
    r = post(c, equipment_json())
    assert r.status_code == 200 and r.json()['path'] == 'stub'
    assert 'X-System2-Cache' not in r.headers


def test_to_response_matches_flat_contract():
    from analyst.pipeline import run_pipeline
    run = run_pipeline(case().request, FakeGen([good()]), PipelineConfig())
    flag_id = case().prepared.flag_id
    out = to_response(run, flag_id)
    assert out.path == 'llm' and out.flag_id == flag_id and out.model == 'fake-model'
    assert out.evidence[0].ids == ['F2', 'F3']


# ── assessor_from_env ────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('env', [{}, {'SYSTEM2_LLAMA_URL': ''}, {'SYSTEM2_LLAMA_URL': '   ', 'SYSTEM2_MODEL': 'm'}],
                         ids=['absent', 'empty', 'blank'])
def test_env_without_url_is_stub(env):
    assert assessor_from_env(env) is None


def test_env_url_without_model_fails():
    with pytest.raises(RuntimeError, match='SYSTEM2_MODEL'):
        assessor_from_env({'SYSTEM2_LLAMA_URL': URL})
    with pytest.raises(RuntimeError, match='SYSTEM2_MODEL'):
        assessor_from_env({'SYSTEM2_LLAMA_URL': URL, 'SYSTEM2_MODEL': '  '})


def test_env_non_http_url_fails_without_credentials():
    with pytest.raises(RuntimeError) as err:
        assessor_from_env({'SYSTEM2_LLAMA_URL': 'ftp://user:hunter2-secret@box:21', 'SYSTEM2_MODEL': 'm'})
    assert 'hunter2-secret' not in str(err.value)


def test_env_live_builds_llama_generator_without_network():
    a = assessor_from_env({'SYSTEM2_LLAMA_URL': ' http://127.0.0.1:9 ', 'SYSTEM2_MODEL': 'qwen3.5-9b-q4km'})
    assert isinstance(a, LiveAssessor) and isinstance(a.generator, LlamaGenerator)
    assert a.generator.endpoint.endswith('/v1/chat/completions')
    assert a.generator.model == 'qwen3.5-9b-q4km' == a.model
    assert a.config.deadline_s == 15.0 and a.config.catalog is not None


# ── end to end over HTTP to a local fake llama-server (regression only, not AMD evidence) ────

def envelope(content, finish='stop', completion=120, prompt=900, speed=35.6, model='qwen-fake'):
    body = {'model': model, 'choices': [{'index': 0, 'finish_reason': finish,
                                          'message': {'role': 'assistant', 'content': content}}],
            'usage': {'prompt_tokens': prompt, 'completion_tokens': completion}}
    if speed is not None:
        body['timings'] = {'predicted_per_second': speed, 'prompt_n': prompt, 'predicted_n': completion}
    return body


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            raw = self.rfile.read(int(self.headers['Content-Length']))
            self.server.requests.append({'path': self.path, 'body': json.loads(raw)})
            data = json.dumps(self.server.reply).encode('utf-8')
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    http.daemon_threads = True
    http.requests, http.reply = [], None
    worker = threading.Thread(target=http.serve_forever, kwargs={'poll_interval': 0.02}, daemon=True)
    worker.start()
    yield http, 'http://127.0.0.1:%d' % http.server_port
    http.shutdown()
    http.server_close()
    worker.join()


def test_live_request_over_http_to_fake_llama_server(server):
    http, url = server
    c = case()
    http.reply = envelope(json.dumps(example_output(c.prepared), ensure_ascii=False), speed=27.25)
    assessor = LiveAssessor(LlamaGenerator(url, model='qwen-fake'), 'qwen-fake')
    r = post(TestClient(create_app(api_key=KEY, assessor=assessor)), c.to_dict()['request'])
    assert r.status_code == 200, r.text
    body = BackendAssessResponse.model_validate(r.json())
    assert body.path == 'llm' and body.model == 'qwen-fake' and body.tokens_per_sec == 27.25
    assert len(http.requests) == 1 and http.requests[0]['path'] == '/v1/chat/completions'
    assert http.requests[0]['body']['model'] == 'qwen-fake'


# ── serve.py fails closed on an incomplete live config ───────────────────────────────────────

def test_serve_live_without_model_exits_2():
    env = {k: v for k, v in os.environ.items()
           if k not in {'AMD_API_KEY', 'SYSTEM2_API_KEY', 'SYSTEM2_HOST', 'SYSTEM2_PORT', *LIVE_ENV}}
    env.update(SYSTEM2_API_KEY=KEY, SYSTEM2_LLAMA_URL='http://127.0.0.1:9')
    r = subprocess.run([sys.executable, str(SERVE), '--port', '0'], env=env, capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert 'SYSTEM2_MODEL' in r.stderr
    assert KEY not in r.stdout + r.stderr
