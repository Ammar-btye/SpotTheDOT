import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # orchestrator package
sys.path.insert(0, str(HERE))         # fakes

from fastapi.testclient import TestClient  # noqa: E402

from fakes import World, settings_env  # noqa: E402
from orchestrator.app import build_chat, create_app  # noqa: E402
from orchestrator.config import Settings  # noqa: E402


@pytest.fixture
def world() -> World:
    return World()


@pytest.fixture
def make_client(world):
    """make_client(**env_overrides) -> a started TestClient wired to the fake world."""
    opened = []

    def make(**env):
        s = Settings.from_env(settings_env(**env))
        app = create_app(s, http=world.http(), chat=build_chat(s, world.http2()))
        c = TestClient(app, headers={"X-API-Key": s.api_key or ""})
        c.__enter__()
        opened.append(c)
        return c

    yield make
    for c in opened:
        c.__exit__(None, None, None)
