"""Configuration from environment variables only (names in docs/orchestrator-contract.md "Environment")."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Tuple

CONTRACT_VERSION = "2026-10-10.orchestrator.2"
MIN_KEY_LEN = 16
MAX_TOOL_CALLS = 4          # hard cap for /v1/ask, whatever ASK_MAX_TOOL_CALLS says


def _get(env: Mapping[str, str], name: str, default: Optional[str] = None) -> Optional[str]:
    v = env.get(name)
    return v.strip() if v is not None and v.strip() != "" else default


def _float(env: Mapping[str, str], name: str, default: float) -> float:
    v = _get(env, name)
    return float(v) if v is not None else default


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    v = _get(env, name)
    return int(v) if v is not None else default


def _flag(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    v = _get(env, name)
    return default if v is None else v.lower() in ("1", "true", "yes", "on")


def _url(env: Mapping[str, str], name: str, default: str) -> Optional[str]:
    """Unset -> default; set but empty -> None (the dependency is turned off)."""
    if name in env and env[name].strip() == "":
        return None
    return (_get(env, name, default) or "").rstrip("/") or None


def key_problem(key: str) -> Optional[str]:
    """Why `key` cannot be the shared secret, or None. Never includes the key (same rules as System 2)."""
    if len(key) < MIN_KEY_LEN:
        return "it has fewer than %d characters" % MIN_KEY_LEN
    if key != key.strip():
        return "it has leading or trailing whitespace"
    if not key.isascii():
        return "it has non-ASCII characters"
    if not key.isprintable():
        return "it has non-printable characters"
    return None


def _default_demo_dir() -> str:
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "web" / "public" / "kit" / "inspection"
        if cand.is_dir():
            return str(cand)
    return "/app/demo-images"


@dataclass(frozen=True)
class Settings:
    api_key: Optional[str]
    allow_no_auth: bool
    host: str
    port: int
    mcp_url: Optional[str]
    mcp_auth_token: Optional[str]
    gateway_url: Optional[str]
    gateway_key: Optional[str]
    system1_alias: str
    ask_model: str
    vision_url: Optional[str]
    vision_api_key: Optional[str]
    system2_url: Optional[str]
    system2_api_key: Optional[str]
    demo_images: bool
    demo_images_dir: str
    deadline_s: float
    context_budget_s: float
    system1_budget_s: float
    vision_budget_s: float
    system2_budget_s: float
    system2_image_budget_s: float
    vision_trust_min: float
    ocr_top_n: int
    max_image_b64: int
    ask_deadline_s: float
    ask_max_tool_calls: int
    ask_tool_allowlist: Tuple[str, ...]
    log_level: str

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Settings":
        e = os.environ if env is None else env
        gw = _url(e, "GATEWAY_URL", "http://localhost:4000")
        if gw and gw.endswith("/v1"):
            gw = gw[:-3]
        return cls(
            api_key=e.get("ORCHESTRATOR_API_KEY") or None,   # raw: surrounding whitespace is rejected, not stripped
            allow_no_auth=_flag(e, "ORCHESTRATOR_ALLOW_NO_AUTH"),
            host=_get(e, "ORCHESTRATOR_HOST", "127.0.0.1") or "127.0.0.1",
            port=_int(e, "ORCHESTRATOR_PORT", 8085),
            mcp_url=_url(e, "MCP_URL", "http://localhost:8090/mcp"),
            mcp_auth_token=_get(e, "MCP_AUTH_TOKEN"),
            gateway_url=gw,
            gateway_key=_get(e, "GATEWAY_KEY", _get(e, "LITELLM_MASTER_KEY")),
            system1_alias=_get(e, "SYSTEM1_ALIAS", "system1") or "system1",
            ask_model=_get(e, "ASK_MODEL", "system2") or "system2",
            vision_url=_url(e, "VISION_URL", "http://localhost:8084"),
            vision_api_key=_get(e, "VISION_API_KEY"),
            system2_url=_url(e, "SYSTEM2_URL", "http://localhost:8083"),
            system2_api_key=_get(e, "SYSTEM2_API_KEY", _get(e, "AMD_API_KEY")),
            demo_images=_flag(e, "DEMO_IMAGES"),
            demo_images_dir=_get(e, "DEMO_IMAGES_DIR") or _default_demo_dir(),
            deadline_s=_float(e, "ORCH_DEADLINE_S", 40.0),   # < backend REQUEST_DEADLINE_S 45
            context_budget_s=_float(e, "ORCH_CONTEXT_BUDGET_S", 15.0),
            system1_budget_s=_float(e, "ORCH_SYSTEM1_BUDGET_S", 6.0),
            vision_budget_s=_float(e, "ORCH_VISION_BUDGET_S", 12.0),
            system2_budget_s=_float(e, "ORCH_SYSTEM2_BUDGET_S", 20.0),   # System 2: 15 s generation + checks
            # with an image: System 2's SYSTEM2_IMAGE_DEADLINE_S (25 s) + checks (contract "Timeout chain")
            system2_image_budget_s=_float(e, "ORCH_SYSTEM2_IMAGE_BUDGET_S", 28.0),
            vision_trust_min=_float(e, "VISION_TRUST_MIN", 0.5),
            ocr_top_n=_int(e, "OCR_TOP_N", 8),
            max_image_b64=_int(e, "ORCH_MAX_IMAGE_B64", 12_000_000),
            ask_deadline_s=_float(e, "ASK_DEADLINE_S", 30.0),
            ask_max_tool_calls=max(1, min(MAX_TOOL_CALLS, _int(e, "ASK_MAX_TOOL_CALLS", MAX_TOOL_CALLS))),
            ask_tool_allowlist=tuple(p.strip() for p in (_get(e, "ASK_TOOL_ALLOWLIST", "search_*,get_*") or "")
                                     .split(",") if p.strip()),
            log_level=_get(e, "LOG_LEVEL", "INFO") or "INFO",
        )

    def check_auth(self) -> None:
        """RuntimeError unless a usable key is set or ORCHESTRATOR_ALLOW_NO_AUTH=1; never prints the key."""
        if self.api_key is None or self.api_key == "":
            if self.allow_no_auth:
                return
            raise RuntimeError("ORCHESTRATOR_API_KEY is not set (>= %d printable ASCII characters); set "
                               "ORCHESTRATOR_ALLOW_NO_AUTH=1 only for tests" % MIN_KEY_LEN)
        why = key_problem(self.api_key)
        if why:
            raise RuntimeError("ORCHESTRATOR_API_KEY is unusable: %s (the key is never logged)" % why)
