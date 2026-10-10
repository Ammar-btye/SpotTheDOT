"""Contract check against the REAL System 2 app (amd/system2, stub mode, in-process over ASGI): the orchestrator's
/v1/assess request (flag, reasons, context incl. live system1 rows, vision V# rows, OCR, image_b64) must pass System 2's
strict validation. Skipped when amd/system2 cannot be imported (e.g. a separate checkout of this folder)."""
import copy
import sys
from pathlib import Path

import httpx
import pytest

from fakes import ESCALATED_PACKET, TINY_JPEG

S2_ROOT = Path(__file__).resolve().parents[2] / "system2"
S2_KEY = "s2-key-0123456789"


@pytest.fixture
def real_system2(world):
    sys.path.insert(0, str(S2_ROOT))
    try:
        from analyst.api import create_app as s2_app   # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        pytest.skip("amd/system2 not importable: %s" % exc)
    finally:
        sys.path.remove(str(S2_ROOT))
    app = s2_app(api_key=S2_KEY)

    async def handler(body, headers):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s2") as c:
            r = await c.post("/v1/assess", json=body, headers={"X-API-Key": headers.get("x-api-key", "")})
        return r.status_code, r.json(), {}

    world.system2_handler = handler
    return app


def test_full_request_with_vision_passes_real_system2(make_client, world, real_system2):
    out = make_client().post("/v1/assess", json={"flag_id": 42, "image_b64": TINY_JPEG}).json()
    assert world.of("system2"), "System 2 was not called"
    assert out["source"] == "system2", out.get("fallback_reason")
    assert out["system2"]["path"] in ("stub", "llm", "retry", "fallback", "insufficient_context")
    assert out["system2"]["flag_id"] == 42


def test_live_system1_rows_pass_real_system2(make_client, world, real_system2):
    world.packet = copy.deepcopy(ESCALATED_PACKET)
    del world.packet["system1"]
    out = make_client().post("/v1/assess", json={"flag_id": 42}).json()
    assert out["system1"]["source"] == "gateway"
    # accepted (no 422); the stub may answer with its checked template, which is labelled system2_template (A-8)
    assert [t for t in out["trace"] if t["node"] == "system2"][0]["status"] == "ok", out.get("fallback_reason")
    assert out["source"] in ("system2", "system2_template") and out["system2"]["flag_id"] == 42
    if out["system2"]["path"] in ("fallback", "insufficient_context"):
        assert out["source"] == "system2_template"


def test_canonical_events_validate_against_real_system1_schemas():
    """The events rebuilt from MCP packets must pass System 1's own event models (amd/system1/service/schemas.py)."""
    root = Path(__file__).resolve().parents[2] / "system1"
    sys.path.insert(0, str(root))
    try:
        from service.schemas import EVENT_MODELS   # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        pytest.skip("amd/system1 not importable: %s" % exc)
    finally:
        sys.path.remove(str(root))
    from orchestrator.assess import canonical_event
    kind, ev = canonical_event(ESCALATED_PACKET)
    EVENT_MODELS[kind].model_validate(ev)
    mission = {"event": {"mission": {
        "id": "mission:M014", "configuration_version": "V1", "end_time": "2026-09-06T03:00:00",
        "reported_status": "COMPLETED", "duration_min": 42.0, "start_battery_pct": 90, "end_battery_pct": 30.4,
        "actions_total": 10, "actions_failed": 2, "failure_types": {"PATH_BLOCKED": 2},
        "anomalies_by_severity": {"LOW": 0, "MEDIUM": 1, "HIGH": 0, "CRITICAL": 0}}}}
    kind, ev = canonical_event(mission)
    EVENT_MODELS[kind].model_validate(ev)
