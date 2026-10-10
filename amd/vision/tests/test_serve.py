import subprocess
import sys
from pathlib import Path

SERVE = Path(__file__).resolve().parents[1] / "scripts" / "serve.py"


def test_bad_setting_exits_2_before_binding():
    env = {"VISION_API_KEY": "short", "PATH": "/usr/bin:/bin"}
    p = subprocess.run([sys.executable, str(SERVE), "--port", "0"], env=env, capture_output=True, text=True, timeout=60)
    assert p.returncode == 2 and "VISION_API_KEY" in p.stderr and "short" not in p.stderr


def test_missing_key_exits_2_before_binding():
    p = subprocess.run([sys.executable, str(SERVE), "--port", "0"], env={"PATH": "/usr/bin:/bin"}, capture_output=True,
                       text=True, timeout=60)
    assert p.returncode == 2 and "VISION_API_KEY is not set" in p.stderr
