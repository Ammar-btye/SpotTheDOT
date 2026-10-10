"""Static checks on config.yaml (no proxy started): the routing rules the README promises, and that every
os.environ/NAME it reads is produced by serve.build_env (a drift guard between the two files)."""
import re
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import serve  # noqa: E402

CONFIG = yaml.safe_load((HERE / "config.yaml").read_text())
MODELS = {m["model_name"]: m for m in CONFIG["model_list"]}
ALIASES = {"system2", "system2-vision", "system1", "embed"}
ENV_REF = re.compile(r"^os\.environ/([A-Z0-9_]+)$")


def _walk(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, path + (str(k),))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, path + (str(i),))
    else:
        yield path, node


def test_exactly_the_four_aliases():
    assert set(MODELS) == ALIASES and len(CONFIG["model_list"]) == len(ALIASES)   # one deployment per alias


@pytest.mark.parametrize("alias", sorted(ALIASES))
def test_every_alias_has_its_own_timeout_and_no_retries(alias):
    params = MODELS[alias]["litellm_params"]
    assert ENV_REF.match(str(params.get("timeout", ""))), "%s has no per-alias timeout" % alias
    assert params.get("max_retries") == 0
    assert params.get("api_base", "").startswith("os.environ/GATEWAY_")


def test_timeouts_are_distinct_per_alias():
    refs = [MODELS[a]["litellm_params"]["timeout"] for a in sorted(ALIASES)]
    assert len(set(refs)) == len(refs)


def test_no_fallbacks_retries_or_cooldowns_anywhere():
    keys = {k for p, _ in _walk(CONFIG) for k in p}
    assert not {k for k in keys if "fallback" in k.lower()}, "a fallback model would hide a failed System 2 call"
    assert CONFIG["litellm_settings"]["num_retries"] == 0
    assert CONFIG["router_settings"]["num_retries"] == 0
    assert CONFIG["router_settings"]["disable_cooldowns"] is True


def test_params_reach_llama_server_unchanged_and_no_telemetry():
    assert CONFIG["litellm_settings"]["drop_params"] is False     # json_schema / chat_template_kwargs must pass
    assert CONFIG["litellm_settings"]["telemetry"] is False
    gs = CONFIG["general_settings"]
    assert gs["store_model_in_db"] is False and gs["disable_spend_logs"] is True
    assert "database_url" not in {k.lower() for k in gs}


def test_hidden_aliases_point_at_real_models():
    for name, spec in CONFIG["router_settings"].get("model_group_alias", {}).items():
        assert spec["model"] in MODELS, name
        assert spec.get("hidden") is True, "%s would show up in /v1/models" % name


def test_custom_provider_handler_exists():
    for entry in CONFIG["litellm_settings"]["custom_provider_map"]:
        module, attr = entry["custom_handler"].rsplit(".", 1)
        assert (HERE / ("%s.py" % module)).is_file()
        assert re.search(r"^%s\s*=" % re.escape(attr), (HERE / ("%s.py" % module)).read_text(), re.M)
    providers = {e["provider"] for e in CONFIG["litellm_settings"]["custom_provider_map"]}
    assert MODELS["system1"]["litellm_params"]["model"].split("/")[0] in providers


def test_every_env_var_the_config_reads_is_set_by_serve():
    refs = {m.group(1) for _, v in _walk(CONFIG) if isinstance(v, str) for m in [ENV_REF.match(v)] if m}
    env = serve.build_env({"LITELLM_MASTER_KEY": "sk-gateway-test-key-0001"})
    missing = refs - set(env) - {"LITELLM_MASTER_KEY"}            # the master key comes from the caller's env
    assert not missing, "config.yaml reads %s but serve.build_env never sets them" % sorted(missing)
    unused = {k for k in env if k.startswith("GATEWAY_")} - refs
    assert not unused, "serve.build_env derives %s but config.yaml never reads them" % sorted(unused)
