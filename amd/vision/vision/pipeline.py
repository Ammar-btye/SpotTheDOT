"""One request -> one response dict (docs/vision-contract.md). No HTTP here; api.py wraps it."""
import logging
import time
from importlib import metadata
from typing import Dict, List, Optional

from . import CONTRACT_VERSION, SERVICE_VERSION, gauge, orbit, spectrogram, textaxes, thermal
from .annotate import annotate as draw
from .compare import compare
from .config import Settings
from .imageio import decode_b64, downscale, encode_jpeg_b64
from .result import Frame, ReaderResult
from .router import route

log = logging.getLogger("vision")


def _pkg_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "unknown"


VERSION = {"service": SERVICE_VERSION, "contract": CONTRACT_VERSION, "rapidocr": _pkg_version("rapidocr"),
           "onnxruntime": _pkg_version("onnxruntime"), "opencv": _pkg_version("opencv-python-headless")}


def run_reader(kind: str, frame: Frame, hints: Optional[dict]) -> ReaderResult:
    if kind == "thermal":
        return thermal.read(frame, hints)
    if kind == "gauge":
        return gauge.read(frame, hints)
    if kind == "spectrogram":
        return spectrogram.read(frame, hints)
    if kind == "orbit_screenshot":
        return orbit.read(frame, hints, require_header=True)
    if kind == "acoustic_imager":
        return orbit.read(frame, hints, require_header=False)
    res = ReaderResult()                     # visual: OCR only
    res.words = textaxes.ocr(frame.orig)
    return res


def analyze(req: Dict, settings: Settings) -> Dict:
    """req: a validated VisionRequest as a dict. Raises imageio.ImageError for 413/422."""
    t0 = time.perf_counter()
    dec = decode_b64(req["image_b64"], settings.max_image_bytes, settings.max_pixels)
    work, scale = downscale(dec.rgb, settings.work_max_side)
    frame = Frame(orig=dec.rgb, work=work, scale=scale)
    flags: List[str] = ["DOWNSCALED"] if scale < 1.0 else []
    rt = route(work, dec.size, req.get("kind"), req.get("action_type"))
    if rt["method"] == "heuristic":
        flags.append("ROUTER_HEURISTIC")
    hints = req.get("hints") or None
    try:
        res = run_reader(rt["label"], frame, hints)
    except Exception:                         # a reader bug must not take the request down
        log.exception("reader %s failed (media %s)", rt["label"], req.get("media_id") or dec.sha256[:16])
        res = ReaderResult(flags=["READER_FAILED"])
        try:
            res.words = textaxes.ocr(frame.orig)
        except Exception:
            log.exception("OCR fallback failed")
    flags += [f for f in res.flags if f not in flags]
    if not res.words:
        flags.append("NO_TEXT")
    ids = ["V%d" % (i + 1) for i in range(len(res.readings))]
    cmp_ = compare(req.get("logged"), res.readings, ids)
    alert = res.alert
    if cmp_ is not None and cmp_["agrees"] is False:
        title = "Vision %s %g %s disagrees with logged %s %g (Δ %+g, tolerance %g)" % (
            cmp_["vision_id"], cmp_["vision_value"], cmp_["logged_unit"], cmp_["logged_id"] or "value",
            cmp_["logged_value"], cmp_["delta"], cmp_["tolerance"])
        if alert is None or alert["severity"] < 2:
            alert = {"title": title, "severity": 2, "source": "vision.compare"}
    annotated = None
    if req.get("annotate", True):
        annotated = encode_jpeg_b64(draw(dec.rgb, res.readings, ids, res.extra_marks))
    readings = []
    for vid, rd in zip(ids, res.readings):
        d = {"id": vid, "quantity": rd.quantity, "value": float(rd.value), "unit": rd.unit,
             "confidence": float(rd.confidence), "method": rd.method, "flags": list(dict.fromkeys(rd.flags))}
        if rd.bbox is not None:
            d["bbox"] = [int(v) for v in rd.bbox]
        if rd.point is not None:
            d["point"] = [int(v) for v in rd.point]
        if rd.note:
            d["note"] = rd.note
        readings.append(d)
    return {"media_id": req.get("media_id") or "sha256:" + dec.sha256[:16],
            "kind": rt["label"], "router": rt,
            "ocr": [w.as_dict() for w in res.words],
            "readings": readings,
            "key_results": res.key_results,
            "comparison": cmp_, "alert": alert, "flags": list(dict.fromkeys(flags)),
            "annotated_image_b64": annotated, "annotated_mime": "image/jpeg" if annotated else None,
            "latency_ms": int(round((time.perf_counter() - t0) * 1000)),
            "version": dict(VERSION)}


def ocr_only(image_b64: str, upscale: Optional[bool], settings: Settings) -> Dict:
    t0 = time.perf_counter()
    dec = decode_b64(image_b64, settings.max_image_bytes, settings.max_pixels)
    words = textaxes.ocr(dec.rgb, upscale=upscale)
    w, h = dec.size
    return {"words": [x.as_dict() for x in words], "width": w, "height": h,
            "latency_ms": int(round((time.perf_counter() - t0) * 1000))}
