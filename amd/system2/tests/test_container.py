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
# Phase-2 offline modules must import and load their data in the image layout (/app/analyst, kit at SPOT_KIT_DIR).
OFFLINE_IMPORTS = ("import analyst.evaluation, analyst.generation, analyst.pipeline\n"
                   "from analyst.grounding import default_catalog\n"
                   "from analyst.prompts import load_examples\n"
                   "assert default_catalog().entities and len(load_examples()) >= 3\n"
                   "print('offline-ok')")


def test_offline_modules_import_in_image_layout(tmp_path):
    """Same layout as the Dockerfile (analyst/ and data/ under /app, no repo above): no IndexError at import."""
    import shutil
    app = tmp_path / "app"
    shutil.copytree(ROOT / "analyst", app / "analyst", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "data", app / "data")
    env = dict(os.environ, SPOT_KIT_DIR=str(ROOT.parents[0] / "system1" / "data" / "kit"), PYTHONPATH="")
    run = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, %r)\n" % str(app)
                          + OFFLINE_IMPORTS], capture_output=True, text=True, timeout=120, env=env, cwd=str(app))
    assert run.returncode == 0 and run.stdout.strip() == "offline-ok", run.stderr[-2000:]
    env.pop("SPOT_KIT_DIR")
    run = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, %r)\n" % str(app)
                          + "import analyst.evaluation\nfrom analyst.grounding import default_catalog\n"
                          "default_catalog()"], capture_output=True, text=True, timeout=120, env=env, cwd=str(app))
    assert run.returncode != 0 and "set SPOT_KIT_DIR" in run.stderr and "IndexError" not in run.stderr


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
        kit = ROOT.parents[0] / "system1" / "data" / "kit"
        out = docker("run", "--rm", "-v", "%s:/app/kit:ro" % kit, tag, "python", "-c", OFFLINE_IMPORTS, timeout=60)
        assert out.endswith("offline-ok"), out
        while time.monotonic() < deadline:
            if docker("inspect", "--format", "{{.State.Health.Status}}", name) == "healthy":
                break
            time.sleep(0.5)
        else:
            pytest.fail("image HEALTHCHECK did not become healthy")
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)
        subprocess.run(["docker", "image", "rm", "-f", tag], capture_output=True, timeout=30)
