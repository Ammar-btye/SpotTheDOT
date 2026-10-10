"""Start the SPOT model gateway: LiteLLM proxy on GATEWAY_HOST:GATEWAY_PORT (default 0.0.0.0:4000) with config.yaml.

    LITELLM_MASTER_KEY=sk-... LLAMA_URL=http://127.0.0.1:8080 python serve.py        # native (AMD box, venv)

Why a launcher instead of bare `litellm --config`: config.yaml reads every value with os.environ/NAME, which has no
defaults and no derivation. This file fills the defaults below, derives the `/v1` api_base for each upstream
(VISION_LLAMA_URL falls back to LLAMA_URL), checks the master key, turns LiteLLM's network extras off, and then
runs the stock LiteLLM CLI in-process. Nothing else is configured here: routing, timeouts and retries live in
config.yaml.

Env (defaults are for a native run; docker-compose.yml sets service-name URLs):
  LITELLM_MASTER_KEY  required, starts with "sk-", >= 16 chars; clients send `Authorization: Bearer <key>`
  LLAMA_URL           http://127.0.0.1:8080  llama-server (Qwen3.5-9B) base URL, no /v1   -> alias system2
  VISION_LLAMA_URL    = LLAMA_URL            llama-server started with --mmproj           -> alias system2-vision
  LLAMA_API_KEY       (empty)                llama-server --api-key, if it has one
  SYSTEM1_URL         http://127.0.0.1:8082  Laya triage service                          -> alias system1
  EMBED_URL           http://127.0.0.1:8081  embedding service                            -> alias embed
  EMBED_API_KEY       (empty)
  SYSTEM2_TIMEOUT_S 15 | VISION_TIMEOUT_S 30 | SYSTEM1_TIMEOUT_S 10 | EMBED_TIMEOUT_S 10   (whole call, seconds)
  GATEWAY_HOST 0.0.0.0 | GATEWAY_PORT 4000 | GATEWAY_WORKERS 1 | GATEWAY_CONFIG ./config.yaml
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Mapping
import urllib.parse

HERE = Path(__file__).resolve().parent
MIN_KEY_LEN = 16
NO_KEY = "sk-no-key"   # the OpenAI client needs a non-empty key; llama-server without --api-key ignores it

DEFAULTS = {
    "LLAMA_URL": "http://127.0.0.1:8080",
    "SYSTEM1_URL": "http://127.0.0.1:8082",
    "EMBED_URL": "http://127.0.0.1:8081",
    "SYSTEM2_TIMEOUT_S": "15",
    "VISION_TIMEOUT_S": "30",
    "SYSTEM1_TIMEOUT_S": "10",
    "EMBED_TIMEOUT_S": "10",
    "GATEWAY_HOST": "0.0.0.0",
    "GATEWAY_PORT": "4000",
    "GATEWAY_WORKERS": "1",
}

# LiteLLM extras we never want: no DB, no admin UI, no telemetry, no cost-map download at startup, no .env loading.
QUIET = {
    "LITELLM_TELEMETRY": "False",
    "LITELLM_LOCAL_MODEL_COST_MAP": "True",
    "DISABLE_ADMIN_UI": "True",
    "LITELLM_MODE": "PRODUCTION",
    "LITELLM_LOG": "ERROR",
}
FORBIDDEN = ("DATABASE_URL",)   # LiteLLM would start Prisma + its UI/spend tables if this were set


def _base(name: str, url: str) -> str:
    """http(s)://host[:port][/path] -> the same with exactly one trailing /v1 (LiteLLM's openai api_base)."""
    url = (url or "").strip().rstrip("/")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("%s must be http(s)://host[:port], got %r" % (name, url))
    return url if url.endswith("/v1") else url + "/v1"


def _seconds(name: str, value: str) -> str:
    try:
        v = float(value)
    except ValueError:
        raise ValueError("%s must be a number of seconds, got %r" % (name, value)) from None
    if not 0 < v <= 600:
        raise ValueError("%s must be in (0, 600], got %r" % (name, value))
    return repr(v)


def build_env(environ: Mapping[str, str]) -> Dict[str, str]:
    """The variables config.yaml reads (GATEWAY_*), plus QUIET; ValueError on an unusable config."""
    env = {k: (environ.get(k) or "").strip() or v for k, v in DEFAULTS.items()}
    key = environ.get("LITELLM_MASTER_KEY") or ""
    if not key.startswith("sk-") or len(key) < MIN_KEY_LEN or key != key.strip():
        raise ValueError('LITELLM_MASTER_KEY must start with "sk-", have at least %d characters and no '
                         "surrounding whitespace (the key is never logged)" % MIN_KEY_LEN)
    for name in FORBIDDEN:
        if environ.get(name):
            raise ValueError("%s is set; the gateway runs without a database (unset it for this process)" % name)
    vision = (environ.get("VISION_LLAMA_URL") or "").strip() or env["LLAMA_URL"]
    out = {k: (environ.get(k) or "").strip() or v for k, v in QUIET.items()}
    out["LITELLM_TELEMETRY"] = "False"
    out.update({
        "GATEWAY_SYSTEM2_API_BASE": _base("LLAMA_URL", env["LLAMA_URL"]),
        "GATEWAY_VISION_API_BASE": _base("VISION_LLAMA_URL", vision),
        "GATEWAY_SYSTEM1_API_BASE": _base("SYSTEM1_URL", env["SYSTEM1_URL"])[:-3],   # Laya: no /v1 suffix
        "GATEWAY_EMBED_API_BASE": _base("EMBED_URL", env["EMBED_URL"]),
        "GATEWAY_LLAMA_KEY": (environ.get("LLAMA_API_KEY") or "").strip() or NO_KEY,
        "GATEWAY_EMBED_KEY": (environ.get("EMBED_API_KEY") or "").strip() or NO_KEY,
        "GATEWAY_SYSTEM2_TIMEOUT_S": _seconds("SYSTEM2_TIMEOUT_S", env["SYSTEM2_TIMEOUT_S"]),
        "GATEWAY_VISION_TIMEOUT_S": _seconds("VISION_TIMEOUT_S", env["VISION_TIMEOUT_S"]),
        "GATEWAY_SYSTEM1_TIMEOUT_S": _seconds("SYSTEM1_TIMEOUT_S", env["SYSTEM1_TIMEOUT_S"]),
        "GATEWAY_EMBED_TIMEOUT_S": _seconds("EMBED_TIMEOUT_S", env["EMBED_TIMEOUT_S"]),
    })
    return out


def cli_args(environ: Mapping[str, str]) -> list:
    host = (environ.get("GATEWAY_HOST") or "").strip() or DEFAULTS["GATEWAY_HOST"]
    port = (environ.get("GATEWAY_PORT") or "").strip() or DEFAULTS["GATEWAY_PORT"]
    workers = (environ.get("GATEWAY_WORKERS") or "").strip() or DEFAULTS["GATEWAY_WORKERS"]
    config = (environ.get("GATEWAY_CONFIG") or "").strip() or str(HERE / "config.yaml")
    return ["--config", config, "--host", host, "--port", port, "--num_workers", workers]


def main() -> None:
    try:
        derived = build_env(os.environ)
    except ValueError as exc:
        sys.exit("gateway config error: %s" % exc)
    os.environ.update(derived)
    # config.yaml names its custom handler as `laya_provider.laya_provider`; LiteLLM loads it relative to the
    # config file, but keep this folder importable for workers too
    sys.path.insert(0, str(HERE))
    os.environ["PYTHONPATH"] = os.pathsep.join(p for p in (str(HERE), os.environ.get("PYTHONPATH", "")) if p)
    from litellm.proxy.proxy_cli import run_server   # imported after the env is final
    run_server.main(args=cli_args(os.environ), prog_name="litellm", standalone_mode=True)


if __name__ == "__main__":
    main()
