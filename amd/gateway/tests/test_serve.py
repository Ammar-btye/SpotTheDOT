"""serve.build_env: defaults, /v1 derivation, vision fallback, master-key and DB guards."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import serve  # noqa: E402

KEY = "sk-gateway-test-key-0001"


def test_defaults_are_native_localhost():
    env = serve.build_env({"LITELLM_MASTER_KEY": KEY})
    assert env["GATEWAY_SYSTEM2_API_BASE"] == "http://127.0.0.1:8080/v1"
    assert env["GATEWAY_VISION_API_BASE"] == "http://127.0.0.1:8080/v1"      # same llama-server by default
    assert env["GATEWAY_SYSTEM1_API_BASE"] == "http://127.0.0.1:8082"         # Laya has no /v1 base
    assert env["GATEWAY_EMBED_API_BASE"] == "http://127.0.0.1:8081/v1"
    assert env["GATEWAY_LLAMA_KEY"] == env["GATEWAY_EMBED_KEY"] == serve.NO_KEY
    assert (env["GATEWAY_SYSTEM2_TIMEOUT_S"], env["GATEWAY_SYSTEM1_TIMEOUT_S"]) == ("15.0", "10.0")
    assert env["LITELLM_TELEMETRY"] == "False" and env["LITELLM_LOCAL_MODEL_COST_MAP"] == "True"


def test_urls_and_keys_are_derived():
    env = serve.build_env({"LITELLM_MASTER_KEY": KEY, "LLAMA_URL": "http://llama:8080/",
                           "VISION_LLAMA_URL": "http://vision:8080/v1", "SYSTEM1_URL": "http://system1:8082/v1",
                           "EMBED_URL": "http://embed:8081", "LLAMA_API_KEY": "llama-secret", "SYSTEM2_TIMEOUT_S": "9"})
    assert env["GATEWAY_SYSTEM2_API_BASE"] == "http://llama:8080/v1"
    assert env["GATEWAY_VISION_API_BASE"] == "http://vision:8080/v1"
    assert env["GATEWAY_SYSTEM1_API_BASE"] == "http://system1:8082"
    assert env["GATEWAY_LLAMA_KEY"] == "llama-secret" and env["GATEWAY_SYSTEM2_TIMEOUT_S"] == "9.0"


def test_telemetry_cannot_be_turned_back_on():
    assert serve.build_env({"LITELLM_MASTER_KEY": KEY, "LITELLM_TELEMETRY": "True"})["LITELLM_TELEMETRY"] == "False"


@pytest.mark.parametrize("environ,needle", [
    ({}, "LITELLM_MASTER_KEY"),
    ({"LITELLM_MASTER_KEY": "short"}, "LITELLM_MASTER_KEY"),
    ({"LITELLM_MASTER_KEY": "no-sk-prefix-but-long-enough"}, "LITELLM_MASTER_KEY"),
    ({"LITELLM_MASTER_KEY": " " + KEY}, "LITELLM_MASTER_KEY"),
    ({"LITELLM_MASTER_KEY": KEY, "DATABASE_URL": "postgresql://x"}, "DATABASE_URL"),
    ({"LITELLM_MASTER_KEY": KEY, "LLAMA_URL": "llama:8080"}, "LLAMA_URL"),
    ({"LITELLM_MASTER_KEY": KEY, "SYSTEM2_TIMEOUT_S": "0"}, "SYSTEM2_TIMEOUT_S"),
    ({"LITELLM_MASTER_KEY": KEY, "SYSTEM1_TIMEOUT_S": "fast"}, "SYSTEM1_TIMEOUT_S"),
])
def test_unusable_config_is_rejected(environ, needle):
    with pytest.raises(ValueError) as err:
        serve.build_env(environ)
    assert needle in str(err.value) and KEY not in str(err.value)


def test_cli_args():
    args = serve.cli_args({"GATEWAY_PORT": "4100"})
    assert args[args.index("--port") + 1] == "4100" and args[args.index("--host") + 1] == "0.0.0.0"
    assert args[args.index("--config") + 1].endswith("config.yaml")
