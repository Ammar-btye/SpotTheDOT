"""Exercise the stdlib feasibility client over a real local HTTP connection."""
import copy
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "smoke_serve", Path(__file__).resolve().parents[1] / "scripts/smoke_serve.py"
)
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.server.requests.append((self.path, json.loads(self.rfile.read(
                int(self.headers["Content-Length"])
            ))))
            body = json.dumps({"model": "fake", "choices": [{"message": {
                "content": self.server.reply
            }}], "usage": {"prompt_tokens": 10, "completion_tokens": 20}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    http.requests = []
    worker = threading.Thread(target=http.serve_forever, daemon=True)
    worker.start()
    yield http, "http://127.0.0.1:%d" % http.server_port
    http.shutdown()
    http.server_close()
    worker.join()


def valid_reply(packet):
    return {"evidence": [{"claim": "Recorded reading", "ids": [smoke.row_ids(packet)[0]]}],
            "answer": "Recorded reading", "question": "What happened?",
            "recommended_action": packet["allowed_actions"][0],
            "confidence": "medium", "insufficient_context": False}


def test_real_request_payload_and_valid_reply(server):
    http, url = server
    packet = smoke.load_packet("equipment")
    http.reply = json.dumps(valid_reply(packet))
    result = smoke.run_once(url, packet, 512, 2)
    assert result["errors"] == []
    assert result["output_tokens"] == 20
    path, body = http.requests[0]
    assert path == "/v1/chat/completions"
    assert body["max_tokens"] == 512
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    schema = body["response_format"]["json_schema"]["schema"]
    assert body["response_format"]["type"] == "json_schema"
    assert schema == smoke.schema_for(packet)
    assert schema["properties"]["recommended_action"]["enum"] == packet["allowed_actions"]
    assert schema["properties"]["evidence"]["items"]["properties"]["ids"]["items"]["enum"] == smoke.row_ids(packet)


@pytest.mark.parametrize("mutation", [
    lambda o: o.pop("answer"),
    lambda o: o.update(extra=True),
    lambda o: o.update(answer=3),
    lambda o: o.update(question=None),
    lambda o: o.update(insufficient_context="false"),
    lambda o: o.update(evidence="wrong"),
    lambda o: o.update(evidence=[None]),
    lambda o: o.update(evidence=[{}]),
    lambda o: o["evidence"][0].update(extra=True),
    lambda o: o["evidence"][0].update(claim=4),
    lambda o: o["evidence"][0].update(ids=[]),
    lambda o: o["evidence"][0].update(ids="E1"),
    lambda o: o["evidence"][0].update(ids=[{}]),
    lambda o: o["evidence"][0].update(ids=["UNKNOWN"]),
    lambda o: o.update(evidence=o["evidence"] * 6),
    lambda o: o.update(confidence="med"),
    lambda o: o.update(recommended_action="DISPATCH_TECHNICIAN"),
])
def test_schema_violations_rejected_over_http(server, mutation):
    http, url = server
    packet = smoke.load_packet("equipment")
    reply = copy.deepcopy(valid_reply(packet))
    mutation(reply)
    http.reply = json.dumps(reply)
    assert smoke.run_once(url, packet, 512, 2)["errors"]


@pytest.mark.parametrize("reply", ['{"evidence":', '[]', 'null'])
def test_truncated_or_nonobject_json_rejected(server, reply):
    http, url = server
    http.reply = reply
    assert smoke.run_once(url, smoke.load_packet("equipment"), 512, 2)["errors"]


def test_schema_does_not_require_property_order():
    packet = smoke.load_packet("equipment")
    reply = valid_reply(packet)
    assert smoke.check(dict(reversed(list(reply.items()))), packet) == []
