"""Orbit screenshot reader: the "Key Results" table (label ........ value rows) and the status badge.

The real numbers in an Orbit capture are text, so this is OCR + row pairing, never pixel reading:
  acoustic  SPL At Source (dB), SNR Value, SNR Threshold  -> anomaly = snr > snr_threshold (computed here)
  thermal   Region N Max/Min Temperature (°F)             -> also emitted in °C
  gauge     Reading (+unit), Reading Confidence (%), Anomaly Prediction
  AI check  answer / reasoning / question (strings)
Also used for `acoustic_imager` frames (no Key Results header: every label/value row in the frame is read).
"""
import re
from typing import List, Optional, Tuple

from . import textaxes
from .result import Frame, Mark, ReaderResult, Reading, r1
from .textaxes import Word

STATUS_WORDS = ("NOMINAL", "ANOMALY", "WARN", "WARNING", "CRITICAL", "ALERT", "FAILURE")
KNOWN = {  # normalised label -> (quantity, default unit)
    "spl at source": ("spl_at_source", "dB"),
    "snr value": ("snr_value", ""),
    "snr threshold": ("snr_threshold", ""),
    "max temperature": ("max_temperature", "°F"),
    "min temperature": ("min_temperature", "°F"),
    "reading": ("reading", ""),
    "reading confidence": ("reading_confidence", "%"),
    "anomaly prediction": ("anomaly_prediction", ""),
    "anomaly confidence": ("anomaly_confidence", "%"),
}
PRIMARY = ("spl_at_source", "max_temperature", "reading")
_UNIT_PATTERNS = [(re.compile(r"(°\s*F|℉)", re.I), "°F"), (re.compile(r"(°\s*C|℃)", re.I), "°C"),
                  (re.compile(r"d\s*B", re.I), "dB"), (re.compile(r"psi", re.I), "psi"), (re.compile(r"kpa", re.I), "kPa"),
                  (re.compile(r"%"), "%")]


def snr_severity(ratio: float) -> Tuple[str, int]:
    """SNR/threshold -> (band, Spot alert severity). <1 none, 1-1.5 low, 1.5-3 medium, >=3 high."""
    if ratio < 1.0:
        return "none", 0
    if ratio < 1.5:
        return "low", 2
    if ratio < 3.0:
        return "medium", 3
    return "high", 4


def f_to_c(f: float) -> float:
    return (f - 32.0) * 5.0 / 9.0


def _norm(label: str) -> str:
    t = re.sub(r"[^a-z0-9 ]+", " ", label.lower())
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace("assetld", "assetid")
    return t


def _value(text: str) -> Tuple[object, str]:
    """value cell -> (number or string, unit)."""
    unit = ""
    for pat, u in _UNIT_PATTERNS:
        if pat.search(text):
            unit = u
            break
    v = textaxes.parse_num(text, allow_negative=True)
    if v is None:
        return text.strip(), ""
    m = re.match(r"^\s*[-+]?\d+(?:[.,]\d+)?\s*(.*)$", text)
    rest = m.group(1).strip() if m else ""
    if not unit and rest and re.search(r"[A-Za-z]{3,}", rest):
        unit = rest                         # "73Square Root Units" -> unit "Square Root Units"
    return v, unit


def _status(words: List[Word], W: int, H: int) -> Optional[Word]:
    """The status badge of the open inspection (top-right of the detail pane), not a word in the image or a table."""
    for w in words:
        if w.cy > 0.3 * H or w.cx < 0.5 * W:
            continue
        t = re.sub(r"[^A-Z]", "", w.text.upper())
        if t in STATUS_WORDS:
            return w
    return None


def _title(words: List[Word]) -> Optional[str]:
    edit = [w for w in words if w.text.strip().lower() == "edit"]
    if not edit:
        return None
    e = edit[0]
    row = [w for w in words if abs(w.cy - e.cy) < 0.8 * e.h and w.bbox[2] < e.bbox[0] and w.cx > 0.3 * e.cx]
    return " ".join(w.text for w in sorted(row, key=lambda w: w.bbox[0])) or None


def _label_words(row_words: List[Word], value: Optional[Word]) -> List[Word]:
    return [w for w in row_words if w is not value and len(re.findall(r"[A-Za-z]", w.text)) >= 3]


def read(frame: Frame, hints: Optional[dict] = None, require_header: bool = True) -> ReaderResult:
    img = frame.orig
    H, W = img.shape[:2]
    res = ReaderResult()
    overview = textaxes.ocr(img, upscale=None if H < 300 else False)
    words = list(overview)
    header = next((w for w in overview if "key result" in w.text.lower()), None)
    table: List[Word]
    if header is not None:
        x0 = max(0, header.bbox[0] - 0.02 * W)
        y0 = max(0, header.bbox[1] - 0.5 * header.h)
        native = textaxes.ocr(img, region=(x0, y0, W, H), upscale=False)   # near-native pass over the table
        table = [w for w in native if w.cy > header.bbox[3]] or [w for w in overview if w.cy > header.bbox[3]]
        words = [w for w in overview if w.cy <= header.bbox[3] or w.cx < x0] + native
    elif require_header:
        res.flags.append("NO_KEY_RESULTS")
        table = []
    else:
        table = overview
    res.words = words
    status_w = _status(overview, W, H)
    title = _title(overview)
    if title:
        res.key_results.append({"name": "Inspection", "units": "", "value": title})
    if status_w is not None:
        res.key_results.append({"name": "status", "units": "", "value": re.sub(r"[^A-Z]", "", status_w.text.upper())})

    readings: List[Reading] = []
    found = {}
    for row in textaxes.kv_rows(table):
        value = row.value
        lw = _label_words(row.words, value)
        if not lw:
            continue
        label = " ".join(w.text for w in lw)
        key = _norm(label)
        if key.startswith("region") and value is None:
            continue
        known = KNOWN.get(key)
        row_box = [min(w.bbox[0] for w in row.words), min(w.bbox[1] for w in row.words),
                   max(w.bbox[2] for w in row.words), max(w.bbox[3] for w in row.words)]
        if value is None:
            if known:
                res.key_results.append({"name": label, "units": known[1], "value": None})
                res.flags.append("MISSING_VALUE")
                found[known[0]] = None
            continue
        v, unit = _value(value.text)
        unit = unit or (known[1] if known else "")
        res.key_results.append({"name": label, "units": unit, "value": v})
        if not isinstance(v, float):
            continue
        q = known[0] if known else re.sub(r"[^a-z0-9]+", "_", key).strip("_")
        found[q] = v
        conf = round(0.95 * min(value.conf, min(w.conf for w in lw)), 2)
        box = [int(round(c)) for c in row_box]
        if unit == "°F":
            c = f_to_c(v)
            res.key_results.append({"name": label + " (°C)", "units": "°C", "value": r1(c)})
            readings.append(Reading(q, r1(c), "°C", conf, "orbit_ocr_f_to_c", [], bbox=box,
                                    note="%s %s °F on screen = %.1f °C" % (label, v, c), primary=q in PRIMARY,
                                    marks=[Mark("box", box)]))
        else:
            readings.append(Reading(q, v, unit, conf, "orbit_ocr", [], bbox=box, note="%s %g%s on screen"
                                    % (label, v, (" " + unit) if unit else ""), primary=q in PRIMARY,
                                    marks=[Mark("box", box)]))
    # computed (not read): anomaly = snr > threshold
    snr, thr = found.get("snr_value"), found.get("snr_threshold")
    shown = next((kr["value"] for kr in res.key_results if kr["name"] == "status"), None)
    if snr is not None and thr:
        ratio = snr / thr
        band, sev = snr_severity(ratio)
        anomaly = snr > thr
        res.key_results += [{"name": "snr_ratio", "units": "", "value": round(ratio, 3)},
                            {"name": "anomaly", "units": "", "value": "true" if anomaly else "false"},
                            {"name": "severity_band", "units": "", "value": band}]
        if shown in ("NOMINAL", "ANOMALY") and (shown == "ANOMALY") != anomaly:
            res.flags.append("STATUS_MISMATCH")
        if sev:
            res.alert = {"title": "Acoustic anomaly: SNR %g over threshold %g (x%.2f, %s)" % (snr, thr, ratio, band),
                         "severity": sev, "source": "vision.orbit.acoustic"}
    elif shown in ("ANOMALY", "CRITICAL", "ALERT", "FAILURE"):
        res.alert = {"title": "Orbit shows %s (values not readable)" % shown, "severity": 2,
                     "source": "vision.orbit.status"}
    if not readings and not res.flags and header is None and not require_header:
        res.flags.append("NO_KEY_RESULTS")
    res.readings = readings
    return res
