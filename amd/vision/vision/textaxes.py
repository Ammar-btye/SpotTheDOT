"""OCR (RapidOCR on onnxruntime CPU), number parsing, tick finding and RANSAC axis calibration.

Shared by every reader. All boxes are axis-aligned [x0, y0, x1, y1] in the pixel frame of the array passed in.
"""
import itertools
import math
import re
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

OCR_MAX_SIDE = 2000          # RapidOCR's own Global.max_side_len
UPSCALE_BELOW_H = 300        # auto 3x upscale for small images (tested: kit images are ~166 px high)
UPSCALE_FACTOR = 3

_engine = None
_engine_lock = threading.Lock()   # one OCR call at a time: onnxruntime sessions are shared
_ocr_threads = -1


@dataclass(frozen=True)
class Word:
    text: str
    bbox: Tuple[float, float, float, float]
    conf: float

    @property
    def cx(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def cy(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2

    @property
    def h(self) -> float:
        return self.bbox[3] - self.bbox[1]

    def shifted(self, dx: float, dy: float, scale: float = 1.0) -> "Word":
        x0, y0, x1, y1 = self.bbox
        return Word(self.text, (x0 / scale + dx, y0 / scale + dy, x1 / scale + dx, y1 / scale + dy), self.conf)

    def as_dict(self) -> dict:
        return {"text": self.text, "bbox": [int(round(v)) for v in self.bbox], "conf": round(float(self.conf), 3)}


def configure(threads: int = -1) -> None:
    global _ocr_threads
    _ocr_threads = threads


def engine():
    """Lazily build the RapidOCR engine (loads 3 ONNX models, ~1 s)."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from rapidocr import RapidOCR
                # use_cls off: inspection images are upright, and the 180° classifier flips short tokens ("99%" -> "%66")
                _engine = RapidOCR(params={"Global.log_level": "error", "Global.use_cls": False,
                                           "EngineConfig.onnxruntime.intra_op_num_threads": _ocr_threads})
    return _engine


def ocr_ready() -> bool:
    return _engine is not None


def ocr(img: np.ndarray, upscale: Optional[bool] = None, region: Optional[Sequence[int]] = None,
        max_side: int = OCR_MAX_SIDE) -> List[Word]:
    """OCR an RGB uint8 array (or a region [x0,y0,x1,y1] of it). Boxes come back in `img` pixels.

    upscale=None -> 3x when the (region) height < 300 px; the working copy is capped at max_side.
    """
    ox = oy = 0
    if region is not None:
        x0, y0, x1, y1 = [int(round(v)) for v in region]
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(img.shape[1], x1), min(img.shape[0], y1)
        if x1 - x0 < 4 or y1 - y0 < 4:
            return []
        img = img[y0:y1, x0:x1]
        ox, oy = x0, y0
    h, w = img.shape[:2]
    s = 1.0
    if upscale is None:
        upscale = h < UPSCALE_BELOW_H
    if upscale:
        s = float(UPSCALE_FACTOR)
    s = min(s, float(max_side) / max(h, w))
    if abs(s - 1.0) > 1e-6:
        work = np.asarray(Image.fromarray(img).resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS))
    else:
        work = img
    bgr = np.ascontiguousarray(work[:, :, ::-1])
    eng = engine()
    with _engine_lock:
        res = eng(bgr)
    if res is None or res.txts is None or res.boxes is None:
        return []
    out = []
    for text, box, score in zip(res.txts, res.boxes, res.scores):
        q = np.asarray(box, dtype=float)
        bb = (q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max())
        out.append(Word(str(text).strip(), bb, float(score)).shifted(ox, oy, s))
    return [w_ for w_ in out if w_.text]


# ── numbers ───────────────────────────────────────────────────────────────────────────────────────────
_UNIT_RE = re.compile(r"(°\s*[CF]|[℃℉]|°|deg[CF]?|psi|kpa|bar|khz|hz|db[az]?|%|ms|s)$", re.I)
_FIX = str.maketrans({"O": "0", "o": "0", "S": "5", "s": "5", "l": "1", "I": "1", "|": "1", "B": "8",
                      "—": "-", "–": "-", "−": "-", ",": ""})
_NUM_RE = re.compile(r"^[-+]?\d+(?:\.\d+)?$")
_LEAD_RE = re.compile(r"^\s*([-+]?\d+(?:[.,]\d+)?)")


def strip_units(text: str) -> str:
    t = text.strip()
    for _ in range(3):
        t2 = _UNIT_RE.sub("", t).strip()
        if t2 == t:
            break
        t = t2
    return t.lstrip("%").strip()


def parse_num(text: str, allow_negative: bool = False) -> Optional[float]:
    """OCR text -> float. Fixes O->0, S->5, l->1 (only when the whole token becomes a number), strips units and a
    stray leading '-' (tick marks read as minus) unless allow_negative. '3,450' -> 3450; '%66' -> 66; '73Square Root
    Units' -> 73 (leading number of a value cell)."""
    if not text:
        return None
    t = strip_units(text.replace(" ", ""))
    if t.count(",") == 1 and "." not in t and re.match(r"^\d+,\d{1,2}$", t):
        t = t.replace(",", ".")            # decimal comma "41,5"
    fixed = t.translate(_FIX)
    if not allow_negative:
        fixed = fixed.lstrip("-")
    if _NUM_RE.match(fixed):
        v = float(fixed)
    else:
        m = _LEAD_RE.match(text.replace(",", "") if re.match(r"^\d{1,3}(,\d{3})+", text) else text)
        if not m:
            return None
        v = float(m.group(1).replace(",", "."))
        if v < 0 and not allow_negative:
            v = -v
    return v


@dataclass(frozen=True)
class Tick:
    pos: float      # pixel coordinate along the axis (x for a horizontal axis, y for a vertical one) or an angle
    value: float
    word: Optional[Word] = None


def find_ticks(words: Sequence[Word], axis: str = "y", region: Optional[Sequence[float]] = None,
               allow_negative: bool = False, min_conf: float = 0.5) -> List[Tick]:
    """Numeric words aligned along one axis. axis='y' -> a vertical axis (labels share a column, pos = cy);
    axis='x' -> a horizontal axis (labels share a row, pos = cx). Keeps the largest aligned cluster."""
    cands = []
    for w in words:
        if w.conf < min_conf:
            continue
        if region is not None and not (region[0] <= w.cx <= region[2] and region[1] <= w.cy <= region[3]):
            continue
        v = parse_num(w.text, allow_negative=allow_negative)
        if v is None or len(w.text) > 8:
            continue
        cands.append((w, v))
    if not cands:
        return []
    key = (lambda w: w.cx) if axis == "y" else (lambda w: w.cy)
    tol = max(4.0, 1.5 * float(np.median([w.h for w, _ in cands])))
    best: List[Tuple[Word, float]] = []
    for w0, _ in cands:
        grp = [(w, v) for w, v in cands if abs(key(w) - key(w0)) <= tol]
        if len(grp) > len(best):
            best = grp
    pos = (lambda w: w.cy) if axis == "y" else (lambda w: w.cx)
    return sorted((Tick(pos(w), v, w) for w, v in best), key=lambda t: t.pos)


# ── calibration ───────────────────────────────────────────────────────────────────────────────────────
_FWD = {"linear": lambda v: v, "log": np.log10, "sqrt": np.sqrt}
_INV = {"linear": lambda y: y, "log": lambda y: 10.0 ** y, "sqrt": lambda y: np.square(y)}


@dataclass
class AxisFit:
    slope: float
    intercept: float
    scale: str
    inliers: int
    n: int
    max_resid: float          # in transformed units (value units for linear)
    rejected: List[Tick] = field(default_factory=list)

    def value(self, pos):
        return _INV[self.scale](self.slope * np.asarray(pos, dtype=float) + self.intercept)

    def pos(self, value):
        return (_FWD[self.scale](np.asarray(value, dtype=float)) - self.intercept) / self.slope


def calibrate_axis(ticks: Sequence[Tick], scale: str = "linear", residual: Optional[float] = None,
                   expect_sign: int = 0, min_inliers: int = 3) -> Optional[AxisFit]:
    """value = f(a*pos + b) by exhaustive-pair RANSAC (deterministic), then least squares on the inliers.

    Returns None when fewer than `min_inliers` ticks agree or the slope sign != expect_sign (+1/-1; 0 = any).
    `residual` is the inlier threshold in transformed units (default 5 % of the value span)."""
    if scale not in _FWD:
        raise ValueError("scale must be linear|log|sqrt")
    pts = [(t, float(t.pos), float(t.value)) for t in ticks
           if not (scale == "log" and t.value <= 0) and not (scale == "sqrt" and t.value < 0)]
    if len(pts) < max(2, min_inliers):
        return None
    x = np.array([p[1] for p in pts])
    y = _FWD[scale](np.array([p[2] for p in pts]))
    span = float(np.ptp(y))
    if span <= 0:
        return None
    thr = residual if residual is not None else 0.05 * span
    best = None
    for i, j in itertools.combinations(range(len(pts)), 2):
        if abs(x[i] - x[j]) < 1e-6:
            continue
        a = (y[j] - y[i]) / (x[j] - x[i])
        if expect_sign and np.sign(a) != expect_sign:
            continue
        b = y[i] - a * x[i]
        r = np.abs(a * x + b - y)
        inl = r <= thr
        score = (int(inl.sum()), -float(r[inl].sum()))
        if best is None or score > best[0]:
            best = (score, inl)
    if best is None:
        return None
    inl = best[1]
    if inl.sum() < min_inliers:
        return None
    a, b = np.polyfit(x[inl], y[inl], 1)
    if expect_sign and np.sign(a) != expect_sign:
        return None
    resid = np.abs(a * x[inl] + b - y[inl])
    return AxisFit(float(a), float(b), scale, int(inl.sum()), len(pts), float(resid.max()),
                   [p[0] for p, m in zip(pts, inl) if not m])


# ── key/value rows ────────────────────────────────────────────────────────────────────────────────────
@dataclass
class Row:
    y: float
    words: List[Word]

    @property
    def label(self) -> Optional[Word]:
        return self.words[0] if self.words else None

    @property
    def value(self) -> Optional[Word]:
        """Rightmost word when it is separated from the label by a wide gap (a 'label ........ value' row)."""
        if len(self.words) < 2:
            return None
        last, prev = self.words[-1], self.words[-2]
        gap = last.bbox[0] - prev.bbox[2]
        return last if gap > 2.0 * max(last.h, prev.h) else None

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


def kv_rows(words: Sequence[Word], y_tol: Optional[float] = None) -> List[Row]:
    """Group words into rows by vertical centre (tolerance 0.6 x median height), each row sorted left to right."""
    if not words:
        return []
    tol = y_tol if y_tol is not None else 0.6 * float(np.median([w.h for w in words]))
    rows: List[Row] = []
    for w in sorted(words, key=lambda w: w.cy):
        if rows and abs(rows[-1].y - w.cy) <= tol:
            rows[-1].words.append(w)
            rows[-1].y = float(np.mean([v.cy for v in rows[-1].words]))
        else:
            rows.append(Row(w.cy, [w]))
    for r in rows:
        r.words.sort(key=lambda w: w.bbox[0])
    return rows


def angle_cw_from_up(x: float, y: float, cx: float, cy: float) -> float:
    """Clockwise angle in degrees from 12 o'clock of (x, y) around (cx, cy), in (-180, 180]."""
    a = math.degrees(math.atan2(x - cx, cy - y))
    return a - 360.0 if a > 180.0 else a

