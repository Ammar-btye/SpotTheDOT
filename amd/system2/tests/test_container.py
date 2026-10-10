"""Opt-in live Docker proof. An enabled check fails when Docker is unavailable."""
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import pytest

from analyst.backend_contract import BackendAssessResponse

ROOT = Path(__file__).resolve().parents[1]
KEY = "container-test-only-0123456789abcdef"


@pytest.mark.skipif(os.environ.get("SYSTEM2_CONTAINER_TEST") != "1", reason="opt in with SYSTEM2_CONTAINER_TEST=1")
def test_real_container():
    tag = "spot-system2-test:" + uuid.uuid4().hex
    name = "spot-system2-test-" + uuid.uuid4().hex

    def docker(*args, timeout=120):
        return subprocess.run(["docker", *args], check=True, capture_output=True, text=True,
                              timeout=timeout).stdout.strip()

    docker("info", timeout=20)
    try:
        docker("build", "-t", tag, str(ROOT), timeout=300)
        env = os.environ.copy()
        env["SYSTEM2_API_KEY"] = KEY
        subprocess.run(["docker", "run", "-d", "--name", name, "-e", "SYSTEM2_API_KEY",
                        "-p", "127.0.0.1::8083", tag], env=env, check=True,
                       capture_output=True, text=True, timeout=30)
        port = docker("port", name, "8083/tcp").split(":")[-1]
        base = "http://127.0.0.1:" + port
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                if httpx.get(base + "/health", timeout=2).status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(0.25)
        else:
            pytest.fail("container health endpoint did not become ready")
        req = json.loads((ROOT / "fixtures/backend/equipment.json").read_text())["request"]
        r = httpx.post(base + "/v1/assess", json=req, headers={"X-API-Key": KEY}, timeout=10)
        assert r.status_code == 200, r.text
        out = BackendAssessResponse.model_validate(r.json())
        assert out.model == "stub" and out.evidence and out.answer
        assert httpx.post(base + "/v1/assess", json=req, timeout=10).status_code == 401
        assert int(docker("exec", name, "id", "-u")) != 0
        while time.monotonic() < deadline:
            if docker("inspect", "--format", "{{.State.Health.Status}}", name) == "healthy":
                break
            time.sleep(0.5)
        else:
            pytest.fail("image HEALTHCHECK did not become healthy")
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)
        subprocess.run(["docker", "image", "rm", "-f", tag], capture_output=True, timeout=30)
