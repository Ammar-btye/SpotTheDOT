"""Readers on synthetic renders with known ground truth (tests/synth.py)."""
import numpy as np
import pytest
from PIL import Image

import synth
from vision import gauge, spectrogram, thermal
from vision.router import route


@pytest.mark.parametrize("psi", [0, 37, 117, 150, 233, 290])
@pytest.mark.parametrize("size,quality", [(360, 90), (240, 60)])
def test_gauge_reads_known_value(frame_of, psi, size, quality):
    img = synth.jpeg(synth.render_gauge(psi, size=size), quality)
    res = gauge.read(frame_of(img))
    rd = res.readings[0]
    assert rd.quantity == "pressure" and rd.unit == "psi"
    assert abs(rd.value - psi) <= 0.02 * 300, (rd.value, rd.flags)        # within 2 % of full scale
    assert rd.confidence >= 0.5 and "AMBIGUOUS_NEEDLE" not in rd.flags
    assert rd.full_scale == 300


def test_gauge_two_ended_needle_is_low_confidence(frame_of):
    img = synth.jpeg(synth.render_gauge(117, two_ended=True), 85)
    rd = gauge.read(frame_of(img)).readings[0]
    assert "AMBIGUOUS_NEEDLE" in rd.flags and rd.confidence <= 0.3


def test_gauge_other_range_and_unit(frame_of):
    img = synth.jpeg(synth.render_gauge(6.5, vmin=0, vmax=10, major=2, minor=0.5, unit="bar", size=360), 90)
    rd = gauge.read(frame_of(img)).readings[0]
    assert rd.unit == "bar"
    assert abs(rd.value - 6.5) <= 0.2


def test_gauge_without_labels_uses_hint_sweep(frame_of):
    img = synth.render_gauge(150, size=360)
    blank = img.copy()
    # paint over the label ring so OCR finds nothing
    from PIL import ImageDraw
    im = Image.fromarray(blank)
    d = ImageDraw.Draw(im)
    c, R = 180, 360 * 0.44
    for a in range(0, 360, 2):
        import math
        x, y = c + 0.66 * R * math.sin(math.radians(a)), c - 0.66 * R * math.cos(math.radians(a))
        d.ellipse([x - 16, y - 12, x + 16, y + 12], fill=(245, 245, 240))
    res = gauge.read(frame_of(np.asarray(im)), {"range_min": 0, "range_max": 300})
    rd = res.readings[0]
    assert "DEFAULT_SWEEP" in rd.flags and "USED_HINT" in rd.flags
    assert rd.confidence <= 0.4
    assert abs(rd.value - 150) <= 15


@pytest.mark.parametrize("max_c", [55.0, 83.5, 99.0])
def test_thermal_max_and_hotspot(frame_of, max_c):
    img = synth.jpeg(synth.render_thermal(max_c, hot_xy=(150, 90)), 85)
    res = thermal.read(frame_of(img))
    v = {r.quantity: r for r in res.readings}
    assert abs(v["max_temperature"].value - max_c) <= 3.0, v["max_temperature"].value
    px, py = v["max_temperature"].point
    assert abs(px - 150) <= 6 and abs(py - 90) <= 6
    assert "CLIPPED" not in v["max_temperature"].flags
    assert v["max_temperature"].confidence >= 0.5


def test_thermal_clipped_at_scale_top(frame_of):
    img = synth.jpeg(synth.render_thermal(140.0, tmax=120.0), 85)
    res = thermal.read(frame_of(img))
    mx = res.readings[0]
    assert "CLIPPED" in mx.flags and mx.clipped
    assert mx.value == pytest.approx(120.0, abs=1.0)
    assert res.alert["severity"] == 4


def test_thermal_large_frame_is_downscaled_consistently(frame_of):
    img = np.asarray(Image.fromarray(synth.render_thermal(83.5)).resize((1920, 1320), Image.BICUBIC))
    f = frame_of(img)
    assert f.scale < 1
    mx = thermal.read(f).readings[0]
    assert abs(mx.value - 83.5) <= 3.0
    px, py = mx.point                      # reported in ORIGINAL pixels
    assert abs(px - 150 * 6) <= 40 and abs(py - 90 * 6) <= 40


def test_spectrogram_peak_and_bursts(frame_of):
    img = synth.jpeg(synth.render_spectrogram(peak_khz=3.0, bursts=(2.0, 5.0, 8.0)), 85)
    res = spectrogram.read(frame_of(img))
    v = {r.quantity: r for r in res.readings}
    assert abs(v["peak_frequency"].value - 3.0) <= 0.5
    assert "RELATIVE_ONLY" in v["peak_frequency"].flags
    kr = {k["name"]: k["value"] for k in res.key_results}
    times = [float(t) for t in kr["Burst Times"].split(",")]
    assert len(times) == 3 and all(abs(a - b) <= 0.2 for a, b in zip(times, (2.0, 5.0, 8.0)))
    assert kr["absolute_db_available"] == "false"
    assert v["band_energy_2_5khz"].value > v["band_energy_10_20khz"].value


def test_router_heuristic_on_synthetic():
    th = synth.render_thermal(80)
    sp = synth.render_spectrogram()
    assert route(th, (th.shape[1], th.shape[0]))["label"] == "thermal"
    assert route(sp, (sp.shape[1], sp.shape[0]))["label"] == "spectrogram"
    g = synth.render_gauge(100)
    assert route(g, (360, 360))["label"] == "visual"
    assert route(g, (360, 360), action_type="GAUGE_READING") == {"label": "gauge", "method": "action_type",
                                                                    "confidence": 1.0}
    assert route(g, (360, 360), kind="thermal")["method"] == "kind"
    assert route(sp, (420, 280), action_type="ACOUSTIC_INSPECTION")["label"] == "spectrogram"
    assert route(g, (360, 360), action_type="ACOUSTIC_INSPECTION")["label"] == "acoustic_imager"
