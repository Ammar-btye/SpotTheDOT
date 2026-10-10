"""Every reader on the real kit images (skipped when the kit folder is absent)."""
import base64

import pytest

from conftest import ORBIT, SAMPLES, load, orbit_shot, requires_kit, requires_orbit
from vision import gauge, orbit, spectrogram, thermal
from vision.config import Settings
from vision.pipeline import analyze
from vision.router import route


def _req(path, **kw):
    return dict({"image_b64": base64.b64encode(path.read_bytes()).decode(), "kind": "auto", "annotate": True}, **kw)


@requires_kit
def test_thermal_pump_bearing(frame_of):
    res = thermal.read(frame_of(load(SAMPLES / "thermal_pump_bearing_01.jpg")))
    v = {r.quantity: r for r in res.readings}
    mx = v["max_temperature"]
    assert 98.0 <= mx.value <= 101.0 and "CLIPPED" in mx.flags            # ~99.8 °C at the 100 °C top of the bar
    px, py = mx.point
    assert abs(px - 149) <= 8 and abs(py - 63) <= 8                        # bearing housing hotspot
    assert 35.0 <= v["reference_temperature"].value <= 45.0                # motor body ~40 °C
    assert v["delta_t"].value >= 50
    assert res.alert["severity"] == 4


@requires_kit
def test_gauge_pressure_is_ambiguous_not_confident(frame_of):
    res = gauge.read(frame_of(load(SAMPLES / "gauge_pressure_01.jpg")))
    rd = res.readings[0]
    assert "AMBIGUOUS_NEEDLE" in rd.flags and rd.confidence <= 0.3
    assert "LABEL_OUTLIER" in rd.flags                                    # the printed '290' is rejected
    assert rd.full_scale == 300


@requires_kit
def test_acoustic_spectrogram(frame_of):
    res = spectrogram.read(frame_of(load(SAMPLES / "acoustic_valve_01.jpg")))
    v = {r.quantity: r for r in res.readings}
    assert 0.5 <= v["peak_frequency"].value <= 2.5
    assert v["band_energy_0_2khz"].value == max(r.value for q, r in v.items() if q.startswith("band_energy"))
    assert "RELATIVE_ONLY" in v["peak_frequency"].flags
    assert v["high_frequency_ratio"].value < 0.5


@requires_kit
@pytest.mark.parametrize("name", ["pipe_gallery_01.jpg", "valve_detail_01.jpg", "visual_pump_motor_01.jpg"])
def test_visual_images_route_to_ocr_only(name):
    out = analyze(_req(SAMPLES / name, action_type="VISUAL_INSPECTION"), Settings())
    assert out["kind"] == "visual" and out["readings"] == [] and out["comparison"] is None


@requires_kit
def test_router_heuristic_on_kit_samples():
    for name, want in [("thermal_pump_bearing_01.jpg", "thermal"), ("acoustic_valve_01.jpg", "spectrogram"),
                       ("gauge_pressure_01.jpg", "visual"), ("pipe_gallery_01.jpg", "visual")]:
        im = load(SAMPLES / name)
        assert route(im, (im.shape[1], im.shape[0]))["label"] == want, name


@requires_kit
def test_pipeline_thermal_vs_log_disagrees():
    out = analyze(_req(SAMPLES / "thermal_pump_bearing_01.jpg", action_type="THERMAL_INSPECTION",
                       logged={"reading_id": "R0042", "measurement_type": "TEMPERATURE_C", "value": 83.5}), Settings())
    c = out["comparison"]
    assert c["vision_id"] == "V1" and c["agrees"] is False and c["logged_id"] == "R0042"
    assert out["readings"][0]["id"] == "V1" and out["alert"]["severity"] == 4
    assert out["annotated_image_b64"] and out["annotated_mime"] == "image/jpeg"


@requires_kit
def test_pipeline_gauge_vs_log_is_not_judged():
    out = analyze(_req(SAMPLES / "gauge_pressure_01.jpg", action_type="GAUGE_READING",
                       logged={"reading_id": "R7", "measurement_type": "PRESSURE_PSI", "value": 120.0}), Settings())
    assert out["comparison"]["agrees"] is None and "LOW_CONFIDENCE" in out["comparison"]["flags"]


# ── Orbit screenshots ─────────────────────────────────────────────────────────────────────────────────
def _orbit(frame_of, stamp):
    return orbit.read(frame_of(load(orbit_shot(stamp))))


def _kr(res):
    return {k["name"]: k["value"] for k in res.key_results}


@requires_orbit
@pytest.mark.parametrize("stamp,spl,snr,thr,anomaly,sev", [
    ("11.29.16", 68.06, 167, 200, "false", None),
    ("11.29.24", 84.24, 230, 200, "true", 2),
    ("11.29.51", 91.16, 781, 200, "true", 4),
])
def test_orbit_acoustic_key_results(frame_of, stamp, spl, snr, thr, anomaly, sev):
    res = _orbit(frame_of, stamp)
    kr = _kr(res)
    assert kr["SPL At Source"] == spl and kr["SNR Value"] == snr and kr["SNR Threshold"] == thr
    assert kr["anomaly"] == anomaly
    assert (res.alert or {}).get("severity") == sev
    assert res.readings[0].quantity == "spl_at_source" and res.readings[0].primary and res.readings[0].unit == "dB"
    assert "STATUS_MISMATCH" not in res.flags                              # computed rule matches Orbit's badge


@requires_orbit
def test_orbit_occluded_values_are_missing_not_guessed(frame_of):
    res = _orbit(frame_of, "11.29.20")                                     # a screenshot thumbnail covers the values
    kr = _kr(res)
    assert kr["SNR Value"] is None and kr["SNR Threshold"] is None and "MISSING_VALUE" in res.flags
    assert kr["status"] == "ANOMALY" and res.alert["source"] == "vision.orbit.status"


@requires_orbit
def test_orbit_thermal_region_f_to_c(frame_of):
    res = _orbit(frame_of, "11.29.05")
    kr = _kr(res)
    assert kr["Max Temperature"] == 415.85 and kr["Min Temperature"] == 104.81
    v = {r.quantity: r for r in res.readings}
    assert v["max_temperature"].unit == "°C" and v["max_temperature"].value == pytest.approx(213.2, abs=0.1)


@requires_orbit
@pytest.mark.parametrize("stamp,value", [("11.30.53", 34.0), ("11.31.07", 35.6)])
def test_orbit_gauge_reading(frame_of, stamp, value):
    res = _orbit(frame_of, stamp)
    kr = _kr(res)
    assert kr["Reading"] == value and kr["Reading Confidence"] == 99.0
    assert res.readings[0].unit == "psi"


@requires_orbit
def test_orbit_ai_answer_rows_are_strings(frame_of):
    kr = _kr(_orbit(frame_of, "11.30.06"))
    assert kr["answer"] == "Yes" and "fire extinguisher" in kr["question"]


@requires_orbit
def test_orbit_router_and_dashboards():
    for stamp in ("11.29.16", "11.32.01"):
        im = load(orbit_shot(stamp))
        from vision.imageio import downscale
        w, _ = downscale(im, 1280)
        assert route(w, (im.shape[1], im.shape[0]))["label"] == "orbit_screenshot"


@pytest.mark.slow
@requires_orbit
def test_every_orbit_screenshot_runs_cleanly():
    for p in sorted(ORBIT.glob("*.png")):
        out = analyze(_req(p, annotate=False), Settings())
        assert "READER_FAILED" not in out["flags"], p.name
        assert out["annotated_image_b64"] is None
