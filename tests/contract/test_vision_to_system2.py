"""Cross-service contract: vision service -> orchestrator V# mapping -> System 2 request parser, all real code.

Each unit suite checks its own side with hand-made data (amd/vision/tests, amd/orchestrator/tests/test_assess.py,
amd/system2/tests/test_multimodal.py). This one runs a synthetic image through the REAL chain, in-process:

  amd/vision   POST /v1/vision (TestClient, with the X-API-Key the orchestrator sends)
  amd/orchestrator   logged_reading -> vision_rows / ocr_lines / system2_image (what the vision node does)
  amd/system2  BackendAssessRequest + normalize_packet (the parser /v1/assess runs), then POST /v1/assess (stub)

and asserts that V# ids, trust casing, reader flags / bound, demo-row comparison stripping and LOW-row value
stripping survive end to end. Offline (synthetic images; the OCR models must already be downloaded, see
amd/vision/scripts/fetch_models.py). Own venv: pip install -r tests/contract/requirements.txt; `make test-contract`.
"""
from __future__ import annotations

import base64
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "amd" / "vision", ROOT / "amd" / "vision" / "tests", ROOT / "amd" / "orchestrator",
          ROOT / "amd" / "system2"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

pytest.importorskip("rapidocr", reason="vision deps missing: pip install -r tests/contract/requirements.txt")
pytest.importorskip("langgraph", reason="orchestrator deps missing: pip install -r tests/contract/requirements.txt")

from fastapi.testclient import TestClient  # noqa: E402

import synth  # noqa: E402  (amd/vision/tests/synth.py: rendered gauges / thermal frames)
from vision.api import create_app as vision_app  # noqa: E402
from vision.config import Settings as VisionSettings  # noqa: E402
from vision.imageio import to_b64_png  # noqa: E402

from orchestrator.assess import logged_reading, ocr_lines, system2_image, vision_rows  # noqa: E402
from orchestrator.config import Settings as OrchSettings  # noqa: E402

from analyst.api import create_app as system2_app  # noqa: E402
from analyst.backend_contract import BackendAssessRequest  # noqa: E402
from analyst.packet import DISAGREE_BLOCKED, normalize_packet  # noqa: E402

VISION_KEY = "contract-vision-key-0123456789"
S2_KEY = "contract-s2-key-0123456789"
# The orchestrator's own defaults (VISION_TRUST_MIN 0.5, OCR_TOP_N 8), read from its Settings, not restated here.
ORCH = OrchSettings.from_env({"ORCHESTRATOR_API_KEY": "contract-orch-key-0123456789"})
FIXTURE = json.loads((ROOT / "amd" / "system2" / "fixtures" / "backend" / "equipment.json").read_text())["request"]
COMPARISON_FIELDS = ("logged_id", "logged_value", "delta", "agrees")


@pytest.fixture(scope="module")
def vision():
    with TestClient(vision_app(VisionSettings(api_key=VISION_KEY), warm=False)) as c:
        yield c


@pytest.fixture(scope="module")
def system2():
    with TestClient(system2_app(api_key=S2_KEY)) as c:
        yield c


def request_with(reading: dict | None) -> dict:
    """System 2's equipment fixture, with the event's first reading swapped for `reading` (same packet id)."""
    req = copy.deepcopy(FIXTURE)
    if reading is not None:
        req["context"]["event"]["readings"] = [dict(reading, id="reading:R0150")]
    return req


def chain(vision, system2, image_b64: str, *, action_type: str, reading: dict | None = None,
          pairing: str = "linked", kind: str = "auto"):
    """One image through vision -> orchestrator mapping -> System 2, as amd/orchestrator/orchestrator/assess.py
    `vision` + `system2` nodes do it. Returns (vision response, V# rows, PreparedPacket, System 2 response)."""
    req = request_with(reading)
    logged = logged_reading(req["context"]) if pairing == "linked" else None   # demo images are never compared
    body = {"kind": kind, "action_type": action_type, "image_b64": image_b64, "annotate": True}
    if logged:
        body["logged"] = {k: v for k, v in logged.items() if k != "packet_id"}
    r = vision.post("/v1/vision", json=body, headers={"X-API-Key": VISION_KEY})
    assert r.status_code == 200, r.text
    resp = r.json()
    rows = vision_rows(resp, pairing, ORCH.vision_trust_min, (logged or {}).get("packet_id"))
    s2_image, note = system2_image(resp.get("annotated_image_b64"))
    assert s2_image is not None, note
    req["context"]["vision"] = rows
    req["context"]["ocr"] = ocr_lines(resp, ORCH.ocr_top_n)
    req["image_b64"] = s2_image
    prepared = normalize_packet(BackendAssessRequest.model_validate(req))
    http = system2.post("/v1/assess", json=req, headers={"X-API-Key": S2_KEY})
    assert http.status_code == 200, http.text
    return resp, rows, prepared, http.json()


def kept(prepared, vid: str) -> dict:
    """The fields System 2 kept for one V# row (what the model sees and what grounding checks against)."""
    return json.loads(prepared.content[vid])


PSI = {"measurement_type": "PRESSURE_PSI", "value": 118.0, "unit": "psi"}


def test_linked_gauge_ids_trust_and_comparison_survive(vision, system2):
    resp, rows, prepared, out = chain(vision, system2, to_b64_png(synth.render_gauge(117)),
                                      action_type="GAUGE_READING", reading=PSI)
    vision_ids = [r["id"] for r in resp["readings"]]
    assert vision_ids and vision_ids[0] == "V1"
    assert [r["id"] for r in rows] == vision_ids == list(prepared.vision_ids)    # V# ids unchanged end to end
    assert all(r["trust"] in ("HIGH", "LOW") for r in rows)                      # System 2's enum casing
    v1 = kept(prepared, "V1")
    assert v1["trust"] == "HIGH" and v1["pairing"] == "linked" and v1["kind"] == "gauge"
    assert abs(v1["value"] - 117) <= 6 and v1["unit"] == resp["readings"][0]["unit"]
    # comparison attached to the compared reading, with the packet's citation id (not the vision service's R id)
    assert v1["logged_id"] == "reading:R0150" and v1["logged_value"] == 118.0 and v1["agrees"] is True
    assert "MONITOR" in prepared.allowed_actions                                 # agreement restricts nothing
    assert prepared.image is not None and prepared.image.mime in ("image/jpeg", "image/png")
    assert {w["text"] for w in resp["ocr"]} & set(prepared.ocr)                  # OCR lines reach System 2 ...
    assert not set(prepared.ocr) & set(prepared.content)                         # ... but are never citable
    assert out["flag_id"] == FIXTURE["flag_id"] and out["path"] == "stub"


def test_linked_disagreement_removes_all_fine_actions(vision, system2):
    resp, rows, prepared, out = chain(vision, system2, to_b64_png(synth.render_gauge(233)),
                                      action_type="GAUGE_READING", reading=dict(PSI, value=150.0))
    assert resp["comparison"]["agrees"] is False and resp["alert"]["source"] == "vision.compare"
    v1 = kept(prepared, "V1")
    assert v1["trust"] == "HIGH" and v1["agrees"] is False and v1["logged_id"] == "reading:R0150"
    assert not set(DISAGREE_BLOCKED) & set(prepared.allowed_actions)
    assert out["recommended_action"] not in DISAGREE_BLOCKED


def test_demo_pairing_never_carries_a_comparison(vision, system2):
    image = to_b64_png(synth.render_gauge(233))
    # The orchestrator sends no `logged` for a demo image, so vision makes no comparison at all ...
    resp, rows, prepared, _ = chain(vision, system2, image, action_type="GAUGE_READING",
                                    reading=dict(PSI, value=150.0), pairing="demo")
    assert resp["comparison"] is None and resp["alert"] is None
    assert all(r["pairing"] == "demo" for r in rows)
    assert "MONITOR" in prepared.allowed_actions

    # ... and even a vision response that does carry one (a linked call) is stripped twice: by vision_rows ...
    linked = vision.post("/v1/vision", headers={"X-API-Key": VISION_KEY}, json={
        "action_type": "GAUGE_READING", "image_b64": image, "annotate": False,
        "logged": {"reading_id": "R0150", "measurement_type": "PRESSURE_PSI", "value": 150.0}}).json()
    assert linked["comparison"]["agrees"] is False
    demo_rows = vision_rows(linked, "demo", ORCH.vision_trust_min, "reading:R0150")
    assert demo_rows and not any(k in r for r in demo_rows for k in COMPARISON_FIELDS)

    # ... and by System 2, if a caller labels comparison-carrying rows as demo anyway.
    relabelled = [dict(r, pairing="demo") for r in vision_rows(linked, "linked", ORCH.vision_trust_min,
                                                                "reading:R0150")]
    assert relabelled[0]["agrees"] is False
    req = request_with(dict(PSI, value=150.0))
    req["context"]["vision"] = relabelled
    prepared = normalize_packet(BackendAssessRequest.model_validate(req))
    assert not any(k in kept(prepared, "V1") for k in COMPARISON_FIELDS)
    assert "MONITOR" in prepared.allowed_actions                                 # a demo row never judges the asset


def test_ambiguous_needle_row_is_low_and_loses_its_value(vision, system2):
    image = to_b64_png(synth.jpeg(synth.render_gauge(117, two_ended=True), 85))
    resp, rows, prepared, _ = chain(vision, system2, image, action_type="GAUGE_READING",
                                    reading=dict(PSI, value=40.0))
    assert "AMBIGUOUS_NEEDLE" in resp["readings"][0]["flags"]
    assert rows[0]["trust"] == "LOW" and "AMBIGUOUS_NEEDLE" in rows[0]["flags"]
    assert rows[0].get("value") is not None                                     # the orchestrator forwards it ...
    v1 = kept(prepared, "V1")
    assert v1["trust"] == "LOW" and "AMBIGUOUS_NEEDLE" in v1["flags"]
    assert not {"value", "delta", "agrees"} & set(v1)                          # ... System 2 drops it (LOW row)
    assert "MONITOR" in prepared.allowed_actions                                 # a LOW row never restricts actions


def test_clipped_thermal_reading_is_a_lower_bound(vision, system2):
    image = to_b64_png(synth.jpeg(synth.render_thermal(140.0, tmax=120.0), 85))
    resp, rows, prepared, _ = chain(vision, system2, image, action_type="THERMAL_INSPECTION",
                                    reading={"measurement_type": "TEMPERATURE_C", "value": 95.0, "unit": "C"})
    clipped = [r for r in rows if "CLIPPED" in r.get("flags", [])]
    assert clipped, [(r["id"], r.get("flags")) for r in rows]
    for row in clipped:
        assert row["bound"] == "lower"
        assert kept(prepared, row["id"])["bound"] == "lower"
        assert "CLIPPED" in kept(prepared, row["id"])["flags"]
    by_id = {r["id"]: r for r in resp["readings"]}
    for row in rows:                                                            # trust follows the orchestrator rule
        conf = by_id[row["id"]]["confidence"]
        assert row["trust"] == ("HIGH" if conf >= ORCH.vision_trust_min else "LOW")
        assert kept(prepared, row["id"])["trust"] == row["trust"]


def test_every_row_vision_can_emit_is_accepted_by_system2(vision, system2):
    """Gauge, thermal and spectrogram output through the mapping: System 2 never 422s on the orchestrator's rows."""
    cases = [("GAUGE_READING", synth.render_gauge(42)),
             ("THERMAL_INSPECTION", synth.render_thermal(83.5)),
             ("ACOUSTIC_INSPECTION", synth.render_spectrogram())]
    for action_type, rgb in cases:
        _, rows, prepared, _ = chain(vision, system2, to_b64_png(rgb), action_type=action_type, reading=None)
        assert rows, action_type
        assert list(prepared.vision_ids) == [r["id"] for r in rows]
        for row in rows:
            assert kept(prepared, row["id"])["tool"] == row["tool"]
            assert base64.b64decode(prepared.image.b64)[:2] in (b"\xff\xd8", b"\x89P")
