"""Vision value vs logged value. Code decides `agrees`; no model ever arbitrates between the tool and the log."""
from typing import Dict, List, Optional, Tuple

from .result import Reading, r1

TOLERANCES = {"temperature_c": 4.0, "pressure_psi": 6.0, "pressure_fs_frac": 0.03, "sound_db": 3.0,
              "visual_points": 10.0}
MIN_CONFIDENCE = 0.5
_PSI = {"psi": 1.0, "bar": 14.5038, "kPa": 0.145038, "MPa": 145.038}


def _family(measurement_type: str, unit: str) -> Optional[str]:
    mt, u = (measurement_type or "").upper(), (unit or "").strip().lower().replace("°", "").replace("deg", "")
    if "TEMP" in mt or u in ("c", "f", "℃", "℉"):
        return "temperature"
    if "PRESS" in mt or u in ("psi", "bar", "kpa", "mpa"):
        return "pressure"
    if "SOUND" in mt or "DB" in mt or u in ("db", "dba", "dbz"):
        return "sound"
    return None


def _logged_canonical(family: str, value: float, unit: str, measurement_type: str) -> Tuple[float, str]:
    u = (unit or "").strip().lower().replace("°", "").replace("deg", "")
    if family == "temperature":
        if u in ("f", "℉") or measurement_type.upper().endswith("_F"):
            return (value - 32.0) * 5.0 / 9.0, "°C"
        return value, "°C"
    if family == "pressure":
        for k, f in _PSI.items():
            if u == k.lower():
                return value * f, "psi"
        return value, "psi"
    return value, "dB"


def _vision_canonical(family: str, rd: Reading) -> Optional[float]:
    if family == "temperature":
        if rd.unit == "°C":
            return rd.value
        if rd.unit == "°F":
            return (rd.value - 32.0) * 5.0 / 9.0
        return None
    if family == "pressure":
        f = _PSI.get(rd.unit)
        return rd.value * f if f else None
    if family == "sound":
        return rd.value if rd.unit == "dB" else None
    return None


def compare(logged: Optional[Dict], readings: List[Reading], ids: List[str]) -> Optional[Dict]:
    """The comparison block of docs/vision-contract.md, or None when there is nothing to compare."""
    if not logged or logged.get("value") is None:
        return None
    mt = str(logged.get("measurement_type") or "")
    fam = _family(mt, str(logged.get("unit") or ""))
    if fam is None:
        return None
    for rd, vid in zip(readings, ids):
        if not rd.primary:
            continue
        vv = _vision_canonical(fam, rd)
        if vv is None:
            continue
        lv, unit = _logged_canonical(fam, float(logged["value"]), str(logged.get("unit") or ""), mt)
        if fam == "temperature":
            tol = TOLERANCES["temperature_c"]
        elif fam == "pressure":
            tol = TOLERANCES["pressure_psi"]
            if rd.full_scale:
                tol = max(tol, TOLERANCES["pressure_fs_frac"] * rd.full_scale * _PSI.get(rd.unit, 1.0))
        else:
            tol = TOLERANCES["sound_db"]
        delta = vv - lv
        flags: List[str] = []
        if rd.confidence < MIN_CONFIDENCE:
            agrees = None
            flags.append("LOW_CONFIDENCE")
        elif rd.clipped and lv >= vv - tol:
            agrees = True
            flags.append("VISION_CLIPPED")
        else:
            agrees = abs(delta) <= tol
            if rd.clipped:
                flags.append("VISION_CLIPPED")
        return {"logged_id": logged.get("reading_id"), "logged_value": r1(lv, 2), "logged_unit": unit,
                "vision_id": vid, "vision_value": r1(vv, 2), "delta": r1(delta, 2), "tolerance": r1(tol, 2),
                "agrees": agrees, "flags": flags}
    return None
