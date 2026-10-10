import pytest

from vision.compare import compare
from vision.result import Reading


def rd(value, unit, conf=0.9, clipped=False, fs=None, primary=True):
    return Reading("q", value, unit, conf, "m", primary=primary, clipped=clipped, full_scale=fs)


def test_temperature_agrees_within_4c_and_disagrees_beyond():
    c = compare({"reading_id": "R1", "measurement_type": "TEMPERATURE_C", "value": 80.0}, [rd(83.5, "°C")], ["V1"])
    assert c["agrees"] is True and c["delta"] == 3.5 and c["tolerance"] == 4.0 and c["vision_id"] == "V1"
    c = compare({"reading_id": "R1", "measurement_type": "TEMPERATURE_C", "value": 70.0}, [rd(83.5, "°C")], ["V1"])
    assert c["agrees"] is False and c["delta"] == 13.5


def test_low_confidence_gives_null_agrees():
    c = compare({"measurement_type": "PRESSURE_PSI", "value": 100.0}, [rd(1.0, "psi", conf=0.3)], ["V1"])
    assert c["agrees"] is None and "LOW_CONFIDENCE" in c["flags"]


def test_pressure_tolerance_uses_3pct_full_scale():
    c = compare({"measurement_type": "PRESSURE_PSI", "value": 100.0}, [rd(108.0, "psi", fs=300)], ["V1"])
    assert c["tolerance"] == 9.0 and c["agrees"] is True
    c = compare({"measurement_type": "PRESSURE_PSI", "value": 100.0}, [rd(108.0, "psi", fs=100)], ["V1"])
    assert c["tolerance"] == 6.0 and c["agrees"] is False


def test_clipped_vision_agrees_with_higher_log():
    c = compare({"measurement_type": "TEMPERATURE_C", "value": 105.0}, [rd(100.0, "°C", clipped=True)], ["V1"])
    assert c["agrees"] is True and "VISION_CLIPPED" in c["flags"]
    c = compare({"measurement_type": "TEMPERATURE_C", "value": 83.5}, [rd(100.0, "°C", clipped=True)], ["V1"])
    assert c["agrees"] is False


def test_units_are_converted():
    c = compare({"measurement_type": "TEMPERATURE", "value": 212.0, "unit": "°F"}, [rd(100.0, "°C")], ["V1"])
    assert c["logged_value"] == 100.0 and c["agrees"] is True
    c = compare({"measurement_type": "PRESSURE_PSI", "value": 145.0}, [rd(10.0, "bar")], ["V1"])
    assert c["vision_value"] == pytest.approx(145.04, abs=0.01) and c["agrees"] is True
    c = compare({"measurement_type": "SOUND_DB", "value": 70.0}, [rd(68.06, "dB")], ["V1"])
    assert c["tolerance"] == 3.0 and c["agrees"] is True


def test_no_comparison_without_matching_primary():
    assert compare(None, [rd(1, "psi")], ["V1"]) is None
    assert compare({"measurement_type": "SOUND_DB", "value": 70.0}, [rd(83.5, "°C")], ["V1"]) is None
    assert compare({"measurement_type": "TEMPERATURE_C", "value": 70.0}, [rd(83.5, "°C", primary=False)], ["V1"]) is None
    assert compare({"measurement_type": "BATTERY", "value": 70.0}, [rd(83.5, "°C")], ["V1"]) is None
