"""Real-process smoke tests for scripts/serve.py: loopback default, fail-closed key check, 200/401 over a real socket.

Run: uv run --no-project --with-requirements amd/system2/requirements.txt python -m pytest amd/system2/tests -q
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
import pytest  # noqa: E402

from analyst.api import FIXTURES, KEY_HEADER  # noqa: E402
from analyst.backend_contract import BackendAssessResponse as AssessResponse  # noqa: E402
from scripts.serve import build_parser  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SERVE = ROOT / "scripts" / "serve.py"
TEST_KEY = "test-key-0123456789abcdef0123456"     # 32 characters
assert len(TEST_KEY) == 32


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _env(key=None) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in {"AMD_API_KEY", "SYSTEM2_API_KEY", "SYSTEM2_HOST", "SYSTEM2_PORT"}}
    if key is not None:
        env["AMD_API_KEY"] = key
    return env


def test_default_host_is_loopback():
    args = build_parser().parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8083


def test_environment_defaults_and_cli_override(monkeypatch):
    monkeypatch.setenv("SYSTEM2_HOST", "0.0.0.0")
    monkeypatch.setenv("SYSTEM2_PORT", "8100")
    args = build_parser().parse_args([])
    assert (args.host, args.port) == ("0.0.0.0", 8100)
    args = build_parser().parse_args(["--host", "127.0.0.1", "--port", "8083"])
    assert (args.host, args.port) == ("127.0.0.1", 8083)


def test_conflicting_keys_fail_closed():
    env = _env(TEST_KEY)
    env["SYSTEM2_API_KEY"] = "different-test-key-0123456789"
    r = subprocess.run([sys.executable, str(SERVE)], env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 2 and "disagree" in r.stderr
    assert TEST_KEY not in r.stdout + r.stderr
    assert env["SYSTEM2_API_KEY"] not in r.stdout + r.stderr


def test_serve_refuses_without_key():
    r = subprocess.run([sys.executable, str(SERVE), "--port", str(_free_port())],
                       capture_output=True, text=True, timeout=30, env=_env())
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert "AMD_API_KEY" in r.stderr


def test_serve_refuses_short_key():
    r = subprocess.run([sys.executable, str(SERVE), "--port", str(_free_port())],
                       capture_output=True, text=True, timeout=30, env=_env("short-key"))
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert "AMD_API_KEY" in r.stderr
    assert "short-key" not in r.stderr + r.stdout


@pytest.mark.parametrize("bad", [" " * 20, TEST_KEY + " ", "  " + TEST_KEY, TEST_KEY + "\t", "clé-secrète-0123456789"],
                         ids=["whitespace_only", "trail_space", "lead_space", "trail_tab", "non_ascii"])
def test_serve_refuses_unusable_key(bad):
    r = subprocess.run([sys.executable, str(SERVE), "--port", str(_free_port())],
                       capture_output=True, text=True, timeout=30, env=_env(bad))
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert "AMD_API_KEY" in r.stderr
    out = r.stdout + r.stderr
    assert repr(bad) not in out and (not bad.strip() or bad.strip() not in out)


def test_serve_end_to_end():
    port = _free_port()
    base = "http://127.0.0.1:%d" % port
    req = json.loads((FIXTURES / "backend" / "equipment.json").read_text(encoding="utf-8"))["request"]
    proc = subprocess.Popen([sys.executable, str(SERVE), "--port", str(port), "--log-level", "warning"],
                            env={**_env(), "SYSTEM2_API_KEY": TEST_KEY}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        health = None
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and proc.poll() is None:
            try:
                health = httpx.get(base + "/health", timeout=2)
                break
            except httpx.TransportError:
                time.sleep(0.2)
        assert health is not None, "stub did not come up on %s (exit %r)" % (base, proc.poll())
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        ok = httpx.post(base + "/v1/assess", json=req, headers={KEY_HEADER: TEST_KEY}, timeout=10)
        assert ok.status_code == 200, ok.text
        body = AssessResponse.model_validate(ok.json())
        assert body.model == "stub"
        assert body.answer and body.evidence

        anon = httpx.post(base + "/v1/assess", json=req, timeout=10)
        assert anon.status_code == 401
    finally:
        proc.terminate()
        out, err = proc.communicate(timeout=10)
    assert TEST_KEY not in out + err, "the key must never be logged"
