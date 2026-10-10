import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from vision import textaxes
from vision.textaxes import Tick, Word, calibrate_axis, find_ticks, kv_rows, parse_num


@pytest.mark.parametrize("text,neg,expected", [
    ("100", False, 100.0), ("SO", False, 50.0), ("-25", False, 25.0), ("-25", True, -25.0), ("8", False, 8.0),
    ("68.06dB", False, 68.06), ("415.85°℉", False, 415.85), ("42.17℉", False, 42.17), ("34psi", False, 34.0),
    ("99%", False, 99.0), ("%66", False, 66.0), ("3,450", False, 3450.0), ("73Square Root Units", False, 73.0),
    ("0(0=Normal)", False, 0.0), ("2OHz", False, 20.0), ("l5", False, 15.0), ("psi", False, None), ("", False, None),
    ("Frequency", False, None), ("41,5", False, 41.5),
])
def test_parse_num(text, neg, expected):
    assert parse_num(text, allow_negative=neg) == expected


def test_calibrate_rejects_bogus_label_and_fits():
    # the kit gauge: label angles vs printed values, with '290' printed where 250 belongs
    ticks = [Tick(-90, 50), Tick(-45, 100), Tick(0, 150), Tick(45, 200), Tick(90, 290), Tick(135, 300), Tick(-135, 0)]
    fit = calibrate_axis(ticks, "linear", residual=12, expect_sign=1)
    assert fit is not None and fit.inliers == 6
    assert [t.value for t in fit.rejected] == [290]
    assert fit.value(22.5) == pytest.approx(175, abs=0.5)
    assert fit.pos(250) == pytest.approx(90, abs=0.5)


def test_calibrate_fails_on_wrong_sign_or_too_few_inliers():
    ticks = [Tick(10, 0), Tick(20, 10), Tick(30, 20)]
    assert calibrate_axis(ticks, expect_sign=-1) is None
    assert calibrate_axis(ticks[:2]) is None
    assert calibrate_axis([Tick(10, 0), Tick(20, 10), Tick(30, 95), Tick(40, 3)]) is None   # no 3 agree


def test_calibrate_log_and_sqrt():
    ticks = [Tick(p, 10 ** (p / 100)) for p in (0, 100, 200, 300)]
    fit = calibrate_axis(ticks, "log")
    assert fit.value(150) == pytest.approx(10 ** 1.5, rel=1e-6)
    sq = [Tick(p, (p / 10) ** 2) for p in (0, 50, 100, 150)]
    fit = calibrate_axis(sq, "sqrt")
    assert fit.value(120) == pytest.approx(144, rel=1e-6)


def _w(text, x, y, h=10, w=20):
    return Word(text, (x, y - h / 2, x + w, y + h / 2), 0.99)


def test_find_ticks_keeps_aligned_column():
    words = [_w("20", 30, 10), _w("15", 31, 40), _w("10", 30, 70), _w("5", 32, 100), _w("Time", 120, 140),
             _w("4", 120, 140)]
    t = find_ticks(words, axis="y")
    assert [x.value for x in t] == [20, 15, 10, 5]


def test_kv_rows_pairs_label_and_value():
    rows = kv_rows([_w("SPL At Source", 10, 100, w=120), _w("68.06dB", 900, 101), _w("SNR Value", 10, 140, w=90),
                    _w("SNR Threshold", 10, 180, w=120), _w("200", 905, 179)])
    assert [(r.label.text, r.value.text if r.value else None) for r in rows] == [
        ("SPL At Source", "68.06dB"), ("SNR Value", None), ("SNR Threshold", "200")]


def test_angle_cw_from_up():
    assert textaxes.angle_cw_from_up(10, 0, 10, 10) == pytest.approx(0)
    assert textaxes.angle_cw_from_up(20, 10, 10, 10) == pytest.approx(90)
    assert textaxes.angle_cw_from_up(0, 10, 10, 10) == pytest.approx(-90)


def test_ocr_reads_rendered_numbers_with_auto_upscale():
    im = Image.new("RGB", (200, 60), (255, 255, 255))
    ImageDraw.Draw(im).text((10, 10), "127.5 psi", fill=(0, 0, 0), font=ImageFont.load_default(size=28))
    words = textaxes.ocr(np.asarray(im))
    assert any(parse_num(w.text) == 127.5 for w in words), [w.text for w in words]
    w = words[0]
    assert 0 <= w.bbox[0] < w.bbox[2] <= 200 and 0 <= w.bbox[1] < w.bbox[3] <= 60   # boxes in input pixels
